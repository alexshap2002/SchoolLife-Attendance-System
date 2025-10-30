"""Швидка відмітка присутності через Reply Keyboard."""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import Teacher, LessonEvent, Student, ScheduleEnrollment, Attendance
from app.models.lesson_event import LessonEventStatus
from app.services.attendance_service import AttendanceService

router = Router()
logger = logging.getLogger(__name__)

# FSM States для відмітки присутності
class AttendanceFlow(StatesGroup):
    marking_attendance = State()

# Временне сховище сесій (в production використовуй Redis)
attendance_sessions: Dict[int, Dict] = {}

def create_attendance_keyboard():
    """Створює клавіатуру для швидкої відмітки присутності."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Присутній"),
                KeyboardButton(text="❌ Відсутній")
            ],
            [
                KeyboardButton(text="📋 Завершити")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

async def start_quick_attendance(chat_id: int, lesson_event_id: int, bot: Bot):
    """Розпочинає швидку відмітку через Reply Keyboard."""
    
    try:
        async with AsyncSessionLocal() as db:
            # Отримуємо lesson event та студентів
            result = await db.execute(
                select(LessonEvent).where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = result.scalar_one_or_none()
            
            if not lesson_event:
                await bot.send_message(chat_id, "❌ Заняття не знайдено")
                return
            
            # Отримуємо студентів
            students_result = await db.execute(
                select(Student)
                .join(ScheduleEnrollment, Student.id == ScheduleEnrollment.student_id)
                .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
                .order_by(Student.first_name, Student.last_name)
            )
            students = students_result.scalars().all()
            
            if not students:
                await bot.send_message(chat_id, "❌ Студенти не знайдені для цього заняття")
                return
            
            # Створюємо дефолтні записи відвідування якщо їх немає
            attendance_service = AttendanceService(db)
            await attendance_service.create_default_attendance(lesson_event_id)
            
            # Ініціалізуємо сесію
            attendance_sessions[chat_id] = {
                'lesson_event_id': lesson_event_id,
                'students': [{'id': s.id, 'name': f"{s.first_name} {s.last_name}", 'age': s.age} for s in students],
                'current_index': 0,
                'marked_count': 0,
                'total_count': len(students)
            }
            
            # Показуємо першого студента
            await show_current_student(chat_id, bot)
            
    except Exception as e:
        logger.error(f"Error starting quick attendance: {e}")
        await bot.send_message(chat_id, f"❌ Помилка: {e}")

async def show_current_student(chat_id: int, bot: Bot):
    """Показує поточного студента для відмітки."""
    session = attendance_sessions.get(chat_id)
    if not session:
        await bot.send_message(chat_id, "❌ Сесія втрачена. Спробуйте почати знову.")
        return
    
    current_index = session['current_index']
    students = session['students']
    
    if current_index >= len(students):
        await finish_attendance(chat_id, bot)
        return
    
    student = students[current_index]
    progress = f"{current_index + 1}/{len(students)}"
    
    text = f"""
📚 **Відмітка присутності**

👤 **{student['name']}** ({student['age']} років)

📊 Прогрес: {progress}
✅ Відмічено: {session['marked_count']}

Учень присутній чи відсутній?
"""
    
    keyboard = create_attendance_keyboard()
    
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.message(F.text.in_(["✅ Присутній", "❌ Відсутній"]))
async def handle_attendance_button(message: Message):
    """Обробляє натискання кнопок відмітки."""
    chat_id = message.chat.id
    session = attendance_sessions.get(chat_id)
    
    if not session:
        await message.answer("❌ Сесія відмітки не активна.")
        return
    
    try:
        async with AsyncSessionLocal() as db:
            current_student = session['students'][session['current_index']]
            lesson_event_id = session['lesson_event_id']
            
            # Обробляємо вибір
            if message.text == "✅ Присутній":
                status = "PRESENT"
                response = "✅ Присутній"
            elif message.text == "❌ Відсутній":
                status = "ABSENT"
                response = "❌ Відсутній"
            
            # Завжди збільшуємо лічильник відмічених
            session['marked_count'] += 1
            
            # Зберігаємо відмітку в базу (завжди зберігаємо)
            await db.execute(
                update(Attendance)
                .where(
                    Attendance.lesson_event_id == lesson_event_id,
                    Attendance.student_id == current_student['id']
                )
                .values(
                    status=status,
                    marked_at=datetime.utcnow(),
                    marked_by=chat_id  # chat_id як marked_by
                )
            )
            await db.commit()
            
            # Показуємо швидкий фідбек
            await message.answer(f"{response} - {current_student['name']}")
            
            # Переходимо до наступного студента
            session['current_index'] += 1
            await show_current_student(chat_id, message.bot)
            
    except Exception as e:
        logger.error(f"Error handling attendance button: {e}")
        await message.answer(f"❌ Помилка: {e}")

@router.message(F.text == "📋 Завершити")
async def handle_finish_attendance(message: Message):
    """Завершує відмітку присутності."""
    await finish_attendance(message.chat.id, message.bot)

async def finish_attendance(chat_id: int, bot: Bot):
    """Завершує процес відмітки присутності."""
    session = attendance_sessions.get(chat_id)
    if not session:
        await bot.send_message(chat_id, "❌ Сесія не знайдена.")
        return
    
    try:
        marked_count = session['marked_count']
        total_count = session['total_count']
        lesson_event_id = session['lesson_event_id']
        
        # Оновлюємо статус lesson event на завершений
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(LessonEvent)
                .where(LessonEvent.id == lesson_event_id)
                .values(
                    status=LessonEventStatus.COMPLETED,
                    completed_at=datetime.utcnow()
                )
            )
            await db.commit()
        
        # Видаляємо сесію
        del attendance_sessions[chat_id]
        
        # Приховуємо клавіатуру
        await bot.send_message(
            chat_id=chat_id,
            text=f"""
✅ **Відмітка завершена!**

📊 **Підсумок:**
• Всього студентів: {total_count}
• Відмічено: {marked_count}

Всі студенти відмічені! 🙏
""",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        
        logger.info(f"Attendance completed for lesson {lesson_event_id}: {marked_count}/{total_count} marked")
        
    except Exception as e:
        logger.error(f"Error finishing attendance: {e}")
        await bot.send_message(chat_id, f"❌ Помилка завершення: {e}")

# Функція для відправки повідомлення з кнопкою "Почати відмітку"
async def send_quick_attendance_invitation(chat_id: int, lesson_event_id: int, lesson_info: str, bot: Bot):
    """Відправляє запрошення почати швидку відмітку."""
    
    # Використовуємо новий єдиний список замість старої системи
    from app.bot.unified_attendance import send_unified_attendance_list
    
    await send_unified_attendance_list(chat_id, lesson_event_id, lesson_info, bot)

# Callback handler для початку відмітки
@router.callback_query(F.data.startswith("start_quick_attendance:"))
async def handle_start_quick_attendance(query):
    """Обробляє початок швидкої відмітки."""
    lesson_event_id = int(query.data.split(":")[1])
    chat_id = query.message.chat.id
    
    await query.answer()
    await start_quick_attendance(chat_id, lesson_event_id, query.bot)
    
    # Видаляємо початкове повідомлення
    await query.message.delete()
