import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
import httpx

from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.settings import settings
from app.models import LessonEvent, Student, ScheduleEnrollment, Club, Attendance, Enrollment
from app.models.attendance import AttendanceStatus
from app.models.lesson_event import LessonEventStatus
from app.workers.automation_scheduler import start_automation_scheduler, stop_automation_scheduler

logger = logging.getLogger(__name__)


class TelegramBotDispatcher:
    def __init__(self):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.running = False
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup callback handlers."""
        # Обробник для attendance callbacks
        @self.dp.callback_query(F.data.startswith("attendance_"))
        async def handle_attendance_callback(callback: CallbackQuery):
            await self._handle_attendance_callback(callback)
        
        # Універсальний обробник для всіх інших callbacks
        @self.dp.callback_query()
        async def handle_any_callback(callback: CallbackQuery):
            await self._handle_any_callback(callback)
        
    async def start_polling(self):
        """Start the dispatcher polling loop."""
        self.running = True
        logger.info("🚀 Starting Telegram dispatcher polling...")
        
        # Запускаємо планувальник автоматизацій
        try:
            await start_automation_scheduler()
            logger.info("✅ Automation scheduler started")
        except Exception as e:
            logger.error(f"Failed to start automation scheduler: {e}")
        
        # Запускаємо aiogram polling для callback'ів
        aiogram_task = asyncio.create_task(self.dp.start_polling(self.bot))
        logger.info("✅ Aiogram polling started for callbacks")
        
        # Polling loop для відправки повідомлень
        try:
            while self.running:
                try:
                    await self._poll_and_send()
                    await asyncio.sleep(30)  # Poll every 30 seconds (знижуємо навантаження на БД)
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
        finally:
            # Зупиняємо aiogram polling
            aiogram_task.cancel()
            try:
                await aiogram_task
            except asyncio.CancelledError:
                pass
    
    async def stop_polling(self):
        """Stop the dispatcher."""
        self.running = False
        
        # Зупиняємо планувальник автоматизацій
        try:
            await stop_automation_scheduler()
            logger.info("✅ Automation scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop automation scheduler: {e}")
        
        await self.bot.session.close()
        logger.info("🛑 Telegram dispatcher stopped")
    
    async def _poll_and_send(self):
        """Poll for due lesson events and send notifications."""
        try:
            async with AsyncSessionLocal() as db:
                # Get events that need to be sent
                current_time = datetime.now(timezone.utc)
                
                result = await db.execute(
                    select(LessonEvent)
                    .options(
                        selectinload(LessonEvent.club),
                        selectinload(LessonEvent.teacher)
                    )
                    .where(
                        LessonEvent.status == LessonEventStatus.PLANNED,
                        LessonEvent.notify_at <= current_time,
                        LessonEvent.sent_at.is_(None)
                    )
                    .order_by(LessonEvent.notify_at.asc())  # Обробляємо найстаріші події спочатку
                    .with_for_update(skip_locked=True)
                    .limit(30)  # Збільшено з 10 до 30 для швидшої обробки черги
                )
                
                events = result.scalars().all()
                
                for event in events:
                    await self._send_attendance_notification(event, db)
                    
        except Exception as e:
            logger.error(f"Error in poll_and_send: {e}")
    
    async def _send_attendance_notification(self, event: LessonEvent, db: AsyncSession):
        """Send attendance notification for a lesson event."""
        try:
            if not event.teacher_chat_id:
                logger.error(f"No teacher chat_id for event {event.id}")
                return
            
            text, reply_markup = await self.build_attendance_message(event, db)
            
            if reply_markup:
                await self.bot.send_message(
                    chat_id=event.teacher_chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                
                # Mark as sent
                await db.execute(
                    update(LessonEvent)
                    .where(LessonEvent.id == event.id)
                    .values(
                        sent_at=datetime.now(timezone.utc),
                        status=LessonEventStatus.SENT
                    )
                )
                await db.commit()
                
                logger.info(f"✅ Sent notification for lesson_event {event.id}")
            else:
                # ВАЖЛИВА ВАЛІДАЦІЯ: якщо немає студентів - переводимо подію в SKIPPED
                logger.warning(f"⚠️ No students found for event {event.id}, marking as SKIPPED")
                await db.execute(
                    update(LessonEvent)
                    .where(LessonEvent.id == event.id)
                    .values(
                        status=LessonEventStatus.SKIPPED,
                        last_error="No students in schedule"
                    )
                )
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error sending notification for event {event.id}: {e}")
            await db.rollback()
    
    async def build_attendance_message(self, event: LessonEvent, db: AsyncSession) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Build attendance message з урахуванням існуючих статусів."""
        try:
            # Отримуємо студентів зі статусами attendance
            # Отримуємо студентів через конкретні ScheduleEnrollment (запис на групу)
            students_result = await db.execute(
                select(
                    Student.id,
                    Student.first_name,
                    Student.last_name,
                    Attendance.status
                )
                .join(ScheduleEnrollment, ScheduleEnrollment.student_id == Student.id)
                .outerjoin(
                    Attendance,
                    (Attendance.lesson_event_id == event.id) &
                    (Attendance.student_id == Student.id)
                )
                .where(ScheduleEnrollment.schedule_id == event.schedule_id)
                .order_by(Student.id)
            )
            students = students_result.fetchall()
            
            if not students:
                return "❌ Немає студентів у групі", None
            
            club_name = event.club.name if event.club else "Заняття"
            date_str = event.date.strftime("%d.%m.%Y")
            
            text = f"📚 **{club_name} - {date_str}**"
            text = text + "\n\n👆 Натисніть кнопки для зміни статусу"
            
            # Кнопки для студентів з урахуванням поточних статусів
            keyboard = []
            for row in students:
                student_name = f"{row.first_name} {row.last_name}"
                
                # Визначаємо поточний статус і відповідну кнопку
                if row.status == AttendanceStatus.ABSENT:
                    button_text = f"❌ {student_name}"
                    callback_data = f"attendance_toggle_{event.id}_{row.id}_absent"
                else:
                    # За замовчуванням або PRESENT
                    button_text = f"✅ {student_name}"
                    callback_data = f"attendance_toggle_{event.id}_{row.id}_present"
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=callback_data
                    )
                ])
            
            # Кнопка завершення
            keyboard.append([
                InlineKeyboardButton(
                    text="🏁 Завершити відмітку",
                    callback_data=f"attendance_finish_{event.id}"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            return text, reply_markup
            
        except Exception as e:
            logger.error(f"Error building attendance message: {e}")
            return f"❌ Помилка: {e}", None
    
    async def _handle_attendance_callback(self, callback: CallbackQuery):
        """Handle attendance callback from dispatcher."""
        chat_id = callback.message.chat.id
        user_info = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
        logger.info(f"🔥🔥🔥 DISPATCHER CALLBACK: {callback.data} | User: {user_info} | Chat: {chat_id}")
        
        try:
            data_parts = callback.data.split("_")
            
            if len(data_parts) == 3 and data_parts[1] == "finish":
                lesson_event_id = int(data_parts[2])
                logger.info(f"🏁 FINISH ATTENDANCE: lesson_event_id={lesson_event_id}")
                await self._finish_attendance(callback, lesson_event_id)
                return
            
            if len(data_parts) == 5 and data_parts[1] == "toggle":
                _, _, lesson_event_id_str, student_id_str, current_status = data_parts
                lesson_event_id = int(lesson_event_id_str)
                student_id = int(student_id_str)
                
                logger.info(f"🔄 TOGGLE ATTENDANCE: lesson={lesson_event_id}, student={student_id}, current={current_status}")
                
                async with AsyncSessionLocal() as db:
                    new_status = "absent" if current_status == "present" else "present"
                    logger.info(f"📝 NEW STATUS: {current_status} → {new_status}")
                    
                    # Зберігаємо attendance
                    save_result = await self._save_attendance_status(db, lesson_event_id, student_id, new_status, chat_id)
                    logger.info(f"💾 SAVE RESULT: {save_result}")
                    
                    # Оновлюємо повідомлення
                    logger.info(f"🔄 UPDATING MESSAGE...")
                    await self._update_attendance_message(callback, lesson_event_id, db)
                    logger.info(f"✅ MESSAGE UPDATED")
                    
                    await callback.answer(f"✅ {new_status.title()}")
                return
            
            await callback.answer("❌ Невідомий формат")
            
        except Exception as e:
            logger.error(f"Error in attendance callback: {e}")
            await callback.answer("❌ Помилка")
    
    async def _handle_any_callback(self, callback: CallbackQuery):
        """Handle any other callback for debugging."""
        logger.info(f"🔍 OTHER CALLBACK: {callback.data} | User: @{callback.from_user.username}")
        await callback.answer("✅ Отримано")
    
    async def _save_attendance_status(self, db: AsyncSession, lesson_event_id: int, student_id: int, status: str, marked_by: int):
        """Save attendance status to database and sync with API."""
        try:
            from sqlalchemy.dialects.postgresql import insert
            
            attendance_status = AttendanceStatus.PRESENT if status == "present" else AttendanceStatus.ABSENT
            
            # 1. Зберігаємо в БД (локально в dispatcher)
            stmt = insert(Attendance).values(
                lesson_event_id=lesson_event_id,
                student_id=student_id,
                status=attendance_status,
                marked_by=marked_by,
                marked_at=datetime.now(timezone.utc)
            )
            
            stmt = stmt.on_conflict_do_update(
                constraint="attendance_lesson_student_unique",
                set_=dict(
                    status=stmt.excluded.status,
                    marked_by=stmt.excluded.marked_by,
                    marked_at=stmt.excluded.marked_at
                )
            )
            
            await db.execute(stmt)
            await db.commit()
            logger.info(f"✅ Saved to DB: {attendance_status} for student {student_id}")
            
            # 2. Синхронізуємо з основною системою через API
            api_result = await self._sync_attendance_with_api(lesson_event_id, student_id, status.upper(), marked_by)
            logger.info(f"🔄 API sync result: {api_result}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving attendance: {e}")
            await db.rollback()
            return False
    
    async def _sync_attendance_with_api(self, lesson_event_id: int, student_id: int, status: str, marked_by: int):
        """Синхронізуємо attendance з основною системою через API."""
        try:
            async with httpx.AsyncClient() as client:
                # Викликаємо API endpoint для створення/оновлення attendance
                api_data = {
                    "lesson_event_id": lesson_event_id,
                    "student_id": student_id,
                    "status": status,  # "PRESENT" або "ABSENT"
                    "marked_by": marked_by,
                    "update_if_exists": True  # Дозволяємо оновлення
                }
                
                # Викликаємо webapp API (з контейнера до контейнера)
                response = await client.post(
                    "http://school-webapp:8000/api/attendance",
                    json=api_data,
                    timeout=10.0
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ API sync successful: {response.status_code}")
                    return True
                else:
                    logger.warning(f"⚠️ API sync failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error syncing with API: {e}")
            return False
    
    async def _update_attendance_message(self, callback: CallbackQuery, lesson_event_id: int, db: AsyncSession):
        """Update attendance message with new statuses."""
        try:
            # Отримуємо lesson_event з club
            lesson_result = await db.execute(
                select(LessonEvent)
                .options(selectinload(LessonEvent.club))
                .where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = lesson_result.scalar_one_or_none()
            
            if not lesson_event:
                await callback.answer("❌ Заняття не знайдено")
                return
            
            # Отримуємо студентів зі статусами
            # Отримуємо студентів через конкретні ScheduleEnrollment (запис на групу)
            students_with_attendance = await db.execute(
                select(
                    Student.id,
                    Student.first_name,
                    Student.last_name,
                    Attendance.status
                )
                .join(ScheduleEnrollment, ScheduleEnrollment.student_id == Student.id)
                .outerjoin(
                    Attendance,
                    (Attendance.lesson_event_id == lesson_event_id) &
                    (Attendance.student_id == Student.id)
                )
                .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
                .order_by(Student.id)
            )
            
            # Будуємо повідомлення
            club_name = lesson_event.club.name if lesson_event.club else "Заняття"
            date_str = lesson_event.date.strftime("%d.%m.%Y")
            
            text = f"📚 **{club_name} - {date_str}**"
            text = text + "\n\n👆 Натисніть кнопки для зміни статусу"
            
            keyboard = []
            for row in students_with_attendance:
                student_name = f"{row.first_name} {row.last_name}"
                
                # Логіка: якщо студент ВІДСУТНІЙ - показати ❌, інакше ✅
                if row.status == AttendanceStatus.ABSENT:
                    button_text = f"❌ {student_name}"
                    callback_data = f"attendance_toggle_{lesson_event_id}_{row.id}_absent"
                else:
                    # row.status == AttendanceStatus.PRESENT або None (за замовчуванням присутній)
                    button_text = f"✅ {student_name}"
                    callback_data = f"attendance_toggle_{lesson_event_id}_{row.id}_present"
                
                keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
            
            # Кнопка завершення
            keyboard.append([
                InlineKeyboardButton(
                    text="🏁 Завершити відмітку",
                    callback_data=f"attendance_finish_{lesson_event_id}"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            logger.info(f"📱 Updating message with {len(keyboard)} buttons")
            await callback.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error updating message: {e}")
    
    async def _finish_attendance(self, callback: CallbackQuery, lesson_event_id: int):
        """Finish attendance marking - створює conducted lesson і payroll."""
        try:
            async with AsyncSessionLocal() as db:
                # 1. Використовуємо AttendanceService для завершення (створює payroll)
                from app.services.attendance_service import AttendanceService
                attendance_service = AttendanceService(db)
                chat_id = callback.from_user.id  # Передаємо як int, не str
                
                await attendance_service.save_attendance(lesson_event_id, chat_id)
                logger.info(f"✅ Completed lesson_event {lesson_event_id} with payroll")
                
                # 2. Створюємо ConductedLesson
                from app.services.conducted_lesson_service import ConductedLessonService
                conducted_service = ConductedLessonService(db)
                conducted_lesson = await conducted_service.create_from_lesson_event(lesson_event_id)
                
                if conducted_lesson:
                    logger.info(f"✅ Created ConductedLesson {conducted_lesson.id}")
                
                # 3. Отримуємо статистику для повідомлення
                result_message = await self._build_completion_message(db, lesson_event_id)
                
                await callback.message.edit_text(
                    result_message,
                    reply_markup=None,
                    parse_mode="Markdown"
                )
                await callback.answer("✅ Відмітку завершено!")
                
        except Exception as e:
            logger.error(f"Error finishing attendance: {e}")
            await callback.message.edit_text(
                "❌ Помилка завершення відмітки.\nСпробуйте ще раз.",
                reply_markup=None
            )
            await callback.answer("❌ Помилка завершення")
    
    async def _build_completion_message(self, db: AsyncSession, lesson_event_id: int) -> str:
        """Будує фінальне повідомлення з результатами."""
        try:
            # Отримуємо lesson_event з club
            lesson_result = await db.execute(
                select(LessonEvent)
                .options(selectinload(LessonEvent.club))
                .where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = lesson_result.scalar_one_or_none()
            
            if not lesson_event:
                return "❌ Помилка: заняття не знайдено"
            
            # Отримуємо студентів через конкретні ScheduleEnrollment (запис на групу)
            students_result = await db.execute(
                select(
                    Student.id,
                    Student.first_name,
                    Student.last_name,
                    Attendance.status
                )
                .join(ScheduleEnrollment, ScheduleEnrollment.student_id == Student.id)
                .outerjoin(
                    Attendance,
                    (Attendance.lesson_event_id == lesson_event_id) &
                    (Attendance.student_id == Student.id)
                )
                .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
                .order_by(Student.first_name)
            )
            students_data = students_result.fetchall()
            
            # Рахуємо статистику з ПРАВИЛЬНОЮ логікою
            present_students = []
            absent_students = []
            
            for student_id, first_name, last_name, attendance_status in students_data:
                full_name = f"{first_name} {last_name}"
                
                # ЛОГІКА: якщо немає запису attendance → студент ПРИСУТНІЙ за замовчуванням
                if attendance_status is None or attendance_status == AttendanceStatus.PRESENT:
                    present_students.append(full_name)
                else:
                    absent_students.append(full_name)
            
            total = len(students_data)
            present_count = len(present_students)
            absent_count = len(absent_students)
            
            # Будуємо повідомлення
            club_name = lesson_event.club.name if lesson_event.club else "Заняття"
            date_str = lesson_event.date.strftime("%d.%m.%Y")
            
            message = f"✅ **Відмітку завершено!**\n\n"
            message += f"📚 **{club_name} - {date_str}**\n\n"
            message += f"📊 **Результати:**\n"
            message += f"• ✅ Присутні: {present_count}\n"
            message += f"• ❌ Відсутні: {absent_count}\n"
            message += f"• 👥 Всього: {total}\n"
            
            if absent_students:
                message += f"\n❌ **Відсутні студенти:**\n"
                for student in absent_students:
                    message += f"• {student}\n"
            
            if present_students:
                message += f"\n✅ **Присутні студенти:**\n"
                for student in present_students:
                    message += f"• {student}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error building completion message: {e}")
            return "✅ Відмітку завершено!\nДякуємо за роботу."


async def main():
    """Main dispatcher function."""
    dispatcher = TelegramBotDispatcher()
    
    try:
        await dispatcher.start_polling()
    except KeyboardInterrupt:
        logger.info("Received stop signal")
    finally:
        await dispatcher.stop_polling()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
