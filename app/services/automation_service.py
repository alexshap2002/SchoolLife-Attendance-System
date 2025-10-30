"""
Сервіс для виконання автоматизацій адміністратора.
"""

import logging
import asyncio
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional
import json

from sqlalchemy import select, func, case, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import (
    AdminAutomation, AutomationLog, Student, Teacher, Club, 
    Schedule, Attendance, ConductedLesson, PayRate, Payroll, LessonEvent
)

logger = logging.getLogger(__name__)


class AutomationService:
    """Сервіс для виконання автоматизацій."""
    
    def __init__(self):
        self.telegram_service = None  # Будемо ініціалізувати пізніше
    
    async def execute_automation(
        self, 
        automation: AdminAutomation, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Виконати автоматизацію."""
        
        start_time = datetime.now()
        
        try:
            # Виконуємо автоматизацію в залежності від типу
            if automation.automation_type == "BIRTHDAYS":
                result = await self._execute_birthdays(automation, db)
            elif automation.automation_type == "LESSON_REMINDER_30":
                result = await self._execute_lesson_reminder(automation, db, 30)
            elif automation.automation_type == "LESSON_REMINDER_10":
                result = await self._execute_lesson_reminder(automation, db, 10)
            elif automation.automation_type == "DAILY_REPORT":
                result = await self._execute_daily_report(automation, db)
            elif automation.automation_type == "WEEKLY_ATTENDANCE":
                result = await self._execute_weekly_attendance(automation, db)
            elif automation.automation_type == "LOW_ATTENDANCE_ALERT":
                result = await self._execute_low_attendance_alert(automation, db)
            elif automation.automation_type == "MISSING_ATTENDANCE":
                result = await self._execute_missing_attendance(automation, db)
            elif automation.automation_type == "PAYROLL_REMINDER":
                result = await self._execute_payroll_reminder(automation, db)
            else:
                # Для інших типів повертаємо базову відповідь
                result = await self._execute_basic_automation(automation, db)
            
            # Оновлюємо час останнього виконання
            automation.last_triggered = datetime.now()
            await db.commit()
            
            # Записуємо лог успіху
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self._log_execution(automation.id, "SUCCESS", result["message"], db, execution_time, result.get("metrics", {}))
            
            return result
        
        except Exception as e:
            logger.error(f"Помилка виконання автоматизації {automation.id}: {e}")
            
            # Записуємо лог помилки
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self._log_execution(automation.id, "ERROR", f"Помилка: {str(e)}", db, execution_time, error_details=str(e))
            
            raise e

    async def _execute_birthdays(self, automation: AdminAutomation, db: AsyncSession) -> Dict[str, Any]:
        """Виконати автоматизацію днів народження."""
        
        today = date.today()
        
        # Знаходимо студентів з днем народження сьогодні
        result = await db.execute(
            select(Student)
            .where(
                    func.extract('month', Student.birth_date) == today.month,
                func.extract('day', Student.birth_date) == today.day
            )
        )
        birthday_students = result.scalars().all()
        
        # 🚫 НЕ ВІДПРАВЛЯЄМО СПАМ: якщо немає студентів з ДН
        if not birthday_students:
            return {
                "message": "🎂 Немає студентів з днем народження сьогодні (повідомлення НЕ відправлено)",
                "metrics": {"students_count": 0}
            }
        
        # ✅ ВІДПРАВЛЯЄМО коли є студенти з ДН
        message = f"🎂 <b>Дні народження сьогодні</b>\n\n"
        message += f"🎉 У {len(birthday_students)} дітей день народження:\n\n"
        
        for student in birthday_students:
            age = today.year - student.birth_date.year if student.birth_date else "?"
            message += f"🎈 <b>{student.first_name} {student.last_name}</b> ({age} років)\n"
        
        message += "\n🎁 Не забудьте привітати іменинників!"
        
        # Відправляємо повідомлення через Telegram
        await self._send_telegram_message(automation.admin_chat_id, message)
        
        return {
            "message": message,
            "metrics": {"students_count": len(birthday_students)}
        }

    async def _execute_lesson_reminder(self, automation: AdminAutomation, db: AsyncSession, minutes: int) -> Dict[str, Any]:
        """Виконати нагадування про урок."""
        
        now = datetime.now()
        current_weekday = now.weekday() + 1  # SQLAlchemy використовує 1-7
        
        # Знаходимо уроки, які починаються через вказану кількість хвилин
        target_time = (now + timedelta(minutes=minutes)).time()
        
        # Діапазон ±2 хвилини для точності
        time_start = (now + timedelta(minutes=minutes-2)).time()
        time_end = (now + timedelta(minutes=minutes+2)).time()
        
        result = await db.execute(
            select(Schedule, Club, Teacher)
            .join(Club, Schedule.club_id == Club.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .where(
                Schedule.weekday == current_weekday,
                Schedule.active == True,
                Schedule.start_time >= time_start,
                Schedule.start_time <= time_end
            )
        )
        upcoming_lessons = result.all()
        
        # 🚫 НЕ ВІДПРАВЛЯЄМО СПАМ: якщо немає уроків
        if not upcoming_lessons:
            return {
                "message": f"Немає уроків через {minutes} хвилин (повідомлення НЕ відправлено)",
                "metrics": {"lessons_count": 0}
            }
        
        # ✅ ВІДПРАВЛЯЄМО ТІЛЬКИ коли є уроки
        message = f"🔔 <b>Нагадування про уроки</b>\n\n"
        message += f"⏰ Через {minutes} хвилин починаються {len(upcoming_lessons)} уроків:\n\n"
        
        for schedule, club, teacher in upcoming_lessons:
            lesson_time = schedule.start_time.strftime("%H:%M")
            message += f"📚 <b>{club.name}</b> о {lesson_time}\n"
            message += f"👨‍🏫 Вчитель: {teacher.full_name}\n\n"
        
        message += "⚡ Підготуйтеся до уроків!"
        
        await self._send_telegram_message(automation.admin_chat_id, message)
        
        return {
            "message": message,
            "metrics": {"lessons_count": len(upcoming_lessons)}
        }

    async def _execute_daily_report(self, automation: AdminAutomation, db: AsyncSession) -> Dict[str, Any]:
        """Виконати щоденний звіт."""
        
        today = date.today()
        
        # Заплановані lesson events на сьогодні
        planned_result = await db.execute(
            select(func.count(LessonEvent.id))
            .where(func.date(LessonEvent.start_at) == today)
        )
        planned_count = planned_result.scalar() or 0
        
        # Проведені уроки сьогодні
        conducted_result = await db.execute(
            select(func.count(ConductedLesson.id))
            .where(func.date(ConductedLesson.lesson_date) == today)
        )
        conducted_count = conducted_result.scalar() or 0
        
        # Загальна відвідуваність за сьогодні
        total_attendance_result = await db.execute(
            select(func.count(Attendance.id))
            .join(LessonEvent)
            .where(func.date(LessonEvent.start_at) == today)
        )
        total_attendance = total_attendance_result.scalar() or 0
        
        # Присутні студенти сьогодні
        present_result = await db.execute(
            select(func.count(Attendance.id))
            .join(LessonEvent)
            .where(
                func.date(LessonEvent.start_at) == today,
                Attendance.status == "PRESENT"
            )
        )
        present_count = present_result.scalar() or 0
        
        # Розрахунок відсотка відвідуваності
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        # Формування повідомлення
        message = f"📊 <b>Щоденний звіт за {today.strftime('%d.%m.%Y')}</b>\n\n"
        message += f"📚 <b>Уроки:</b>\n"
        message += f"• Заплановано: {planned_count}\n"
        message += f"• Проведено: {conducted_count}\n\n"
        
        message += f"👥 <b>Відвідуваність:</b>\n"
        message += f"• Всього відміток: {total_attendance}\n"
        message += f"• Присутніх: {present_count}\n"
        message += f"• Відсоток присутності: {attendance_rate:.1f}%\n\n"
        
        # Оцінка дня
        if attendance_rate >= 80:
            day_rating = "🟢 Відмінно"
        elif attendance_rate >= 60:
            day_rating = "🟡 Добре"
        else:
            day_rating = "🔴 Потребує уваги"
        
        message += f"📈 <b>Загальна оцінка дня:</b> {day_rating}"
        
        await self._send_telegram_message(automation.admin_chat_id, message)
        
        return {
            "message": message,
            "metrics": {
                "planned_lessons": planned_count,
                "conducted_lessons": conducted_count,
                "attendance_rate": attendance_rate,
                "total_attendance": total_attendance,
                "present_count": present_count
            }
        }

    async def _execute_weekly_attendance(self, automation: AdminAutomation, db: AsyncSession) -> Dict[str, Any]:
        """Виконати тижневий звіт відвідуваності."""
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Статистика за тиждень
        total_lessons_result = await db.execute(
            select(func.count(LessonEvent.id))
            .where(
                func.date(LessonEvent.start_at) >= week_start,
                func.date(LessonEvent.start_at) <= week_end
            )
        )
        total_lessons = total_lessons_result.scalar() or 0
        
        conducted_lessons_result = await db.execute(
            select(func.count(ConductedLesson.id))
            .where(
                func.date(ConductedLesson.lesson_date) >= week_start,
                func.date(ConductedLesson.lesson_date) <= week_end
            )
        )
        conducted_lessons = conducted_lessons_result.scalar() or 0
        
        # Відвідуваність за тиждень
        total_attendance_result = await db.execute(
            select(func.count(Attendance.id))
            .join(LessonEvent)
            .where(
                func.date(LessonEvent.start_at) >= week_start,
                func.date(LessonEvent.start_at) <= week_end
            )
        )
        total_attendance = total_attendance_result.scalar() or 0
        
        present_result = await db.execute(
            select(func.count(Attendance.id))
            .join(LessonEvent)
            .where(
                func.date(LessonEvent.start_at) >= week_start,
                func.date(LessonEvent.start_at) <= week_end,
                Attendance.status == "PRESENT"
            )
        )
        present_count = present_result.scalar() or 0
        
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        # ТОП 3 активних студента
        top_students_result = await db.execute(
            select(
                Student.first_name,
                Student.last_name,
                func.count(Attendance.id).label('total_classes'),
                func.sum(case((Attendance.status == "PRESENT", 1), else_=0)).label('attended')
            )
            .join(Attendance)
            .join(LessonEvent)
            .where(
                func.date(LessonEvent.start_at) >= week_start,
                func.date(LessonEvent.start_at) <= week_end
            )
            .group_by(Student.id, Student.first_name, Student.last_name)
            .having(func.count(Attendance.id) > 0)
            .order_by(func.sum(case((Attendance.status == "PRESENT", 1), else_=0)).desc())
            .limit(3)
        )
        top_students = top_students_result.fetchall()
        
        # Формування повідомлення
        message = f"📈 <b>Тижнева відвідуваність</b>\n"
        message += f"<i>{week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')}</i>\n\n"
        
        message += f"📚 <b>Уроки за тиждень:</b>\n"
        message += f"• Заплановано: {total_lessons}\n"
        message += f"• Проведено: {conducted_lessons}\n\n"
        
        message += f"👥 <b>Відвідуваність:</b>\n"
        message += f"• Всього відміток: {total_attendance}\n"
        message += f"• Присутніх: {present_count}\n"
        message += f"• Відсоток присутності: {attendance_rate:.1f}%\n\n"
        
        if top_students:
            message += f"🏆 <b>ТОП активних студентів:</b>\n"
            for i, student in enumerate(top_students, 1):
                student_rate = (student.attended / student.total_classes * 100) if student.total_classes > 0 else 0
                message += f"{i}. {student.first_name} {student.last_name}: {student_rate:.1f}% ({student.attended}/{student.total_classes})\n"
        
        await self._send_telegram_message(automation.admin_chat_id, message)
        
        return {
            "message": message,
            "metrics": {
                "total_lessons": total_lessons,
                "conducted_lessons": conducted_lessons,
                "attendance_rate": attendance_rate,
                "top_students_count": len(top_students)
            }
        }

    async def _execute_low_attendance_alert(self, automation: AdminAutomation, db: AsyncSession) -> Dict[str, Any]:
        """Виконати попередження про низьку відвідуваність."""
        
        # Аналізуємо відвідуваність за останній тиждень
        week_ago = date.today() - timedelta(days=7)
        
        # Знаходимо студентів з низькою відвідуваністю (< 60%)
        result = await db.execute(
            select(
                Student.id,
                Student.first_name,
                Student.last_name,
                func.count(Attendance.id).label('total_classes'),
                func.sum(
                    case(
                        (Attendance.status == "PRESENT", 1),
                        else_=0
                    )
                ).label('attended_classes')
            )
            .join(Attendance)
            .join(LessonEvent)
            .where(func.date(LessonEvent.start_at) >= week_ago)
            .group_by(Student.id, Student.first_name, Student.last_name)
            .having(
                func.cast(
                    func.sum(case((Attendance.status == "PRESENT", 1), else_=0)), 
                    Float
                ) / func.count(Attendance.id) < 0.6  # Менше 60%
            )
        )
        
        low_attendance_students = result.fetchall()
        
        if not low_attendance_students:
            message = "✅ <b>Відвідуваність в нормі</b>\n\nВсі студенти мають відвідуваність вище 60% за останній тиждень."
            alert_count = 0
        else:
            message = "⚠️ <b>Студенти з низькою відвідуваністю</b>\n\n"
            message += f"<i>Менше 60% за останній тиждень:</i>\n\n"
            
            for student in low_attendance_students:
                attendance_rate = (student.attended_classes / student.total_classes * 100) if student.total_classes > 0 else 0
                message += f"🔴 {student.first_name} {student.last_name}: {attendance_rate:.1f}% ({student.attended_classes}/{student.total_classes})\n"
            
            alert_count = len(low_attendance_students)

        await self._send_telegram_message(automation.admin_chat_id, message)

        return {
            "message": message,
            "metrics": {"alert_students": alert_count}
        }

    async def _execute_missing_attendance(self, automation: AdminAutomation, db: AsyncSession) -> Dict[str, Any]:
        """Виконати перевірку незаповненої відвідуваності."""
        
        # Спрощена перевірка: знаходимо всі lesson_events без attendance
        result = await db.execute(
            select(func.count(LessonEvent.id))
            .outerjoin(Attendance, LessonEvent.id == Attendance.lesson_event_id)
            .where(Attendance.id.is_(None))
        )
        missing_count = result.scalar() or 0
        
        # 🚫 НЕ ВІДПРАВЛЯЄМО СПАМ: якщо все заповнено
        if missing_count == 0:
            return {
                "message": "✅ Відвідуваність заповнена для всіх уроків (повідомлення НЕ відправлено)",
                "metrics": {"missing_lessons": 0}
            }
        
        # ✅ ВІДПРАВЛЯЄМО коли є незаповнені уроки
        message = f"❌ <b>Незаповнена відвідуваність</b>\n\n"
        message += f"⚠️ Знайдено {missing_count} уроків без відвідуваності\n\n"
        message += "🎯 Перейдіть до заповнення: /admin/attendance"
        
        await self._send_telegram_message(automation.admin_chat_id, message)
        
        return {
            "message": message,
            "metrics": {"missing_lessons": missing_count}
        }

    async def _execute_payroll_reminder(self, automation: AdminAutomation, db: AsyncSession) -> Dict[str, Any]:
        """Виконати нагадування про зарплати."""
        
        # Знаходимо conducted_lessons без нарахованої зарплати
        result = await db.execute(
            select(ConductedLesson, Teacher, Club)
            .join(Teacher, ConductedLesson.teacher_id == Teacher.id)
            .join(Club, ConductedLesson.club_id == Club.id)
            .where(ConductedLesson.is_salary_calculated == False)
            .order_by(Teacher.full_name, ConductedLesson.lesson_date)
        )
        unpaid_lessons = result.all()
        
        # 🚫 НЕ ВІДПРАВЛЯЄМО СПАМ: якщо все нараховано
        if not unpaid_lessons:
            return {
                "message": "✅ Зарплата нарахована за всі проведені уроки (повідомлення НЕ відправлено)",
                "metrics": {"unpaid_lessons": 0}
            }
        
        # Групуємо по вчителях
        teachers_summary = {}
        for lesson, teacher, club in unpaid_lessons:
            teacher_name = teacher.full_name
            if teacher_name not in teachers_summary:
                teachers_summary[teacher_name] = {
                    "lessons": 0,
                    "clubs": set(),
                    "amount": 0
                }
            
            teachers_summary[teacher_name]["lessons"] += 1
            teachers_summary[teacher_name]["clubs"].add(club.name)
            # Умовний розрахунок: 200 грн за урок (можна зробити точніше)
            teachers_summary[teacher_name]["amount"] += 200
        
        # ✅ ВІДПРАВЛЯЄМО ТІЛЬКИ коли є незараховані уроки
        message = f"💰 <b>Нагадування про зарплати</b>\n\n"
        message += f"📝 Необхідно нарахувати зарплату за {len(unpaid_lessons)} уроків:\n\n"
        
        total_amount = 0
        for teacher_name, data in teachers_summary.items():
            clubs_list = ", ".join(list(data["clubs"])[:2])  # Максимум 2 гуртки
            if len(data["clubs"]) > 2:
                clubs_list += "..."
                
            message += f"👨‍🏫 <b>{teacher_name}</b>\n"
            message += f"   📚 {data['lessons']} уроків ({clubs_list})\n"
            message += f"   💵 ~{data['amount']} грн\n\n"
            
            total_amount += data["amount"]
        
        message += f"💼 <b>Загалом:</b> {len(unpaid_lessons)} уроків, ~{total_amount} грн\n\n"
        message += "🎯 Швидке нарахування: /admin/payroll"
        
        await self._send_telegram_message(automation.admin_chat_id, message)
        
        return {
            "message": message,
            "metrics": {
                "unpaid_lessons": len(unpaid_lessons),
                "teachers_count": len(teachers_summary),
                "estimated_amount": total_amount
            }
        }

    async def _execute_basic_automation(self, automation: AdminAutomation, db: AsyncSession) -> Dict[str, Any]:
        """Базове виконання для інших типів автоматизацій."""
        
        automation_names = {
            "MISSING_ATTENDANCE": "❌ Перевірка незаповненої відвідуваності",
            "TEACHER_WORKLOAD": "👨‍🏫 Звіт про навантаження вчителів",
            "STUDENT_PROGRESS": "📚 Звіт про прогрес студентів",
            "PAYROLL_REMINDER": "💰 Нагадування про зарплати",
            "EQUIPMENT_CHECK": "🔧 Нагадування про перевірку обладнання",
            "PARENT_NOTIFICATIONS": "👪 Нагадування про зв'язок з батьками",
            "HOLIDAY_REMINDERS": "🎉 Нагадування про свята",
            "BACKUP_REMINDER": "💾 Нагадування про резервні копії",
            "SYSTEM_HEALTH": "🏥 Перевірка стану системи"
        }
        
        automation_name = automation_names.get(automation.automation_type, automation.automation_type)
        message = f"{automation_name}\n\nАвтоматизація виконана успішно!"
        
        await self._send_telegram_message(automation.admin_chat_id, message)
        
        return {
            "message": message,
            "metrics": {}
        }

    async def _send_telegram_message(self, chat_id: int, message: str):
        """Відправити повідомлення в Telegram."""
        
        try:
            from aiogram import Bot
            from app.core.settings import settings
            
            bot = Bot(token=settings.telegram_bot_token)
            await bot.send_message(
                chat_id=chat_id, 
                text=message, 
                parse_mode='HTML'
            )
            await bot.session.close()
            
            logger.info(f"✅ Повідомлення відправлено в Telegram chat {chat_id}")
            
        except Exception as e:
            logger.error(f"❌ Помилка відправки в Telegram chat {chat_id}: {e}")
            # Fallback - логуємо повідомлення
            logger.info(f"📱 Telegram message for {chat_id}: {message}")

    async def _log_execution(
        self, 
        automation_id: int, 
        status: str, 
        message: str, 
        db: AsyncSession,
        execution_time_ms: int = 0,
        metrics: Dict[str, Any] = None,
        error_details: str = None
    ):
        """Записати лог виконання автоматизації."""
        
        log_entry = AutomationLog(
            automation_id=automation_id,
            status=status,
            message=message,
            error_details=error_details,
            execution_time_ms=execution_time_ms,
            students_count=metrics.get("students_count") if metrics else None,
            clubs_count=metrics.get("clubs_count") if metrics else None
        )
        
        db.add(log_entry)
        await db.commit()


# Глобальний екземпляр сервісу
automation_service = AutomationService()