"""
WebApp API endpoints for Telegram Mini App.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.settings import settings
from app.models import Teacher, Student, Schedule, ScheduleEnrollment, LessonEvent, Attendance
from app.utils.telegram_auth import validate_telegram_webapp_data, validate_dev_mode, TelegramWebAppUser

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_webapp_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
) -> TelegramWebAppUser:
    """
    Get current user from Telegram WebApp initData.
    """
    # Validate initData
    user = None
    
    # Try production validation first
    if settings.ENVIRONMENT == "production":
        user = validate_telegram_webapp_data(x_telegram_init_data)
    else:
        # In development, try dev mode first, then production validation
        user = validate_dev_mode(x_telegram_init_data)
        if not user:
            user = validate_telegram_webapp_data(x_telegram_init_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram WebApp authentication data"
        )
    
    return user


async def get_webapp_teacher(
    user: TelegramWebAppUser = Depends(get_webapp_user),
    db: AsyncSession = Depends(get_db)
) -> Teacher:
    """
    Get current teacher from database.
    """
    result = await db.execute(
        select(Teacher).where(Teacher.tg_chat_id == user.id)
    )
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher not found. Please contact administrator."
        )
    
    return teacher


@router.get("/me")
async def get_me(
    teacher: Teacher = Depends(get_webapp_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile with groups."""
    # Get teacher's schedules (which represent groups)
    result = await db.execute(
        select(Schedule)
        .options(selectinload(Schedule.club))
        .where(Schedule.teacher_id == teacher.id, Schedule.active == True)
        .distinct()
    )
    schedules = result.scalars().all()
    
    # Group schedules by club to create "groups"
    groups = {}
    for schedule in schedules:
        club = schedule.club
        if club.id not in groups:
            groups[club.id] = {
                "id": club.id,
                "title": club.name,
                "description": f"{club.location} • {club.duration_min} хв",
                "created_at": club.created_at.isoformat()
            }
    
    return {
        "user_id": teacher.tg_chat_id,
        "full_name": teacher.full_name,
        "role": "teacher",
        "teacher_groups": list(groups.values())
    }


@router.get("/groups")
async def get_groups(
    teacher: Teacher = Depends(get_webapp_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get all groups (clubs) for current teacher."""
    # Get teacher's active schedules
    result = await db.execute(
        select(Schedule)
        .options(selectinload(Schedule.club))
        .where(Schedule.teacher_id == teacher.id, Schedule.active == True)
        .distinct()
    )
    schedules = result.scalars().all()
    
    # Group by club
    groups = {}
    for schedule in schedules:
        club = schedule.club
        if club.id not in groups:
            groups[club.id] = {
                "id": club.id,
                "title": club.name,
                "description": f"{club.location} • {club.duration_min} хв",
                "created_at": club.created_at.isoformat()
            }
    
    return list(groups.values())


@router.get("/groups/{group_id}/students")
async def get_group_students(
    group_id: int,
    teacher: Teacher = Depends(get_webapp_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get students for a group (club)."""
    # Verify teacher has access to this club
    result = await db.execute(
        select(Schedule).where(
            Schedule.teacher_id == teacher.id,
            Schedule.club_id == group_id,
            Schedule.active == True
        )
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this group"
        )
    
    # Get students enrolled in any schedule for this club and teacher
    result = await db.execute(
        select(Student)
        .join(ScheduleEnrollment)
        .join(Schedule)
        .where(
            Schedule.club_id == group_id,
            Schedule.teacher_id == teacher.id,
            Schedule.active == True
        )
        .distinct()
        .order_by(Student.first_name, Student.last_name)
    )
    students = result.scalars().all()
    
    return [
        {
            "id": student.id,
            "full_name": student.full_name,
            "gender": getattr(student, 'gender', 'male'),  # Default to male if not set
            "age": getattr(student, 'age', 10),  # Default age
            "group_id": group_id,
            "created_at": student.created_at.isoformat()
        }
        for student in students
    ]


@router.post("/sessions")
async def create_session(
    data: dict,
    teacher: Teacher = Depends(get_webapp_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create attendance session."""
    group_id = data.get("group_id")
    if not group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_id is required"
        )
    
    # Verify teacher has access to this club
    result = await db.execute(
        select(Schedule).where(
            Schedule.teacher_id == teacher.id,
            Schedule.club_id == group_id,
            Schedule.active == True
        )
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this group"
        )
    
    # Create lesson event for today
    today = datetime.now().date()
    lesson_event = LessonEvent(
        schedule_id=schedule.id,
        date=today,
        club_id=group_id,
        teacher_id=teacher.id,
        status="PLANNED"
    )
    
    db.add(lesson_event)
    await db.commit()
    await db.refresh(lesson_event)
    
    return {
        "id": lesson_event.id,
        "group_id": group_id,
        "started_at": lesson_event.created_at.isoformat(),
        "ended_at": None,
        "created_by_tg_user_id": teacher.tg_chat_id
    }


@router.put("/sessions/{session_id}/end")
async def end_session(
    session_id: int,
    teacher: Teacher = Depends(get_webapp_teacher),
    db: AsyncSession = Depends(get_db)
):
    """End attendance session."""
    # Get lesson event
    result = await db.execute(
        select(LessonEvent).where(LessonEvent.id == session_id)
    )
    lesson_event = result.scalar_one_or_none()
    
    if not lesson_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if lesson_event.teacher_id != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session"
        )
    
    # Mark as completed
    lesson_event.status = "COMPLETED"
    lesson_event.completed_at = datetime.now()
    await db.commit()
    
    return {"message": "Session ended successfully"}


@router.post("/attendance/batch")
async def submit_attendance(
    data: dict,
    teacher: Teacher = Depends(get_webapp_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Submit batch attendance data."""
    events = data.get("events", [])
    if not events:
        return {"message": "No events to process", "processed": 0}
    
    processed = 0
    for event in events:
        session_id = event.get("session_id")
        student_id = event.get("student_id") 
        status = event.get("status")
        timestamp = event.get("timestamp")
        
        if not all([session_id, student_id, status]):
            continue
        
        # Verify session belongs to teacher
        result = await db.execute(
            select(LessonEvent).where(
                LessonEvent.id == session_id,
                LessonEvent.teacher_id == teacher.id
            )
        )
        lesson_event = result.scalar_one_or_none()
        
        if not lesson_event:
            continue
        
        # Create or update attendance record
        result = await db.execute(
            select(Attendance).where(
                Attendance.lesson_event_id == session_id,
                Attendance.student_id == student_id
            )
        )
        attendance = result.scalar_one_or_none()
        
        if attendance:
            # Update existing
            attendance.status = status.upper()
            attendance.updated_at = datetime.now()
        else:
            # Create new
            attendance = Attendance(
                lesson_event_id=session_id,
                student_id=student_id,
                status=status.upper(),
                marked_by=str(teacher.tg_chat_id)
            )
            db.add(attendance)
        
        processed += 1
    
    await db.commit()
    
    # 🔄 ПЕРЕСЧИТУЄМО CONDUCTED_LESSONS ДЛЯ ВСІХ ОНОВЛЕНИХ УРОКІВ
    try:
        from app.services.conducted_lesson_service import ConductedLessonService
        conducted_lesson_service = ConductedLessonService(db)
        
        # Збираємо унікальні lesson_event_id з оброблених подій
        lesson_event_ids = set()
        for event in events:
            session_id = event.get("session_id")
            if session_id and session_id not in lesson_event_ids:
                lesson_event_ids.add(session_id)
                await conducted_lesson_service.recalculate_from_attendance(session_id)
        
        logger.info(f"🔄 Recalculated {len(lesson_event_ids)} ConductedLessons after batch attendance update")
        
    except Exception as e:
        logger.warning(f"Failed to recalculate ConductedLessons after batch update: {e}")
        # Не блокуємо основну операцію
    
    return {
        "message": f"Processed {processed} attendance events",
        "processed": processed,
        "total": len(events)
    }
