"""
🎯 Єдиний список дітей для відмітки присутності
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models import (
    LessonEvent,
    Student,
    ScheduleEnrollment,
    Attendance,
    Club,
    Schedule,
)
from app.models.lesson_event import LessonEventStatus

logger = logging.getLogger(__name__)

router = Router()

async def build_attendance_message(event: LessonEvent, db: AsyncSession) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """Build attendance message for a lesson event."""
    try:
        # ШВИДКИЙ запит студентів
        students_result = await db.execute(
            select(Student.id, Student.first_name, Student.last_name)
            .join(ScheduleEnrollment)
            .where(ScheduleEnrollment.schedule_id == event.schedule_id)
            .order_by(Student.id)
        )
        students = [(row.id, f"{row.first_name} {row.last_name}") for row in students_result]
        
        if not students:
            return "❌ Немає студентів у групі", None
        
        club_name = event.club.name if event.club else "Заняття"
        date_str = event.date.strftime("%d.%m.%Y")
        
        # ЧИСТИЙ ТЕКСТ БЕЗ часу дії
        text = f"📚 **{club_name} - {date_str}**"
        text = text + "\n\n👆 Натисніть кнопки для зміни статусу"
        
        # Кнопки для студентів
        keyboard = []
        for student_id, student_name in students:
            row = [
                InlineKeyboardButton(
                    text=f"✅ {student_name}",
                    callback_data=f"attendance_toggle_{event.id}_{student_id}_present"
                )
            ]
            keyboard.append(row)
        
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


async def send_unified_attendance_list(
    bot: Bot,
    chat_id: int,
    lesson_event_id: int
):
    """Відправляє єдиний список студентів для відмітки присутності."""
    
    try:
        async with AsyncSessionLocal() as db:
            lesson_result = await db.execute(
                select(LessonEvent)
                .options(selectinload(LessonEvent.club))
                .where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = lesson_result.scalar_one_or_none()
            
            if not lesson_event:
                await bot.send_message(chat_id, "❌ Заняття не знайдено")
                return
            
            text, reply_markup = await build_attendance_message(lesson_event, db)
            
            if reply_markup:
                await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                logger.info(f"📤 Sent attendance list for lesson_event {lesson_event_id}")
            else:
                await bot.send_message(chat_id, text)
                
    except Exception as e:
        logger.error(f"Error in send_unified_attendance_list: {e}")
        await bot.send_message(chat_id, f"❌ Помилка: {e}")


@router.callback_query(F.data.startswith("attendance_"))
async def handle_attendance_callback(callback: CallbackQuery, state: FSMContext):
    """Обробляє натискання кнопок відмітки."""
    
    chat_id = callback.message.chat.id
    user_info = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
    logger.info(f"🔥 CALLBACK START: {callback.data} | User: {user_info} | Chat: {chat_id}")
    
    try:
        data_parts = callback.data.split("_")
        
        if len(data_parts) == 3 and data_parts[1] == "finish":
            lesson_event_id = int(data_parts[2])
            logger.info(f"🏁 FINISH ATTENDANCE: lesson_event_id={lesson_event_id}")
            await finish_unified_attendance(callback, lesson_event_id)
            return
        
        if len(data_parts) == 5 and data_parts[1] == "toggle":
            _, _, lesson_event_id_str, student_id_str, current_status = data_parts
            lesson_event_id = int(lesson_event_id_str)
            student_id = int(student_id_str)
            
            logger.info(f"🔄 TOGGLE ATTENDANCE: lesson={lesson_event_id}, student={student_id}, current={current_status}")
            
            async with AsyncSessionLocal() as db:
                new_status = "absent" if current_status == "present" else "present"
                logger.info(f"📝 NEW STATUS: {current_status} → {new_status}")
                
                # ШВИДКО зберігаємо
                save_result = await save_attendance_status_fast(db, lesson_event_id, student_id, new_status, chat_id)
                logger.info(f"💾 SAVE RESULT: {save_result}")
                
                # ШВИДКО оновлюємо повідомлення
                logger.info(f"🔄 UPDATING MESSAGE...")
                await update_attendance_message_fast(callback, lesson_event_id, db)
                logger.info(f"✅ MESSAGE UPDATED")
                
                await callback.answer(f"✅ {new_status.title()}")
            return
        
        await callback.answer("❌ Невідомий формат")
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        await callback.answer("❌ Помилка")


async def save_attendance_status_fast(db: AsyncSession, lesson_event_id: int, student_id: int, status: str, marked_by: int):
    """ШВИДКЕ збереження без зайвих перевірок."""
    logger.info(f"💾 FAST SAVE START: lesson={lesson_event_id}, student={student_id}, status={status}, marked_by={marked_by}")
    try:
        from sqlalchemy.dialects.postgresql import insert
        
        attendance_status = "PRESENT" if status == "present" else "ABSENT"
        
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

        result = await db.execute(stmt)
        await db.commit()
        logger.info(f"✅ FAST save: {attendance_status} for student {student_id} | Result: {result}")
        return True

    except Exception as e:
        logger.error(f"❌ ERROR in fast save: {e}")
        await db.rollback()
        return False


async def update_attendance_message_fast(callback: CallbackQuery, lesson_event_id: int, db: AsyncSession):
    """ШВИДКЕ оновлення повідомлення."""
    logger.info(f"🔄 UPDATE MESSAGE START: lesson_event_id={lesson_event_id}")
    try:
        # ВИПРАВЛЕНИЙ запит - без selectinload для простих полів
        lesson_result = await db.execute(
            select(LessonEvent)
            .options(selectinload(LessonEvent.club))
            .where(LessonEvent.id == lesson_event_id)
        )
        lesson_event = lesson_result.scalar_one_or_none()

        if not lesson_event:
            await callback.answer("❌ Заняття не знайдено")
            return

        # ШВИДКИЙ запит студентів зі статусами
        students_with_attendance = await db.execute(
            select(
                Student.id,
                Student.first_name,
                Student.last_name,
                Attendance.status
            )
            .join(ScheduleEnrollment)
            .outerjoin(
                Attendance,
                (Attendance.lesson_event_id == lesson_event_id) &
                (Attendance.student_id == Student.id)
            )
            .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
            .order_by(Student.id)
        )

        # Будуємо ШВИДКЕ повідомлення БЕЗ часу дії
        club_name = lesson_event.club.name if lesson_event.club else "Заняття"
        date_str = lesson_event.date.strftime("%d.%m.%Y")
        
        text = f"📚 **{club_name} - {date_str}**"
        text = text + "\n\n👆 Натисніть кнопки для зміни статусу"

        keyboard = []
        for row in students_with_attendance:
            student_name = f"{row.first_name} {row.last_name}"
            
            # Логіка: якщо студент ВІДСУТНІЙ - показати ❌, інакше ✅ (за замовчуванням ПРИСУТНІЙ)
            if row.status == "ABSENT":
                button_text = f"❌ {student_name}"
                callback_data = f"attendance_toggle_{lesson_event_id}_{row.id}_absent"
            else:
                # row.status == "PRESENT" або None (за замовчуванням присутній)
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

        logger.info(f"📱 SENDING MESSAGE UPDATE with {len(keyboard)} buttons")
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"✅ MESSAGE EDIT SUCCESSFUL")

    except Exception as e:
        logger.error(f"Error in fast update: {e}")


async def save_attendance_status(db: AsyncSession, lesson_event_id: int, student_id: int, status: str, marked_by: int):
    """СТАРИЙ метод - використовуйте save_attendance_status_fast"""
    await save_attendance_status_fast(db, lesson_event_id, student_id, status, marked_by)


async def finish_unified_attendance(callback: CallbackQuery, lesson_event_id: int):
    """Завершує відмітку і показує підсумок."""
    
    try:
        async with AsyncSessionLocal() as db:
            # ВИПРАВЛЕНИЙ запит lesson event
            lesson_result = await db.execute(
                select(LessonEvent)
                .options(selectinload(LessonEvent.club))
                .where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = lesson_result.scalar_one_or_none()
            
            if not lesson_event:
                await callback.answer("❌ Заняття не знайдено")
                return
            
            # ВСІХ студентів без відмітки зберігаємо як PRESENT
            all_students_result = await db.execute(
                select(Student.id, Student.first_name, Student.last_name)
                .join(ScheduleEnrollment)
                .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
            )
            all_students = all_students_result.all()
            
            # Поточні відмітки
            attendance_result = await db.execute(
                select(Attendance.student_id, Attendance.status)
                .where(Attendance.lesson_event_id == lesson_event_id)
            )
            existing_attendance = {row.student_id: row.status for row in attendance_result}
            
            # Зберігаємо невідмічених як PRESENT
            for student in all_students:
                if student.id not in existing_attendance:
                    await save_attendance_status_fast(
                        db, lesson_event_id, student.id, "present", callback.message.chat.id
                    )
            
            # Фінальний підрахунок
            final_result = await db.execute(
                select(Student.first_name, Student.last_name, Attendance.status)
                .join(ScheduleEnrollment)
                .join(Attendance, Attendance.student_id == Student.id)
                .where(
                    ScheduleEnrollment.schedule_id == lesson_event.schedule_id,
                    Attendance.lesson_event_id == lesson_event_id
                )
            )
            
            final_data = final_result.all()
            total_count = len(all_students)
            present_count = sum(1 for row in final_data if row.status == "PRESENT")
            absent_count = total_count - present_count
            absent_students = [f"{row.first_name} {row.last_name}" for row in final_data if row.status == "ABSENT"]
            
            # Завершуємо lesson event
            await db.execute(
                update(LessonEvent)
                .where(LessonEvent.id == lesson_event_id)
                .values(
                    status=LessonEventStatus.COMPLETED,
                    completed_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            # 📚 СТВОРЮЄМО ЗАПИС ПРОВЕДЕНОГО УРОКУ (ВСЕРЕДИНІ КОНТЕКСТУ БД)
            try:
                from app.services.conducted_lesson_service import ConductedLessonService
                conducted_lesson_service = ConductedLessonService(db)
                conducted_lesson = await conducted_lesson_service.create_from_lesson_event(
                    lesson_event_id=lesson_event_id,
                    notes="Урок завершено через Telegram бот"
                )
            except Exception as e:
                logger.error(f"❌ Error creating conducted lesson: {e}")
                conducted_lesson = None
            
            if conducted_lesson:
                logger.info(f"📚 Created ConductedLesson {conducted_lesson.id} for lesson {lesson_event_id}: {conducted_lesson.present_students}/{conducted_lesson.total_students} students")
                
                # 💰 АВТОМАТИЧНЕ НАРАХУВАННЯ ЗАРПЛАТИ НА ОСНОВІ ПРОВЕДЕНОГО УРОКУ
                if conducted_lesson.is_salary_calculated:  # Виправлено назву атрибута
                    try:
                        from app.services.payroll_service import PayrollService
                        payroll_service = PayrollService(db)
                        payroll = await payroll_service.create_automatic_payroll(lesson_event_id)
                        
                        if payroll:
                            logger.info(f"💰 Auto-created payroll {payroll.id} for conducted lesson {conducted_lesson.id}: {payroll.amount_decimal} ₴")
                        else:
                            logger.info(f"💰 No payroll created for conducted lesson {conducted_lesson.id} (requirements not met)")
                            
                    except Exception as e:
                        logger.error(f"💰 Error creating automatic payroll for conducted lesson {conducted_lesson.id}: {e}")
                else:
                    logger.info(f"📚 Conducted lesson {conducted_lesson.id} not valid for salary (no present students)")
            else:
                logger.warning(f"📚 ConductedLesson not created for lesson {lesson_event_id}")
        
        # Фінальне повідомлення
        club_name = lesson_event.club.name if lesson_event.club else "Заняття"
        date_str = lesson_event.date.strftime("%d.%m.%Y")
        
        result_text = f"✅ Відмітку завершено!"
        result_text = result_text + f"\n\n📚 {club_name} - {date_str}"
        result_text = result_text + f"\n\n📊 Результати:"
        result_text = result_text + f"\n• ✅ Присутні: {present_count}"
        result_text = result_text + f"\n• ❌ Відсутні: {absent_count}"
        result_text = result_text + f"\n• 👥 Всього: {total_count}"
        
        if absent_count > 0:
            result_text = result_text + "\n\n❌ Відсутні студенти:"
            for name in absent_students:
                result_text = result_text + f"\n• {name}"
        
        await callback.message.edit_text(result_text, parse_mode="HTML")
        await callback.answer("✅ Відмітку збережено!")
            
    except Exception as e:
        logger.error(f"Error finishing attendance: {e}")
        await callback.answer("❌ Помилка при збереженні")


# Експортуємо router
unified_attendance_router = router
