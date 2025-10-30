"""
🎯 Менеджер Lesson Events - автоматичне управління життєвим циклом
"""

import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.lesson_event import LessonEvent, LessonEventStatus
from app.models.schedule import Schedule
from app.models.bot_schedule import BotSchedule
from app.models.teacher import Teacher
from app.utils.timezone import (
    next_n_weekly, now_utc, parse_time_string, 
    combine_date_time_to_utc, KYIV, to_utc
)

logger = logging.getLogger(__name__)

class LessonEventManager:
    """Управління життєвим циклом lesson events."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def ensure_planned_lesson_event(self, schedule_id: int, target_date: date) -> Optional[LessonEvent]:
        """
        Забезпечує наявність PLANNED lesson event для вказаного розкладу і дати.
        
        Логіка:
        1. Якщо є PLANNED - повертає його
        2. Якщо немає жодного - створює новий PLANNED
        3. Якщо всі COMPLETED/SENT - створює новий PLANNED
        """
        
        # Шукаємо існуючі lesson events для цього розкладу і дати
        result = await self.db.execute(
            select(LessonEvent)
            .where(
                LessonEvent.schedule_id == schedule_id,
                LessonEvent.date == target_date
            )
        )
        
        existing_events = result.scalars().all()
        
        # Перевіряємо чи є PLANNED
        planned_events = [e for e in existing_events if e.status == LessonEventStatus.PLANNED]
        
        if planned_events:
            logger.info(f"Found existing PLANNED lesson event {planned_events[0].id} for schedule {schedule_id}")
            return planned_events[0]
        
        # Отримуємо дані розкладу
        schedule_result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        
        schedule = schedule_result.scalar_one_or_none()
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return None
        
        # Отримуємо teacher_chat_id
        teacher_result = await self.db.execute(
            select(Teacher).where(Teacher.id == schedule.teacher_id)
        )
        teacher = teacher_result.scalar_one_or_none()
        teacher_chat_id = teacher.tg_chat_id if teacher and teacher.tg_chat_id else None
        
        # Розраховуємо UTC timestamps
        lesson_time = schedule.start_time
        start_at_utc = combine_date_time_to_utc(target_date, lesson_time)
        
        # notify_at = start_at (можна додати offset пізніше)
        notify_at_utc = start_at_utc
        
        # Створюємо новий PLANNED lesson event
        new_event = LessonEvent(
            schedule_id=schedule_id,
            date=target_date,
            club_id=schedule.club_id,
            teacher_id=schedule.teacher_id,
            status=LessonEventStatus.PLANNED,
            start_at=start_at_utc,
            notify_at=notify_at_utc,
            teacher_chat_id=teacher_chat_id
        )
        
        self.db.add(new_event)
        await self.db.flush()  # Отримуємо ID без commit
        
        logger.info(f"Created new PLANNED lesson event {new_event.id} for schedule {schedule_id} on {target_date}")
        
        return new_event
    
    async def auto_generate_daily_events(self, target_date: Optional[date] = None) -> int:
        """
        Автоматично генерує lesson events для всіх активних розкладів.
        
        Args:
            target_date: Дата для генерації (за замовчуванням - сьогодні)
            
        Returns:
            Кількість створених events
        """
        
        if target_date is None:
            target_date = date.today()
        
        weekday = target_date.isoweekday()  # 1=Понеділок, 7=Неділя
        
        # Пропускаємо вихідні
        if weekday > 5:
            logger.info(f"Skipping weekend day {target_date}")
            return 0
        
        # Отримуємо всі активні розклади для цього дня тижня
        result = await self.db.execute(
            select(Schedule)
            .where(
                Schedule.weekday == weekday,
                Schedule.active == True
            )
        )
        
        schedules = result.scalars().all()
        
        created_count = 0
        
        for schedule in schedules:
            event = await self.ensure_planned_lesson_event(schedule.id, target_date)
            if event and event.id:  # Якщо створено новий event
                # Перевіряємо чи це щойно створений event
                if event.created_at and (datetime.utcnow() - event.created_at.replace(tzinfo=None)).seconds < 60:
                    created_count += 1
        
        if created_count > 0:
            await self.db.commit()
            logger.info(f"Auto-generated {created_count} lesson events for {target_date}")
        
        return created_count
    
    async def reset_lesson_event_to_planned(self, lesson_event_id: int) -> bool:
        """
        Скидає lesson event назад у статус PLANNED.
        
        Корисно для повторного тестування або виправлення помилок.
        """
        
        try:
            await self.db.execute(
                update(LessonEvent)
                .where(LessonEvent.id == lesson_event_id)
                .values(
                    status=LessonEventStatus.PLANNED,
                    sent_at=None,
                    completed_at=None
                )
            )
            
            await self.db.commit()
            
            logger.info(f"Reset lesson event {lesson_event_id} to PLANNED status")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting lesson event {lesson_event_id}: {e}")
            await self.db.rollback()
            return False
    
    async def ensure_bot_schedule_has_events(self, bot_schedule_id: int) -> bool:
        """
        Забезпечує що для BotSchedule є відповідні lesson events з правильними UTC timestamps.
        
        Викликається при створенні нового BotSchedule через адмін панель.
        """
        
        # Отримуємо BotSchedule з усіма зв'язаними даними
        result = await self.db.execute(
            select(BotSchedule)
            .options(
                selectinload(BotSchedule.schedule).selectinload(Schedule.teacher)
            )
            .where(BotSchedule.id == bot_schedule_id)
        )
        
        bot_schedule = result.scalar_one_or_none()
        if not bot_schedule:
            logger.error(f"BotSchedule {bot_schedule_id} not found")
            return False
        
        schedule = bot_schedule.schedule
        if not schedule:
            logger.error(f"Schedule not found for BotSchedule {bot_schedule_id}")
            return False
        
        # Генеруємо UTC timestamps на основі BotSchedule.custom_time
        notification_time = bot_schedule.custom_time
        
        # Генеруємо events для наступних 14 днів (2 тижні), включаючи сьогодні
        # schedule.weekday: 1=Понеділок, 5=П'ятниця
        # next_n_weekly потребує: 0=Понеділок, 4=П'ятниця  
        target_weekday_0based = schedule.weekday - 1
        
        logger.info(f"Schedule {schedule.id} weekday={schedule.weekday} (1-based), converting to {target_weekday_0based} (0-based)")
        
        # ✅ ВИПРАВЛЕННЯ: Генеруємо occurrences на основі РЕАЛЬНОГО ЧАСУ УРОКУ, а не нотифікації
        # Це гарантує що target_date буде правильна навіть якщо notification_time раніше за start_time
        occurrences = next_n_weekly(
            local_weekday=target_weekday_0based,
            local_hour=schedule.start_time.hour,  # ← Використовуємо ЧАС УРОКУ, а не нотифікації!
            local_minute=schedule.start_time.minute,
            n=52,  # 52 тижні = 1 рік (щотижнева регенерація забезпечить покриття на рік вперед)
            include_today=True  # Включаємо сьогодні якщо час ще не пройшов
        )
        
        logger.info(f"Generated {len(occurrences)} occurrences for schedule {schedule.id}, starting from {occurrences[0] if occurrences else 'None'}")
        
        events_created = 0
        
        # ✅ ВИПРАВЛЕННЯ: occurrences тепер містить час СТАРТУ УРОКУ, а не нотифікації
        for start_at_utc in occurrences:
            target_date = start_at_utc.astimezone(KYIV).date()
            
            # Обчислюємо час нотифікації (start_at - offset)
            offset_minutes = bot_schedule.offset_minutes or 0
            notify_at_utc = start_at_utc - timedelta(minutes=offset_minutes)
            
            # Перевіряємо чи вже є lesson event для цієї дати від цього bot_schedule
            # Використовуємо bot_schedule_id для унікальності
            existing_result = await self.db.execute(
                select(LessonEvent)
                .where(
                    LessonEvent.schedule_id == schedule.id,
                    LessonEvent.date == target_date,
                    LessonEvent.idempotency_key.like(f'bot_schedule_{bot_schedule_id}_%')
                )
                .limit(1)
            )
            
            existing_event = existing_result.scalar_one_or_none()
            
            if existing_event:
                # Оновлюємо існуючий event з правильними UTC timestamps
                await self.db.execute(
                    update(LessonEvent)
                    .where(LessonEvent.id == existing_event.id)
                    .values(
                        start_at=start_at_utc,
                        notify_at=notify_at_utc,
                        teacher_chat_id=bot_schedule.schedule.teacher.tg_chat_id if bot_schedule.schedule.teacher.tg_chat_id else None,
                        status=LessonEventStatus.PLANNED,
                        sent_at=None,
                        completed_at=None,
                        send_attempts=0,
                        last_error=None
                    )
                )
                logger.info(f"Updated existing lesson event {existing_event.id} with notify_at={notify_at_utc}")
            else:
                # Створюємо новий event з унікальним idempotency_key
                idempotency_key = f"bot_schedule_{bot_schedule_id}_{target_date.strftime('%Y%m%d')}"
                new_event = LessonEvent(
                    schedule_id=schedule.id,
                    date=target_date,
                    club_id=schedule.club_id,
                    teacher_id=schedule.teacher_id,
                    status=LessonEventStatus.PLANNED,
                    start_at=start_at_utc,
                    notify_at=notify_at_utc,
                    teacher_chat_id=bot_schedule.schedule.teacher.tg_chat_id if bot_schedule.schedule.teacher.tg_chat_id else None,
                    send_attempts=0,
                    idempotency_key=idempotency_key
                )
                
                self.db.add(new_event)
                events_created += 1
                logger.info(f"Created new lesson event for {target_date} with notify_at={notify_at_utc}")
        
        if events_created > 0:
            await self.db.commit()
            logger.info(f"Created {events_created} new lesson events for BotSchedule {bot_schedule_id}")
        
        return True
    
    async def cleanup_past_lesson_events(self) -> dict:
        """
        Видаляє старі PLANNED події (дата < сьогодні).
        
        Видаляє тільки події які:
        - Мають статус PLANNED
        - Дата вже минула (date < сьогодні)
        - НЕ мають attendance записів
        - НЕ мають conducted_lessons
        
        Returns:
            dict з статистикою: deleted_count, checked_count
        """
        from datetime import date as date_type
        from app.models.attendance import Attendance
        from app.models.conducted_lesson import ConductedLesson
        
        today = date_type.today()
        
        logger.info(f"🧹 Початок очищення старих PLANNED подій (дата < {today})...")
        
        try:
            # Знаходимо старі PLANNED події без attendance та conducted_lessons
            result = await self.db.execute(
                select(LessonEvent)
                .outerjoin(Attendance, Attendance.lesson_event_id == LessonEvent.id)
                .outerjoin(ConductedLesson, ConductedLesson.lesson_event_id == LessonEvent.id)
                .where(
                    and_(
                        LessonEvent.status == LessonEventStatus.PLANNED,
                        LessonEvent.date < today,
                        Attendance.id.is_(None),  # Немає attendance
                        ConductedLesson.id.is_(None)  # Немає conducted_lesson
                    )
                )
            )
            
            old_events = result.scalars().all()
            checked_count = len(old_events)
            
            if checked_count == 0:
                logger.info("✅ Немає старих PLANNED подій для видалення")
                return {"deleted_count": 0, "checked_count": 0}
            
            logger.info(f"📋 Знайдено {checked_count} старих PLANNED подій для видалення")
            
            # Видаляємо по одній для логування
            deleted_count = 0
            for event in old_events:
                await self.db.delete(event)
                deleted_count += 1
                logger.debug(f"🗑️ Видалено стару подію: ID {event.id}, дата {event.date}, schedule {event.schedule_id}")
            
            await self.db.commit()
            
            logger.info(f"✅ Очищення завершено: видалено {deleted_count} старих подій")
            
            return {"deleted_count": deleted_count, "checked_count": checked_count}
            
        except Exception as e:
            logger.error(f"❌ Помилка очищення старих подій: {e}")
            await self.db.rollback()
            return {"deleted_count": 0, "checked_count": 0, "error": str(e)}
    
    async def cleanup_outdated_future_events(self) -> dict:
        """
        Видаляє майбутні PLANNED події з неправильним часом після зміни розкладу.
        
        Перевіряє чи start_at події відповідає schedule.start_time.
        Видаляє тільки майбутні PLANNED події без attendance.
        
        Returns:
            dict з статистикою: deleted_count, checked_count, schedules_checked
        """
        from datetime import date as date_type, timedelta
        from app.models.attendance import Attendance
        
        today = date_type.today()
        
        logger.info(f"🔍 Початок перевірки майбутніх подій на відповідність розкладу...")
        
        try:
            # Отримуємо всі активні розклади
            schedules_result = await self.db.execute(
                select(Schedule).where(Schedule.active == True)
            )
            schedules = schedules_result.scalars().all()
            
            logger.info(f"📋 Перевіряємо {len(schedules)} активних розкладів")
            
            deleted_count = 0
            checked_count = 0
            schedules_checked = 0
            
            for schedule in schedules:
                schedules_checked += 1
                
                # Знаходимо майбутні PLANNED події для цього розкладу
                events_result = await self.db.execute(
                    select(LessonEvent)
                    .outerjoin(Attendance, Attendance.lesson_event_id == LessonEvent.id)
                    .where(
                        and_(
                            LessonEvent.schedule_id == schedule.id,
                            LessonEvent.status == LessonEventStatus.PLANNED,
                            LessonEvent.date >= today,
                            Attendance.id.is_(None)  # Немає attendance
                        )
                    )
                )
                
                events = events_result.scalars().all()
                checked_count += len(events)
                
                for event in events:
                    # Обчислюємо правильний start_at для цієї дати
                    expected_start_at = combine_date_time_to_utc(event.date, schedule.start_time)
                    
                    # Якщо час не збігається (більше ніж на 1 хвилину різниці)
                    time_diff = abs((event.start_at - expected_start_at).total_seconds())
                    
                    if time_diff > 60:  # Більше 1 хвилини різниці
                        logger.info(
                            f"🗑️ Видаляю застарілу подію: ID {event.id}, schedule {schedule.id}, "
                            f"дата {event.date}, має {event.start_at}, очікується {expected_start_at}"
                        )
                        await self.db.delete(event)
                        deleted_count += 1
            
            await self.db.commit()
            
            logger.info(
                f"✅ Перевірка завершена: перевірено {checked_count} подій з {schedules_checked} розкладів, "
                f"видалено {deleted_count} застарілих"
            )
            
            return {
                "deleted_count": deleted_count,
                "checked_count": checked_count,
                "schedules_checked": schedules_checked
            }
            
        except Exception as e:
            logger.error(f"❌ Помилка перевірки майбутніх подій: {e}")
            await self.db.rollback()
            return {"deleted_count": 0, "checked_count": 0, "schedules_checked": 0, "error": str(e)}
    
    async def ensure_events_for_next_365_days(self) -> dict:
        """
        Гарантує що є події на наступні 365 днів для всіх активних bot_schedules.
        
        Логіка:
        1. Знаходить останню майбутню подію для кожного bot_schedule
        2. Якщо остання подія < 365 днів від сьогодні, генерує додаткові події
        3. НЕ генерує більше 365 днів від сьогодні
        
        Returns:
            dict з статистикою: total_bot_schedules, events_created
        """
        from datetime import date as date_type, timedelta
        
        today = date_type.today()
        target_date = today + timedelta(days=365)
        
        logger.info(f"🔄 Забезпечення подій на 365 днів (до {target_date})...")
        
        try:
            # Отримуємо всі активні bot_schedules
            result = await self.db.execute(
                select(BotSchedule)
                .options(selectinload(BotSchedule.schedule))
                .where(BotSchedule.enabled == True)
            )
            
            bot_schedules = result.scalars().all()
            
            if not bot_schedules:
                logger.warning("⚠️ Немає активних bot_schedules")
                return {"total_bot_schedules": 0, "events_created": 0}
            
            logger.info(f"📋 Знайдено {len(bot_schedules)} активних bot_schedules")
            
            total_events_created = 0
            
            for bot_schedule in bot_schedules:
                # Знаходимо останню майбутню подію
                last_event_result = await self.db.execute(
                    select(LessonEvent)
                    .where(
                        LessonEvent.schedule_id == bot_schedule.schedule_id,
                        LessonEvent.date >= today
                    )
                    .order_by(LessonEvent.date.desc())
                    .limit(1)
                )
                
                last_event = last_event_result.scalar_one_or_none()
                
                if last_event and last_event.date >= target_date:
                    logger.debug(
                        f"✅ BotSchedule {bot_schedule.id}: вже є події до {last_event.date} "
                        f"(потрібно до {target_date})"
                    )
                    continue
                
                # Генеруємо події до target_date
                logger.info(
                    f"🔄 BotSchedule {bot_schedule.id}: останя подія {last_event.date if last_event else 'None'}, "
                    f"генеруємо до {target_date}"
                )
                
                success = await self.ensure_bot_schedule_has_events(bot_schedule.id)
                
                if success:
                    total_events_created += 1
            
            await self.db.commit()
            
            logger.info(f"✅ Забезпечення подій завершено: оброблено {len(bot_schedules)} bot_schedules")
            
            return {
                "total_bot_schedules": len(bot_schedules),
                "events_created": total_events_created
            }
            
        except Exception as e:
            logger.error(f"❌ Помилка забезпечення подій: {e}")
            await self.db.rollback()
            return {"total_bot_schedules": 0, "events_created": 0, "error": str(e)}

# Глобальні функції для використання в API
async def ensure_events_for_bot_schedule(bot_schedule_id: int):
    """Забезпечує lesson events для нового BotSchedule."""
    async with AsyncSessionLocal() as db:
        manager = LessonEventManager(db)
        return await manager.ensure_bot_schedule_has_events(bot_schedule_id)

async def auto_generate_todays_events():
    """Автоматично генерує lesson events на сьогодні."""
    async with AsyncSessionLocal() as db:
        manager = LessonEventManager(db)
        return await manager.auto_generate_daily_events()

async def reset_event_to_planned(lesson_event_id: int):
    """Скидає lesson event у статус PLANNED."""
    async with AsyncSessionLocal() as db:
        manager = LessonEventManager(db)
        return await manager.reset_lesson_event_to_planned(lesson_event_id)
