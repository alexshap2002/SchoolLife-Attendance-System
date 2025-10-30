"""Telegram bot handlers."""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models import Teacher, LessonEvent, Student, Enrollment, ScheduleEnrollment, Attendance
from app.models.lesson_event import LessonEventStatus
from app.services.attendance_service import AttendanceService

router = Router()
logger = logging.getLogger(__name__)

# FSM States для відмітки присутності
class AttendanceFlow(StatesGroup):
    marking_attendance = State()

# Временне сховище сесій (в production використовуй Redis)
attendance_sessions: Dict[int, Dict] = {}


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    await message.answer(
        "🏫 Вітаю в системі обліку відвідуваності 'Школа життя'!\n\n"
        f"👤 <b>Ваш chat_id:</b> <code>{message.from_user.id}</code>\n\n"
        "📋 <b>Для вчителів:</b>\n"
        "• Скопіюйте цей chat_id\n"
        "• Перешліть адміністратору\n"
        "• Після підключення ви зможете отримувати нагадування про відмітку"
    )


@router.callback_query(F.data.startswith("toggle:"))
async def handle_attendance_toggle(callback: CallbackQuery) -> None:
    """Handle attendance toggle callback."""
    try:
        _, event_id, student_id = callback.data.split(":")
        event_id = int(event_id)
        student_id = int(student_id)
        
        async with AsyncSessionLocal() as db:
            attendance_service = AttendanceService(db)
            
            # Verify teacher ownership
            result = await db.execute(
                select(LessonEvent)
                .options(selectinload(LessonEvent.teacher))
                .where(LessonEvent.id == event_id)
            )
            lesson_event = result.scalar_one_or_none()
            
            if not lesson_event or lesson_event.teacher.tg_chat_id != callback.from_user.id:
                await callback.answer("Помилка: це не ваше заняття!", show_alert=True)
                return
            
            # Toggle attendance
            await attendance_service.toggle_attendance(event_id, student_id)
            
            # Update keyboard
            keyboard = await _build_attendance_keyboard(db, event_id)
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            await callback.answer("Відвідуваність оновлено")
            
    except Exception as e:
        logger.error(f"Error handling attendance toggle: {e}")
        await callback.answer("Помилка при оновленні відвідуваності", show_alert=True)


@router.callback_query(F.data.startswith("save:"))
async def handle_attendance_save(callback: CallbackQuery) -> None:
    """Handle attendance save callback."""
    try:
        _, event_id = callback.data.split(":")
        event_id = int(event_id)
        
        async with AsyncSessionLocal() as db:
            attendance_service = AttendanceService(db)
            
            # Verify teacher ownership
            result = await db.execute(
                select(LessonEvent)
                .options(selectinload(LessonEvent.teacher), selectinload(LessonEvent.club))
                .where(LessonEvent.id == event_id)
            )
            lesson_event = result.scalar_one_or_none()
            
            if not lesson_event or lesson_event.teacher.tg_chat_id != callback.from_user.id:
                await callback.answer("Помилка: це не ваше заняття!", show_alert=True)
                return
            
            # Save attendance
            await attendance_service.save_attendance(event_id, str(callback.from_user.id))
            
            await callback.message.edit_text(
                f"✅ Відвідуваність збережено!\n"
                f"Заняття: {lesson_event.club.name}\n"
                f"Дата: {lesson_event.date}\n"
                f"Вчитель: {lesson_event.teacher.full_name}"
            )
            await callback.answer("Відвідуваність успішно збережено!")
            
    except Exception as e:
        logger.error(f"Error saving attendance: {e}")
        await callback.answer("Помилка при збереженні відвідуваності", show_alert=True)


@router.callback_query(F.data.startswith("swipe_"))
async def handle_swipe_action(callback: CallbackQuery):
    """Handle swipe actions for attendance."""
    try:
        data_parts = callback.data.split(":")
        action = data_parts[0]  # swipe_present, swipe_absent, swipe_next, swipe_finish
        lesson_event_id = int(data_parts[1])
        
        # Verify teacher
        if not callback.from_user:
            await callback.answer("❌ Помилка авторизації")
            return
            
        teacher_id = callback.from_user.id
        
        async with AsyncSessionLocal() as session:
            attendance_service = AttendanceService(session)
            
            # Verify teacher has access to this lesson
            lesson_event = await session.get(LessonEvent, lesson_event_id)
            if not lesson_event:
                await callback.answer("❌ Подія не знайдена")
                return
                
            if lesson_event.schedule.teacher.tg_chat_id != teacher_id:
                await callback.answer("❌ У вас немає доступу до цієї події")
                return
            
            # Get students for this schedule
            students_query = select(Student).join(ScheduleEnrollment).where(
                ScheduleEnrollment.schedule_id == lesson_event.schedule_id
            ).order_by(Student.first_name, Student.last_name)
            students_result = await session.execute(students_query)
            students = students_result.scalars().all()
            
            if action == "swipe_finish":
                # Finish attendance
                lesson_event.status = LessonEventStatus.COMPLETED
                lesson_event.completed_at = datetime.now(timezone.utc)
                await session.commit()
                
                await callback.answer("✅ Відмітка завершена!")
                await callback.message.edit_text(
                    f"✅ **ВІДМІТКА ЗАВЕРШЕНА**\n\n"
                    f"📅 Дата: {lesson_event.date}\n"
                    f"🏫 Клас: {lesson_event.schedule.club.name}\n"
                    f"👨‍🏫 Вчитель: {lesson_event.schedule.teacher.full_name}\n"
                    f"⏰ Завершено: {lesson_event.completed_at.strftime('%H:%M')}"
                )
                return
            
            current_student_id = int(data_parts[2]) if len(data_parts) > 2 else None
            current_student_index = 0
            
            # Find current student index
            for i, student in enumerate(students):
                if student.id == current_student_id:
                    current_student_index = i
                    break
            
            # Handle attendance actions
            if action in ["swipe_present", "swipe_absent"]:
                if current_student_id:
                    status = "PRESENT" if action == "swipe_present" else "ABSENT"
                    await attendance_service.update_attendance(
                        lesson_event_id, current_student_id, status
                    )
                    await session.commit()
                    
                    status_text = "✅ Присутній" if status == "PRESENT" else "❌ Відсутній"
                    await callback.answer(f"{status_text}")
                    
                    # Auto-advance to next student
                    current_student_index += 1
            
            elif action == "swipe_next":
                current_student_index += 1
                await callback.answer("⏭️ Наступний студент")
            
            # Show next student or finish if at end
            if current_student_index >= len(students):
                # All students processed, show completion
                lesson_event.status = LessonEventStatus.COMPLETED
                lesson_event.completed_at = datetime.now(timezone.utc)
                await session.commit()
                
                await callback.message.edit_text(
                    f"🎉 **ВСІ СТУДЕНТИ ВІДМІЧЕНІ!**\n\n"
                    f"📅 Дата: {lesson_event.date}\n"
                    f"🏫 Клас: {lesson_event.schedule.club.name}\n"
                    f"👨‍🏫 Вчитель: {lesson_event.schedule.teacher.full_name}\n"
                    f"👥 Всього студентів: {len(students)}\n"
                    f"⏰ Завершено: {lesson_event.completed_at.strftime('%H:%M')}"
                )
                return
            
            # Show next student card
            next_student = students[current_student_index]
            
            # Get current attendance status
            attendance_query = select(Attendance).where(
                Attendance.lesson_event_id == lesson_event_id,
                Attendance.student_id == next_student.id
            )
            attendance_result = await session.execute(attendance_query)
            attendance = attendance_result.scalar_one_or_none()
            attendance_status = attendance.status if attendance else "NOT_MARKED"
            
            card = await _build_swipe_card(next_student, attendance_status, lesson_event_id)
            
            # Add progress indicator
            progress_text = f"\n\n📊 Прогрес: {current_student_index + 1}/{len(students)}"
            card["text"] += progress_text
            
            await callback.message.edit_text(
                text=card["text"],
                reply_markup=card["reply_markup"]
            )
            
    except Exception as e:
        logger.error(f"Error handling swipe action: {e}")
        await callback.answer("❌ Помилка обробки дії")


async def send_attendance_checklist(chat_id: int, lesson_event_id: int) -> None:
    """Send attendance checklist to teacher using quick keyboard system."""
    from app.bot import create_bot
    from app.bot.quick_attendance import send_quick_attendance_invitation
    
    async with AsyncSessionLocal() as db:
        try:
            # Get lesson event with related data
            result = await db.execute(
                select(LessonEvent)
                .where(LessonEvent.id == lesson_event_id)
                .options(
                    selectinload(LessonEvent.club),
                    selectinload(LessonEvent.teacher),
                )
            )
            lesson_event = result.scalar_one_or_none()
            
            if not lesson_event:
                logger.error(f"Lesson event {lesson_event_id} not found")
                return
            
            # Get enrolled students for this schedule
            result = await db.execute(
                select(Student)
                .join(ScheduleEnrollment)
                .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
                .order_by(Student.first_name, Student.last_name)
            )
            students = result.scalars().all()
            
            if not students:
                logger.warning(f"No students enrolled in club {lesson_event.club.name}")
                return
            
            # Create bot instance
            bot = create_bot()
            
            # Формуємо інформацію про заняття
            lesson_info = f"📚 {lesson_event.club.name}\n👤 Вчитель: {lesson_event.teacher.full_name}\n📅 Дата: {lesson_event.date.strftime('%d.%m.%Y')}\n👥 Студентів: {len(students)}"
            
            # Відправляємо запрошення для швидкої відмітки
            await send_quick_attendance_invitation(
                chat_id=chat_id,
                lesson_event_id=lesson_event_id,
                lesson_info=lesson_info,
                bot=bot
            )
            return
            
            # Build keyboard
            keyboard = await _build_attendance_keyboard(db, lesson_event_id)
            
            # Create attendance records if they don't exist
            from app.services.attendance_service import AttendanceService
            attendance_service = AttendanceService(db)
            await attendance_service.create_default_attendance(lesson_event_id)
            
            # Send message via bot
            bot = create_bot()
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
            
            logger.info(f"Sent attendance checklist to {chat_id} for event {lesson_event_id}")
            
        except Exception as e:
            logger.error(f"Error sending attendance checklist: {e}")


async def _build_attendance_keyboard(
    db: AsyncSession, lesson_event_id: int
) -> InlineKeyboardMarkup:
    """Build attendance keyboard for lesson event."""
    # Get students and current attendance
    result = await db.execute(
        select(Student, Attendance.status)
        .join(ScheduleEnrollment)
        .join(LessonEvent, LessonEvent.schedule_id == ScheduleEnrollment.schedule_id)
        .outerjoin(
            Attendance, 
            (Attendance.lesson_event_id == lesson_event_id) & 
            (Attendance.student_id == Student.id)
        )
        .where(LessonEvent.id == lesson_event_id)
        .order_by(Student.first_name, Student.last_name)
    )
    
    students_attendance = result.all()
    
    # Build keyboard buttons
    buttons = []
    for student, attendance_status in students_attendance:
        if attendance_status == "present":
            icon = "✅"
        else:
            icon = "❌"
        
        button_text = f"{icon} {student.first_name} {student.last_name}"
        callback_data = f"toggle:{lesson_event_id}:{student.id}"
        
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=callback_data
            )
        ])
    
    # Add save button
    buttons.append([
        InlineKeyboardButton(
            text="💾 Зберегти",
            callback_data=f"save:{lesson_event_id}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _get_student_avatar(gender: Optional[str]) -> str:
    """Get emoji avatar based on student gender."""
    if gender == "male":
        return "👦"
    elif gender == "female":
        return "👧"
    else:
        return "🧒"  # neutral for unknown gender


async def _build_swipe_card(student, attendance_status: str, lesson_event_id: int) -> dict:
    """Build swipe card for a student."""
    avatar = _get_student_avatar(student.gender)
    
    # Status indicators
    if attendance_status == "PRESENT":
        status_emoji = "✅"
        status_text = "Присутній"
    elif attendance_status == "ABSENT":
        status_emoji = "❌"
        status_text = "Відсутній"
    else:
        status_emoji = "❓"
        status_text = "Не відмічено"
    
    card_text = f"""
{avatar} {student.full_name}

{status_emoji} {status_text}

👆 Свайп вгору = Присутній
👇 Свайп вниз = Відсутній
    """.strip()
    
    # Create inline keyboard for swipe actions
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Присутній",
                callback_data=f"swipe_present:{lesson_event_id}:{student.id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Відсутній", 
                callback_data=f"swipe_absent:{lesson_event_id}:{student.id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏭️ Наступний",
                callback_data=f"swipe_next:{lesson_event_id}:{student.id}"
            ),
            InlineKeyboardButton(
                text="💾 Завершити",
                callback_data=f"swipe_finish:{lesson_event_id}"
            )
        ]
    ])
    
    return {
        "text": card_text,
        "reply_markup": keyboard
    }


async def send_swipe_attendance_cards(chat_id: int, lesson_event_id: int):
    """Send swipe-style attendance cards interface."""
    try:
        bot = create_bot()
        async with AsyncSessionLocal() as session:
            attendance_service = AttendanceService(session)
            
            # Get lesson event
            lesson_event = await session.get(LessonEvent, lesson_event_id)
            if not lesson_event:
                await bot.send_message(chat_id, "❌ Подія не знайдена")
                return
            
            # Get students enrolled in this schedule
            students_query = select(Student).join(ScheduleEnrollment).where(
                ScheduleEnrollment.schedule_id == lesson_event.schedule_id
            )
            students_result = await session.execute(students_query)
            students = students_result.scalars().all()
            
            if not students:
                await bot.send_message(chat_id, "❌ Немає студентів для цього розкладу")
                return
            
            # Create or get attendance records
            await attendance_service.create_default_attendance(lesson_event_id)
            
            # Get current attendance statuses
            attendance_query = select(Attendance).where(
                Attendance.lesson_event_id == lesson_event_id
            )
            attendance_result = await session.execute(attendance_query)
            attendance_records = {att.student_id: att.status for att in attendance_result.scalars().all()}
            
            # Send intro message
            intro_text = f"""
🎯 **SWIPE ВІДМІТКА ПРИСУТНОСТІ**

📅 **Дата:** {lesson_event.date}
🏫 **Клас:** {lesson_event.schedule.club.name}
👨‍🏫 **Вчитель:** {lesson_event.schedule.teacher.full_name}

👆 **Свайп вгору** = Дитина присутня
👇 **Свайп вниз** = Дитина відсутня

Всього студентів: {len(students)}
            """.strip()
            
            await bot.send_message(
                chat_id=chat_id,
                text=intro_text,
                parse_mode="Markdown"
            )
            
            # Send first student card
            if students:
                first_student = students[0]
                attendance_status = attendance_records.get(first_student.id, "NOT_MARKED")
                
                card = await _build_swipe_card(first_student, attendance_status, lesson_event_id)
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=card["text"],
                    reply_markup=card["reply_markup"]
                )
            
            await bot.session.close()
            
    except Exception as e:
        logger.error(f"Error sending swipe cards: {e}")
        try:
            await bot.send_message(chat_id, f"❌ Помилка: {e}")
            await bot.session.close()
        except:
            pass
