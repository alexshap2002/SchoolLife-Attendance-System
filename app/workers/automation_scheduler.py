"""
Планувальник для виконання автоматизацій.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import AdminAutomation
from app.models.bot_schedule import BotSchedule
from app.services.automation_service import automation_service
from app.utils.timezone import KYIV
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """Планувальник автоматизацій."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone='Europe/Kiev')
        self.is_running = False
    
    async def start(self):
        """Запустити планувальник."""
        
        if self.is_running:
            logger.warning("Планувальник вже запущений")
            return
        
        logger.info("Запуск планувальника автоматизацій...")
        
        # Завантажуємо всі активні автоматизації
        await self._load_automations()
        
        # Додаємо задачу для оновлення автоматизацій кожні 5 хвилин
        self.scheduler.add_job(
            self._reload_automations,
            IntervalTrigger(minutes=5),
            id="reload_automations",
            name="Оновлення списку автоматизацій"
        )
        
        # Додаємо задачі для нагадувань про уроки (перевіряємо кожну хвилину)
        self.scheduler.add_job(
            self._check_lesson_reminders,
            IntervalTrigger(minutes=1),
            id="lesson_reminders",
            name="Перевірка нагадувань про уроки"
        )
        
        # Додаємо задачу для очищення та регенерації lesson events (кожної неділі о 22:00 та 23:00)
        self.scheduler.add_job(
            self._cleanup_and_regenerate_events,
            CronTrigger(day_of_week='sun', hour=22, minute=0, timezone=KYIV),
            id="cleanup_and_regenerate_events",
            name="Щотижнева очистка та регенерація lesson events"
        )
        
        # Додаємо щоденну задачу для очистки застарілих PLANNED подій (кожного дня о 02:00)
        self.scheduler.add_job(
            self._cleanup_old_planned_events,
            CronTrigger(hour=2, minute=0, timezone=KYIV),
            id="cleanup_old_planned_events",
            name="Щоденна очистка застарілих PLANNED подій"
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info("Планувальник автоматизацій запущений")
        logger.info("✅ Додано задачу очищення та регенерації lesson events (неділя 22:00 Київський час)")
        logger.info("✅ Додано задачу щоденної очистки застарілих PLANNED подій (щодня 02:00 Київський час)")
    
    async def stop(self):
        """Зупинити планувальник."""
        
        if not self.is_running:
            return
        
        logger.info("Зупинка планувальника автоматизацій...")
        
        self.scheduler.shutdown()
        self.is_running = False
        
        logger.info("Планувальник автоматизацій зупинений")
    
    async def _load_automations(self):
        """Завантажити всі активні автоматизації."""
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AdminAutomation)
                .where(AdminAutomation.is_enabled == True)
                .order_by(AdminAutomation.id)
            )
            automations = result.scalars().all()
            
            logger.info(f"Завантажено {len(automations)} активних автоматизацій")
            
            for automation in automations:
                await self._add_automation_job(automation)
    
    async def _reload_automations(self):
        """Перезавантажити автоматизації."""
        
        try:
            # Видаляємо всі старі задачі автоматизацій (крім системних)
            for job in self.scheduler.get_jobs():
                if job.id.startswith("automation_"):
                    self.scheduler.remove_job(job.id)
            
            # Завантажуємо нові
            await self._load_automations()
            
        except Exception as e:
            logger.error(f"Помилка перезавантаження автоматизацій: {e}")
    
    async def _add_automation_job(self, automation: AdminAutomation):
        """Додати задачу для автоматизації."""
        
        job_id = f"automation_{automation.id}"
        
        try:
            # Видаляємо існуючу задачу якщо є
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Для нагадувань про уроки не додаємо окремі задачі - вони обробляються в _check_lesson_reminders
            if automation.automation_type in ["LESSON_REMINDER_30", "LESSON_REMINDER_10"]:
                return
            
            # Створюємо тригер в залежності від типу автоматизації
            trigger = self._create_trigger(automation)
            
            if trigger:
                self.scheduler.add_job(
                    self._execute_automation,
                    trigger,
                    args=[automation.id],
                    id=job_id,
                    name=f"Автоматизація: {automation.name}",
                    misfire_grace_time=300,  # 5 хвилин
                    max_instances=1
                )
                
                logger.info(f"Додано задачу для автоматизації '{automation.name}' (ID: {automation.id})")
        
        except Exception as e:
            logger.error(f"Помилка додавання задачі для автоматизації {automation.id}: {e}")
    
    def _create_trigger(self, automation: AdminAutomation):
        """Створити тригер для автоматизації."""
        
        # Якщо є час та день тижня - щотижнева задача
        if automation.trigger_time and automation.trigger_day is not None:
            return CronTrigger(
                day_of_week=automation.trigger_day,
                hour=automation.trigger_time.hour,
                minute=automation.trigger_time.minute,
                second=automation.trigger_time.second
            )
        
        # Якщо тільки час - щоденна задача
        elif automation.trigger_time:
            return CronTrigger(
                hour=automation.trigger_time.hour,
                minute=automation.trigger_time.minute,
                second=automation.trigger_time.second
            )
        
        # Для автоматизацій без часу - не створюємо тригер
        return None
    
    async def _execute_automation(self, automation_id: int):
        """Виконати автоматизацію."""
        
        try:
            async with AsyncSessionLocal() as db:
                # Отримуємо автоматизацію
                result = await db.execute(
                    select(AdminAutomation)
                    .where(
                        AdminAutomation.id == automation_id,
                        AdminAutomation.is_enabled == True
                    )
                )
                automation = result.scalar_one_or_none()
                
                if not automation:
                    logger.warning(f"Автоматизація {automation_id} не знайдена або вимкнена")
                    return
                
                # Виконуємо автоматизацію
                result = await automation_service.execute_automation(automation, db)
                
                logger.info(f"Автоматизація '{automation.name}' виконана успішно")
                
        except Exception as e:
            logger.error(f"Помилка виконання автоматизації {automation_id}: {e}")
    
    async def _check_lesson_reminders(self):
        """Перевірити нагадування про уроки."""
        
        try:
            async with AsyncSessionLocal() as db:
                # Отримуємо активні нагадування про уроки
                result = await db.execute(
                    select(AdminAutomation)
                    .where(
                        AdminAutomation.is_enabled == True,
                        AdminAutomation.automation_type.in_(["LESSON_REMINDER_30", "LESSON_REMINDER_10"])
                    )
                )
                reminder_automations = result.scalars().all()
                
                for automation in reminder_automations:
                    # Перевіряємо чи не виконувалася ця автоматизація останні 5 хвилин
                    if (automation.last_triggered and 
                        (datetime.now() - automation.last_triggered).total_seconds() < 300):
                        continue
                    
                    try:
                        await automation_service.execute_automation(automation, db)
                    except Exception as e:
                        logger.error(f"Помилка виконання нагадування {automation.id}: {e}")
                        
        except Exception as e:
            logger.error(f"Помилка перевірки нагадувань про уроки: {e}")
    
    async def _cleanup_old_planned_events(self):
        """
        Щоденна очистка застарілих PLANNED подій старше 1 дня.
        
        Викликається щодня о 02:00 (Київський час).
        Переводить застарілі PLANNED події у статус SKIPPED.
        """
        logger.info("🧹 Початок щоденної очистки застарілих PLANNED подій...")
        
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import update, and_
                from app.models.lesson_event import LessonEvent, LessonEventStatus
                from datetime import datetime, timezone, timedelta
                
                # Визначаємо порогову дату (1 день тому)
                threshold_date = datetime.now(timezone.utc) - timedelta(days=1)
                
                # Оновлюємо застарілі PLANNED події
                result = await db.execute(
                    update(LessonEvent)
                    .where(
                        and_(
                            LessonEvent.status == LessonEventStatus.PLANNED,
                            LessonEvent.notify_at < threshold_date
                        )
                    )
                    .values(
                        status=LessonEventStatus.SKIPPED,
                        last_error="Automatically skipped - event older than 1 day"
                    )
                )
                
                await db.commit()
                
                updated_count = result.rowcount
                logger.info(f"✅ Переведено {updated_count} застарілих PLANNED подій у статус SKIPPED")
                
        except Exception as e:
            logger.error(f"❌ Помилка щоденної очистки застарілих подій: {e}")
    
    async def _cleanup_and_regenerate_events(self):
        """
        Щотижнева очистка та регенерація lesson events.
        
        Викликається кожної неділі о 22:00 (Київський час).
        
        Процес:
        1. Видаляє старі PLANNED події (date < сьогодні)
        2. Видаляє застарілі майбутні події (неправильний час після зміни розкладу)
        3. Забезпечує події на 365 днів від сьогодні
        """
        logger.info("🧹🔄 Початок щотижневої очистки та регенерації lesson events...")
        
        try:
            async with AsyncSessionLocal() as db:
                from app.services.lesson_event_manager import LessonEventManager
                manager = LessonEventManager(db)
                
                # Крок 1: Видаляємо старі PLANNED події
                logger.info("📍 Крок 1/3: Видалення старих PLANNED подій...")
                cleanup_past_result = await manager.cleanup_past_lesson_events()
                logger.info(
                    f"✅ Видалено {cleanup_past_result.get('deleted_count', 0)} старих подій "
                    f"(перевірено {cleanup_past_result.get('checked_count', 0)})"
                )
                
                # Крок 2: Видаляємо застарілі майбутні події (після зміни розкладу)
                logger.info("📍 Крок 2/3: Перевірка майбутніх подій на актуальність...")
                cleanup_future_result = await manager.cleanup_outdated_future_events()
                logger.info(
                    f"✅ Видалено {cleanup_future_result.get('deleted_count', 0)} застарілих подій "
                    f"(перевірено {cleanup_future_result.get('checked_count', 0)} подій "
                    f"з {cleanup_future_result.get('schedules_checked', 0)} розкладів)"
                )
                
                # Крок 3: Забезпечуємо події на 365 днів
                logger.info("📍 Крок 3/3: Забезпечення подій на 365 днів...")
                ensure_result = await manager.ensure_events_for_next_365_days()
                logger.info(
                    f"✅ Оброблено {ensure_result.get('total_bot_schedules', 0)} bot_schedules, "
                    f"створено подій для {ensure_result.get('events_created', 0)}"
                )
                
                logger.info("🎉 Щотижнева очистка та регенерація завершена успішно!")
                
        except Exception as e:
            logger.error(f"❌ Критична помилка щотижневої очистки та регенерації: {e}")


# Глобальний екземпляр планувальника
scheduler = AutomationScheduler()


async def start_automation_scheduler():
    """Запустити планувальник автоматизацій."""
    await scheduler.start()


async def stop_automation_scheduler():
    """Зупинити планувальник автоматизацій."""
    await scheduler.stop()
