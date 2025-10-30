"""Bot management API endpoints."""

from datetime import datetime, time, date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import AdminUser, DbSession, get_db
from app.models import BotSchedule, Schedule, Club, Teacher, LessonEvent
from app.models.lesson_event import LessonEventStatus

router = APIRouter(prefix="/bot", tags=["bot"])
logger = logging.getLogger(__name__)


class BotScheduleCreate(BaseModel):
    """Bot schedule creation model."""
    schedule_id: int
    enabled: bool = True
    offset_minutes: int = 0  # Зсув від початку заняття
    custom_time: Optional[time] = None  # Точний час розсилки
    custom_message: Optional[str] = None


class BotScheduleUpdate(BaseModel):
    """Bot schedule update model."""
    enabled: Optional[bool] = None
    offset_minutes: Optional[int] = None
    custom_time: Optional[time] = None
    custom_message: Optional[str] = None


class ScheduleInfo(BaseModel):
    """Schedule info for response."""
    id: int
    club_name: str
    teacher_name: str
    weekday: int
    start_time: str
    group_name: Optional[str]
    active: bool


class BotScheduleResponse(BaseModel):
    """Bot schedule response model."""
    id: int
    schedule_id: int
    enabled: bool
    offset_minutes: int
    custom_time: Optional[time]
    custom_message: Optional[str]
    notification_time_description: str
    status_description: str
    created_at: datetime
    updated_at: datetime
    
    # Інформація про розклад
    schedule: ScheduleInfo


@router.get("/schedules", response_model=List[BotScheduleResponse])
async def get_bot_schedules(
    db: DbSession,
    # admin: AdminUser,  # Поки що відключаємо авторизацію
) -> List[BotScheduleResponse]:
    """Get all bot schedules with schedule information."""
    result = await db.execute(
        select(BotSchedule)
        .options(
            selectinload(BotSchedule.schedule).selectinload(Schedule.club),
            selectinload(BotSchedule.schedule).selectinload(Schedule.teacher)
        )
        .order_by(BotSchedule.created_at.desc())
    )
    bot_schedules = result.scalars().all()
    
    response = []
    for bot_schedule in bot_schedules:
        schedule = bot_schedule.schedule
        response.append(BotScheduleResponse(
            id=bot_schedule.id,
            schedule_id=bot_schedule.schedule_id,
            enabled=bot_schedule.enabled,
            offset_minutes=bot_schedule.offset_minutes,
            custom_time=bot_schedule.custom_time,
            custom_message=bot_schedule.custom_message,
            notification_time_description=bot_schedule.notification_time_description,
            status_description=bot_schedule.status_description,
            created_at=bot_schedule.created_at,
            updated_at=bot_schedule.updated_at,
            schedule=ScheduleInfo(
                id=schedule.id,
                club_name=schedule.club.name,
                teacher_name=schedule.teacher.full_name,
                weekday=schedule.weekday,
                start_time=str(schedule.start_time),
                group_name=schedule.group_name,
                active=schedule.active
            )
        ))
    
    return response


@router.get("/schedules/{bot_schedule_id}", response_model=BotScheduleResponse)
async def get_bot_schedule(
    bot_schedule_id: int,
    db: DbSession,
    # admin: AdminUser,
) -> BotScheduleResponse:
    """Get specific bot schedule."""
    result = await db.execute(
        select(BotSchedule)
        .options(
            selectinload(BotSchedule.schedule).selectinload(Schedule.club),
            selectinload(BotSchedule.schedule).selectinload(Schedule.teacher)
        )
        .where(BotSchedule.id == bot_schedule_id)
    )
    bot_schedule = result.scalar_one_or_none()
    
    if not bot_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot schedule not found"
        )
    
    schedule = bot_schedule.schedule
    return BotScheduleResponse(
        id=bot_schedule.id,
        schedule_id=bot_schedule.schedule_id,
        enabled=bot_schedule.enabled,
        offset_minutes=bot_schedule.offset_minutes,
        custom_time=bot_schedule.custom_time,
        custom_message=bot_schedule.custom_message,
        notification_time_description=bot_schedule.notification_time_description,
        status_description=bot_schedule.status_description,
        created_at=bot_schedule.created_at,
        updated_at=bot_schedule.updated_at,
        schedule=ScheduleInfo(
            id=schedule.id,
            club_name=schedule.club.name,
            teacher_name=schedule.teacher.full_name,
            weekday=schedule.weekday,
            start_time=str(schedule.start_time),
            group_name=schedule.group_name,
            active=schedule.active
        )
    )


@router.post("/schedules", response_model=BotScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_bot_schedule(
    bot_schedule_data: BotScheduleCreate,
    db: DbSession,
    # admin: AdminUser,
) -> BotScheduleResponse:
    """Create new bot schedule."""
    # Перевіряємо чи існує розклад
    result = await db.execute(
        select(Schedule)
        .options(
            selectinload(Schedule.club),
            selectinload(Schedule.teacher)
        )
        .where(Schedule.id == bot_schedule_data.schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Перевіряємо чи вже існує bot_schedule для цього розкладу
    existing_result = await db.execute(
        select(BotSchedule).where(BotSchedule.schedule_id == bot_schedule_data.schedule_id)
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot schedule already exists for this schedule"
        )
    
    # Автоматично обчислюємо custom_time на основі offset_minutes якщо не задано
    custom_time = bot_schedule_data.custom_time
    if custom_time is None and bot_schedule_data.offset_minutes != 0:
        # Обчислюємо час на основі start_time + offset_minutes
        from datetime import timedelta
        schedule_start = datetime.combine(datetime.today(), schedule.start_time)
        notification_time = schedule_start + timedelta(minutes=bot_schedule_data.offset_minutes)
        custom_time = notification_time.time()
    
    # Створюємо новий bot_schedule
    bot_schedule = BotSchedule(
        schedule_id=bot_schedule_data.schedule_id,
        enabled=bot_schedule_data.enabled,
        offset_minutes=bot_schedule_data.offset_minutes,
        custom_time=custom_time,
        custom_message=bot_schedule_data.custom_message
    )
    
    db.add(bot_schedule)
    await db.flush()  # Отримуємо ID
    
    # 📝 AUDIT LOG: Створення bot schedule (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        import logging
        logger_audit = logging.getLogger(__name__)
        
        # Завантажуємо schedule для отримання назви
        result_schedule = await db.execute(
            select(Schedule).options(selectinload(Schedule.club), selectinload(Schedule.teacher))
            .where(Schedule.id == bot_schedule_data.schedule_id)
        )
        schedule_for_log = result_schedule.scalar_one()
        schedule_name = f"{schedule_for_log.club.name if schedule_for_log.club else '(гурток видалений)'} - {schedule_for_log.teacher.full_name if schedule_for_log.teacher else '(викладач не вказаний)'}"
        
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="bot_schedule",
            entity_id=bot_schedule.id,
            entity_name=f"Розсилка для '{schedule_name}'",
            description=f"Створено bot розсилку для розкладу '{schedule_name}'. Зміщення: {bot_schedule.offset_minutes} хв, повідомлення: {bot_schedule.custom_message or 'стандартне'}",
            user_name="Адміністратор",
            changes={"after": {
                "schedule_id": bot_schedule.schedule_id,
                "enabled": bot_schedule.enabled,
                "offset_minutes": bot_schedule.offset_minutes,
                "custom_message": bot_schedule.custom_message
            }}
        )
    except Exception as e:
        logger_audit.error(f"❌ AUDIT LOG ERROR (bot_schedule CREATE): {e}")
        import traceback
        logger_audit.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(bot_schedule)
    
    # Автоматично створюємо lesson events для нового BotSchedule
    try:
        from app.services.lesson_event_manager import LessonEventManager
        manager = LessonEventManager(db)
        await manager.ensure_bot_schedule_has_events(bot_schedule.id)
        logger.info(f"Auto-created lesson events for new BotSchedule {bot_schedule.id}")
    except Exception as e:
        logger.warning(f"Could not auto-create lesson events for BotSchedule {bot_schedule.id}: {e}")
    
    # Завантажуємо з зв'язками
    result = await db.execute(
        select(BotSchedule)
        .options(
            selectinload(BotSchedule.schedule).selectinload(Schedule.club),
            selectinload(BotSchedule.schedule).selectinload(Schedule.teacher)
        )
        .where(BotSchedule.id == bot_schedule.id)
    )
    bot_schedule = result.scalar_one()
    
    schedule = bot_schedule.schedule
    return BotScheduleResponse(
        id=bot_schedule.id,
        schedule_id=bot_schedule.schedule_id,
        enabled=bot_schedule.enabled,
        offset_minutes=bot_schedule.offset_minutes,
        custom_time=bot_schedule.custom_time,
        custom_message=bot_schedule.custom_message,
        notification_time_description=bot_schedule.notification_time_description,
        status_description=bot_schedule.status_description,
        created_at=bot_schedule.created_at,
        updated_at=bot_schedule.updated_at,
        schedule=ScheduleInfo(
            id=schedule.id,
            club_name=schedule.club.name,
            teacher_name=schedule.teacher.full_name,
            weekday=schedule.weekday,
            start_time=str(schedule.start_time),
            group_name=schedule.group_name,
            active=schedule.active
        )
    )


@router.put("/schedules/{bot_schedule_id}", response_model=BotScheduleResponse)
async def update_bot_schedule(
    bot_schedule_id: int,
    bot_schedule_data: BotScheduleUpdate,
    db: DbSession,
    # admin: AdminUser,
) -> BotScheduleResponse:
    """Update bot schedule."""
    result = await db.execute(
        select(BotSchedule)
        .options(
            selectinload(BotSchedule.schedule).selectinload(Schedule.club),
            selectinload(BotSchedule.schedule).selectinload(Schedule.teacher)
        )
        .where(BotSchedule.id == bot_schedule_id)
    )
    bot_schedule = result.scalar_one_or_none()
    
    if not bot_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot schedule not found"
        )
    
    # Зберігаємо старі значення для аудиту
    old_values = {
        "enabled": bot_schedule.enabled,
        "offset_minutes": bot_schedule.offset_minutes,
        "custom_time": str(bot_schedule.custom_time) if bot_schedule.custom_time else None,
        "custom_message": bot_schedule.custom_message
    }
    
    # Оновлюємо поля
    if bot_schedule_data.enabled is not None:
        bot_schedule.enabled = bot_schedule_data.enabled
    if bot_schedule_data.offset_minutes is not None:
        bot_schedule.offset_minutes = bot_schedule_data.offset_minutes
        # Автоматично перераховуємо custom_time при зміні offset_minutes
        if bot_schedule_data.custom_time is None:
            from datetime import timedelta
            schedule_start = datetime.combine(datetime.today(), bot_schedule.schedule.start_time)
            notification_time = schedule_start + timedelta(minutes=bot_schedule_data.offset_minutes)
            bot_schedule.custom_time = notification_time.time()
    if bot_schedule_data.custom_time is not None:
        bot_schedule.custom_time = bot_schedule_data.custom_time
    if bot_schedule_data.custom_message is not None:
        bot_schedule.custom_message = bot_schedule_data.custom_message
    
    bot_schedule.updated_at = datetime.utcnow()
    
    # 📝 AUDIT LOG: Оновлення bot schedule (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        import logging
        logger_audit = logging.getLogger(__name__)
        
        schedule = bot_schedule.schedule
        schedule_name = f"{schedule.club.name if schedule.club else '(гурток видалений)'} - {schedule.teacher.full_name if schedule.teacher else '(викладач не вказаний)'}"
        
        update_data = {}
        if bot_schedule_data.enabled is not None:
            update_data["enabled"] = bot_schedule.enabled
        if bot_schedule_data.offset_minutes is not None:
            update_data["offset_minutes"] = bot_schedule.offset_minutes
        if bot_schedule_data.custom_time is not None:
            update_data["custom_time"] = str(bot_schedule.custom_time)
        if bot_schedule_data.custom_message is not None:
            update_data["custom_message"] = bot_schedule.custom_message
        
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {v}" for k, v in update_data.items() if old_values.get(k) != v])
        
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="bot_schedule",
            entity_id=bot_schedule.id,
            entity_name=f"Розсилка для '{schedule_name}'",
            description=f"Оновлено bot розсилку для '{schedule_name}'. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": update_data}
        )
    except Exception as e:
        logger_audit.error(f"❌ AUDIT LOG ERROR (bot_schedule UPDATE): {e}")
        import traceback
        logger_audit.error(traceback.format_exc())
    
    # Завжди оновлюємо lesson events (при будь-яких змінах)
    from app.services.lesson_event_manager import LessonEventManager
    manager = LessonEventManager(db)
    await manager.ensure_bot_schedule_has_events(bot_schedule.id)
    logger.info(f"Updated lesson events for BotSchedule {bot_schedule.id}")
    
    await db.commit()
    await db.refresh(bot_schedule)
    
    schedule = bot_schedule.schedule
    return BotScheduleResponse(
        id=bot_schedule.id,
        schedule_id=bot_schedule.schedule_id,
        enabled=bot_schedule.enabled,
        offset_minutes=bot_schedule.offset_minutes,
        custom_time=bot_schedule.custom_time,
        custom_message=bot_schedule.custom_message,
        notification_time_description=bot_schedule.notification_time_description,
        status_description=bot_schedule.status_description,
        created_at=bot_schedule.created_at,
        updated_at=bot_schedule.updated_at,
        schedule=ScheduleInfo(
            id=schedule.id,
            club_name=schedule.club.name,
            teacher_name=schedule.teacher.full_name,
            weekday=schedule.weekday,
            start_time=str(schedule.start_time),
            group_name=schedule.group_name,
            active=schedule.active
        )
    )


@router.delete("/schedules/{bot_schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot_schedule(
    bot_schedule_id: int,
    db: DbSession,
    # admin: AdminUser,
) -> None:
    """Delete bot schedule."""
    result = await db.execute(
        select(BotSchedule)
        .options(
            selectinload(BotSchedule.schedule).selectinload(Schedule.club),
            selectinload(BotSchedule.schedule).selectinload(Schedule.teacher)
        )
        .where(BotSchedule.id == bot_schedule_id)
    )
    bot_schedule = result.scalar_one_or_none()
    
    if not bot_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot schedule not found"
        )
    
    # Зберігаємо дані для аудиту перед видаленням
    schedule = bot_schedule.schedule
    schedule_name = f"{schedule.club.name if schedule.club else '(гурток видалений)'} - {schedule.teacher.full_name if schedule.teacher else '(викладач не вказаний)'}"
    
    await db.delete(bot_schedule)
    
    # 📝 AUDIT LOG: Видалення bot schedule (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        import logging
        logger_audit = logging.getLogger(__name__)
        
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="bot_schedule",
            entity_id=bot_schedule_id,
            entity_name=f"Розсилка для '{schedule_name}'",
            description=f"Видалено bot розсилку для розкладу '{schedule_name}'",
            user_name="Адміністратор",
            changes={"deleted": {"schedule_id": bot_schedule.schedule_id, "enabled": bot_schedule.enabled}}
        )
    except Exception as e:
        logger_audit.error(f"❌ AUDIT LOG ERROR (bot_schedule DELETE): {e}")
        import traceback
        logger_audit.error(traceback.format_exc())
    
    await db.commit()


class AvailableScheduleResponse(BaseModel):
    """Available schedule for bot notifications."""
    id: int
    club_name: str
    teacher_name: str
    weekday: int
    start_time: str
    group_name: Optional[str]
    active: bool
    has_bot_schedule: bool


@router.get("/available-schedules", response_model=List[AvailableScheduleResponse])
async def get_available_schedules(
    db: DbSession,
    # admin: AdminUser,
) -> List[AvailableScheduleResponse]:
    """Get all schedules with bot schedule status."""
    result = await db.execute(
        select(Schedule)
        .options(
            selectinload(Schedule.club),
            selectinload(Schedule.teacher),
            selectinload(Schedule.bot_schedule)
        )
        .where(Schedule.active == True)
        .order_by(Schedule.weekday, Schedule.start_time)
    )
    schedules = result.scalars().all()
    
    response = []
    for schedule in schedules:
        response.append(AvailableScheduleResponse(
            id=schedule.id,
            club_name=schedule.club.name,
            teacher_name=schedule.teacher.full_name,
            weekday=schedule.weekday,
            start_time=str(schedule.start_time),
            group_name=schedule.group_name,
            active=schedule.active,
            has_bot_schedule=schedule.bot_schedule is not None
        ))
    
    return response


@router.post("/test-send-checklist/{lesson_event_id}")
async def test_send_checklist(
    lesson_event_id: int,
    db: DbSession,
    # admin: AdminUser,
) -> dict:
    """Test sending attendance checklist for a lesson event."""
    from app.bot.handlers import send_attendance_checklist
    from app.models import LessonEvent, Teacher
    
    # Get lesson event with teacher
    result = await db.execute(
        select(LessonEvent)
        .options(selectinload(LessonEvent.teacher))
        .where(LessonEvent.id == lesson_event_id)
    )
    lesson_event = result.scalar_one_or_none()
    
    if not lesson_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson event not found"
        )
    
    if not lesson_event.teacher.tg_chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teacher has no Telegram chat_id. Teacher must start the bot first."
        )
    
    try:
        await send_attendance_checklist(
            chat_id=lesson_event.teacher.tg_chat_id,
            lesson_event_id=lesson_event_id
        )
        
        return {
            "success": True,
            "message": f"Checklist sent to teacher {lesson_event.teacher.full_name}",
            "lesson_event_id": lesson_event_id,
            "teacher_chat_id": lesson_event.teacher.tg_chat_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send checklist: {str(e)}"
        )


@router.post("/test-send-swipe-checklist/{lesson_event_id}")
async def test_send_swipe_checklist(lesson_event_id: int, db: AsyncSession = Depends(get_db)):
    """Test endpoint to send swipe-style attendance checklist for a lesson event."""
    try:
        from app.bot.handlers import send_swipe_attendance_cards
        
        # Get lesson event
        lesson_event = await db.get(LessonEvent, lesson_event_id)
        if not lesson_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson event {lesson_event_id} not found"
            )
            
        # Get teacher
        if not lesson_event.schedule.teacher.tg_chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teacher doesn't have Telegram chat_id"
            )
        
        # Send swipe checklist
        await send_swipe_attendance_cards(
            lesson_event.schedule.teacher.tg_chat_id, 
            lesson_event_id
        )
        
        return {
            "message": "Swipe checklist sent successfully",
            "lesson_event_id": lesson_event_id,
            "teacher_chat_id": lesson_event.schedule.teacher.tg_chat_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send swipe checklist: {str(e)}"
        )


@router.post("/test-quick-attendance/{lesson_event_id}")
async def test_quick_attendance(lesson_event_id: int, db: AsyncSession = Depends(get_db)):
    """Test endpoint for new quick attendance system with Reply Keyboard."""
    try:
        from app.bot.handlers import send_attendance_checklist
        
        # Get lesson event to find teacher
        lesson_event = await db.get(LessonEvent, lesson_event_id)
        if not lesson_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson event {lesson_event_id} not found"
            )
            
        # Use test chat_id (твій chat_id)
        test_chat_id = 733455161
        
        # Send quick attendance invitation
        await send_attendance_checklist(test_chat_id, lesson_event_id)
        
        return {
            "message": "Quick attendance invitation sent successfully",
            "lesson_event_id": lesson_event_id,
            "chat_id": test_chat_id,
            "system": "Reply Keyboard (макрокнопки)"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send quick attendance: {str(e)}"
        )


@router.get("/check-notifications")
async def check_notifications(db: AsyncSession = Depends(get_db)):
    """Check for lesson notifications that should be sent now."""
    try:
        from datetime import datetime, time
        from zoneinfo import ZoneInfo
        
        timezone = ZoneInfo('Europe/Kiev') 
        now = datetime.now(timezone)
        current_time = now.time().replace(second=0, microsecond=0)
        today = now.date()
        
        logger.info(f"Checking notifications at {current_time}")
        
        # Get active bot schedules that should trigger now
        result = await db.execute(
            select(BotSchedule)
            .join(Schedule)
            .join(LessonEvent, LessonEvent.schedule_id == Schedule.id)
            .join(Teacher)
            .where(
                BotSchedule.enabled == True,
                BotSchedule.custom_time == current_time,
                LessonEvent.date == today,
                LessonEvent.status == LessonEventStatus.PLANNED,
                Teacher.tg_chat_id.is_not(None),
                Teacher.active == True,
            )
            .options(
                selectinload(BotSchedule.schedule).selectinload(Schedule.teacher),
                selectinload(BotSchedule.schedule).selectinload(Schedule.club),
            )
        )
        
        bot_schedules = result.scalars().all()
        sent_count = 0
        
        for bot_schedule in bot_schedules:
            # Find lesson event for today
            lesson_result = await db.execute(
                select(LessonEvent)
                .where(
                    LessonEvent.schedule_id == bot_schedule.schedule_id,
                    LessonEvent.date == today,
                    LessonEvent.status == LessonEventStatus.PLANNED
                )
            )
            
            lesson_event = lesson_result.scalar_one_or_none()
            if not lesson_event:
                continue
            
            # Send notification
            from app.bot.quick_attendance import send_quick_attendance_invitation
            from aiogram import Bot
            from app.core.settings import settings
            
            # Створюємо простий bot без dispatcher
            bot = Bot(token=settings.telegram_bot_token)
            
            # Format lesson info
            weekday_names = ['', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']
            lesson_info = f"{bot_schedule.schedule.club.name} - {weekday_names[bot_schedule.schedule.weekday]} {bot_schedule.schedule.start_time} - {bot_schedule.schedule.group_name or 'Група'}"
            
            await send_quick_attendance_invitation(
                chat_id=bot_schedule.schedule.teacher.tg_chat_id,
                lesson_event_id=lesson_event.id,
                lesson_info=lesson_info,
                bot=bot
            )
            
            # Update lesson event status
            await db.execute(
                update(LessonEvent)
                .where(LessonEvent.id == lesson_event.id)
                .values(
                    status=LessonEventStatus.SENT,
                    sent_at=now
                )
            )
            
            await bot.session.close()
            sent_count += 1
            
            logger.info(f"Sent notification for lesson_event {lesson_event.id} to chat {bot_schedule.schedule.teacher.tg_chat_id}")
        
        await db.commit()
        
        return {
            "checked_at": current_time.isoformat(),
            "notifications_sent": sent_count,
            "message": f"Checked notifications at {current_time}, sent {sent_count}"
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error checking notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking notifications: {e}")


@router.post("/reset-lesson-event/{lesson_event_id}")
async def reset_lesson_event_to_planned(lesson_event_id: int):
    """Скидає lesson event у статус PLANNED для повторного використання."""
    try:
        from app.services.lesson_event_manager import reset_event_to_planned
        
        success = await reset_event_to_planned(lesson_event_id)
        
        if success:
            return {
                "message": f"Lesson event {lesson_event_id} reset to PLANNED",
                "lesson_event_id": lesson_event_id,
                "new_status": "PLANNED"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reset lesson event")
            
    except Exception as e:
        logger.error(f"Error resetting lesson event: {e}")
        raise HTTPException(status_code=500, detail=f"Error resetting lesson event: {e}")


@router.post("/generate-daily-events")
async def generate_daily_events():
    """Автоматично генерує lesson events на сьогодні."""
    try:
        from app.services.lesson_event_manager import auto_generate_todays_events
        
        created_count = await auto_generate_todays_events()
        
        return {
            "message": f"Generated {created_count} lesson events for today",
            "events_created": created_count,
            "date": str(date.today())
        }
        
    except Exception as e:
        logger.error(f"Error generating daily events: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating daily events: {e}")
