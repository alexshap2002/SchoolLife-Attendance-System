#!/usr/bin/env python3
"""
Seed script для додавання тестових автоматизацій.
"""

import asyncio
import logging
from datetime import time

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import AdminAutomation, Teacher

logger = logging.getLogger(__name__)

async def seed_automations():
    """Додати тестові автоматизації."""
    
    async with AsyncSessionLocal() as db:
        # Перевірка чи вже є автоматизації
        result = await db.execute(select(AdminAutomation))
        existing = result.scalars().all()
        
        if existing:
            logger.info(f"Знайдено {len(existing)} існуючих автоматизацій, пропускаємо seed")
            return
        
        # Знаходимо першого активного вчителя для chat_id
        teacher_result = await db.execute(
            select(Teacher).where(Teacher.active == True).limit(1)
        )
        teacher = teacher_result.scalar_one_or_none()
        
        if not teacher or not teacher.tg_chat_id:
            logger.warning("Немає активного вчителя з Telegram chat_id для тестування автоматизацій")
            # Використаємо тестовий chat_id
            admin_chat_id = 733455161
        else:
            admin_chat_id = teacher.tg_chat_id
        
        # Створюємо базові автоматизації
        automations = [
            AdminAutomation(
                name="Дні народження студентів",
                description="Щоденна перевірка днів народження студентів о 09:00",
                automation_type="BIRTHDAYS",
                admin_chat_id=admin_chat_id,
                is_enabled=True,
                trigger_time=time(9, 0, 0),
                config='{"daily": true}'
            ),
            AdminAutomation(
                name="Нагадування за 30 хвилин",
                description="Нагадування про початок уроків за 30 хвилин",
                automation_type="LESSON_REMINDER_30",
                admin_chat_id=admin_chat_id,
                is_enabled=True,
                config='{"minutes": 30}'
            ),
            AdminAutomation(
                name="Нагадування за 10 хвилин",
                description="Нагадування про початок уроків за 10 хвилин",
                automation_type="LESSON_REMINDER_10",
                admin_chat_id=admin_chat_id,
                is_enabled=True,
                config='{"minutes": 10}'
            ),
            AdminAutomation(
                name="Щоденний звіт",
                description="Щоденний звіт про відвідуваність о 18:00",
                automation_type="DAILY_REPORT",
                admin_chat_id=admin_chat_id,
                is_enabled=True,
                trigger_time=time(18, 0, 0),
                config='{"daily": true}'
            ),
            AdminAutomation(
                name="Попередження про низьку відвідуваність",
                description="Щотижневе попередження про студентів з низькою відвідуваністю",
                automation_type="LOW_ATTENDANCE_ALERT",
                admin_chat_id=admin_chat_id,
                is_enabled=True,
                trigger_time=time(10, 0, 0),
                trigger_day=1,  # Понеділок
                config='{"threshold": 0.6, "weekly": true}'
            ),
            AdminAutomation(
                name="Тижнева статистика відвідуваності",
                description="Звіт про відвідуваність за тиждень кожної неділі",
                automation_type="WEEKLY_ATTENDANCE",
                admin_chat_id=admin_chat_id,
                is_enabled=True,
                trigger_time=time(19, 0, 0),
                trigger_day=7,  # Неділя
                config='{"weekly": true}'
            )
        ]
        
        for automation in automations:
            db.add(automation)
        
        await db.commit()
        
        logger.info(f"✅ Додано {len(automations)} тестових автоматизацій з admin_chat_id={admin_chat_id}")
        
        # Виводимо список створених автоматизацій
        for auto in automations:
            logger.info(f"   • {auto.name} ({auto.automation_type}) - {'увімкнено' if auto.is_enabled else 'вимкнено'}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_automations())
