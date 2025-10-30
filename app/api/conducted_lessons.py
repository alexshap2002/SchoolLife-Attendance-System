"""Conducted lessons management API endpoints."""

from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import ConductedLesson, Teacher, Club, LessonEvent, Schedule, ScheduleEnrollment, Student, Attendance
from app.services.conducted_lesson_service import ConductedLessonService

router = APIRouter(prefix="/api/conducted_lessons", tags=["conducted_lessons"])
logger = logging.getLogger(__name__)


class ConductedLessonResponse(BaseModel):
    """Response model for conducted lesson."""
    id: int
    teacher_id: int
    teacher_name: str
    club_id: Optional[int]  # Nullable після видалення гуртка
    club_name: Optional[str]  # Nullable після видалення гуртка
    lesson_event_id: int
    lesson_date: datetime
    lesson_duration_minutes: Optional[int]
    total_students: int
    present_students: int
    absent_students: int
    attendance_rate: float
    notes: Optional[str]
    lesson_topic: Optional[str]
    is_salary_calculated: bool
    is_valid_for_salary: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConductedLessonCreateRequest(BaseModel):
    """Request model for creating a conducted lesson."""
    lesson_event_id: int
    notes: Optional[str] = None
    lesson_topic: Optional[str] = None


class ManualConductedLessonCreateRequest(BaseModel):
    """Request model for creating a manual conducted lesson."""
    schedule_id: int
    lesson_date: datetime
    student_attendance: List[dict]  # [{"student_id": 123, "status": "present"}, ...]
    notes: Optional[str] = None
    lesson_duration_minutes: Optional[int] = None
    auto_calculate_payroll: bool = True  # Автоматично нараховувати зарплату за замовчуванням


class ConductedLessonUpdateRequest(BaseModel):
    """Request model for updating a conducted lesson."""
    lesson_date: Optional[datetime] = None
    lesson_duration_minutes: Optional[int] = None
    total_students: Optional[int] = None
    present_students: Optional[int] = None
    absent_students: Optional[int] = None
    notes: Optional[str] = None
    lesson_topic: Optional[str] = None


class StudentAttendanceResponse(BaseModel):
    """Response model for student attendance in a conducted lesson."""
    student_id: int
    first_name: str
    last_name: str
    full_name: str
    attendance_id: int
    status: str  # PRESENT, ABSENT
    
    class Config:
        from_attributes = True


class AttendanceUpdateRequest(BaseModel):
    """Request model for updating student attendance status."""
    status: str  # PRESENT, ABSENT


class TeacherStatisticsResponse(BaseModel):
    """Response model for teacher statistics."""
    teacher_id: int
    teacher_name: str
    period_start: date
    period_end: date
    total_lessons: int
    total_students: int
    present_students: int
    absent_students: int
    attendance_rate: float
    lessons_with_attendance: int


@router.get("", response_model=List[ConductedLessonResponse])
async def get_conducted_lessons(
    teacher_id: Optional[int] = Query(None, description="Filter by teacher ID"),
    club_id: Optional[int] = Query(None, description="Filter by club ID"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    only_uncalculated: bool = Query(False, description="Show only lessons without salary calculated"),
    limit: Optional[int] = Query(1000, description="Limit number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Get conducted lessons with optional filters."""
    
    query = select(ConductedLesson).options(
        selectinload(ConductedLesson.teacher),
        selectinload(ConductedLesson.club),
        selectinload(ConductedLesson.lesson_event)
    )
    
    # Застосовуємо фільтри
    if teacher_id:
        query = query.where(ConductedLesson.teacher_id == teacher_id)
    
    if club_id:
        query = query.where(ConductedLesson.club_id == club_id)
    
    if start_date:
        query = query.where(ConductedLesson.lesson_date >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.where(ConductedLesson.lesson_date <= datetime.combine(end_date, datetime.max.time()))
    
    if only_uncalculated:
        query = query.where(ConductedLesson.is_salary_calculated == False)
        query = query.where(ConductedLesson.present_students > 0)  # Only valid for salary
    
    query = query.order_by(ConductedLesson.lesson_date.desc())
    
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    conducted_lessons = result.scalars().all()
    
    # Формуємо response
    response_data = []
    for lesson in conducted_lessons:
        response_data.append(ConductedLessonResponse(
            id=lesson.id,
            teacher_id=lesson.teacher_id,
            teacher_name=lesson.teacher.full_name if lesson.teacher else "N/A",
            club_id=lesson.club_id if lesson.club_id else None,
            club_name=lesson.club.name if lesson.club else "(гурток видалений)",
            lesson_event_id=lesson.lesson_event_id,
            lesson_date=lesson.lesson_date,
            lesson_duration_minutes=lesson.lesson_duration_minutes,
            total_students=lesson.total_students,
            present_students=lesson.present_students,
            absent_students=lesson.absent_students,
            attendance_rate=lesson.attendance_rate,
            notes=lesson.notes,
            lesson_topic=lesson.lesson_topic,
            is_salary_calculated=lesson.is_salary_calculated,
            is_valid_for_salary=lesson.is_valid_for_salary,
            created_at=lesson.created_at
        ))
    
    return response_data


@router.get("/available-schedules", response_model=List[dict])
async def get_available_schedules(
    db: AsyncSession = Depends(get_db)
):
    """Get all available schedules for manual lesson creation."""
    result = await db.execute(
        select(Schedule)
        .options(
            selectinload(Schedule.teacher),
            selectinload(Schedule.club),
            selectinload(Schedule.enrolled_students).selectinload(ScheduleEnrollment.student)
        )
        .where(Schedule.active == True)
        .order_by(Schedule.weekday, Schedule.start_time)
    )
    schedules = result.scalars().all()
    
    schedule_list = []
    for schedule in schedules:
        weekday_names = ["", "Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
        schedule_list.append({
            "id": schedule.id,
            "teacher_name": schedule.teacher.full_name if schedule.teacher else "N/A",
            "club_name": schedule.club.name if schedule.club else "N/A",
            "weekday": schedule.weekday,
            "weekday_name": weekday_names[schedule.weekday] if 1 <= schedule.weekday <= 7 else "N/A",
            "start_time": str(schedule.start_time),
            "group_name": schedule.group_name or "Група 1",
            "student_count": len(schedule.enrolled_students),
            "display_name": f"{schedule.teacher.full_name if schedule.teacher else 'N/A'} - {schedule.club.name if schedule.club else 'N/A'} ({weekday_names[schedule.weekday] if 1 <= schedule.weekday <= 7 else 'N/A'} {schedule.start_time})"
        })
    
    return schedule_list


@router.get("/schedule/{schedule_id}/students", response_model=List[dict])
async def get_schedule_students(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all students enrolled in a specific schedule."""
    result = await db.execute(
        select(ScheduleEnrollment)
        .options(selectinload(ScheduleEnrollment.student))
        .where(ScheduleEnrollment.schedule_id == schedule_id)
    )
    enrollments = result.scalars().all()
    
    students = []
    for enrollment in enrollments:
        student = enrollment.student
        # Визначаємо телефон батьків (пріоритет матері, потім батька)
        parent_phone = student.phone_mother or student.phone_father or None
        
        students.append({
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": f"{student.first_name} {student.last_name}",
            "phone_parent": parent_phone,
            "active": True  # У Student немає поля active, вважаємо всіх активними
        })
    
    return sorted(students, key=lambda x: x["full_name"])


@router.get("/{conducted_lesson_id}", response_model=ConductedLessonResponse)
async def get_conducted_lesson(
    conducted_lesson_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conducted lesson."""
    result = await db.execute(
        select(ConductedLesson)
        .options(
            selectinload(ConductedLesson.teacher),
            selectinload(ConductedLesson.club),
            selectinload(ConductedLesson.lesson_event)
        )
        .where(ConductedLesson.id == conducted_lesson_id)
    )
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conducted lesson not found"
        )
    
    return ConductedLessonResponse(
        id=lesson.id,
        teacher_id=lesson.teacher_id,
        teacher_name=lesson.teacher.full_name if lesson.teacher else "N/A",
        club_id=lesson.club_id,
        club_name=lesson.club.name if lesson.club else "N/A",
        lesson_event_id=lesson.lesson_event_id,
        lesson_date=lesson.lesson_date,
        lesson_duration_minutes=lesson.lesson_duration_minutes,
        total_students=lesson.total_students,
        present_students=lesson.present_students,
        absent_students=lesson.absent_students,
        attendance_rate=lesson.attendance_rate,
        notes=lesson.notes,
        lesson_topic=lesson.lesson_topic,
        is_salary_calculated=lesson.is_salary_calculated,
        is_valid_for_salary=lesson.is_valid_for_salary,
        created_at=lesson.created_at
    )


@router.post("", response_model=ConductedLessonResponse)
async def create_conducted_lesson(
    lesson_data: ConductedLessonCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a conducted lesson from a lesson event."""
    
    # Перевіряємо чи існує lesson_event
    lesson_event_result = await db.execute(
        select(LessonEvent).where(LessonEvent.id == lesson_data.lesson_event_id)
    )
    lesson_event = lesson_event_result.scalar_one_or_none()
    
    if not lesson_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson event not found"
        )
    
    # Створюємо conducted lesson через сервіс
    service = ConductedLessonService(db)
    conducted_lesson = await service.create_from_lesson_event(
        lesson_event_id=lesson_data.lesson_event_id,
        notes=lesson_data.notes,
        lesson_topic=lesson_data.lesson_topic
    )
    
    if not conducted_lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create conducted lesson"
        )
    
    # Завантажуємо з зв'язками для response
    result = await db.execute(
        select(ConductedLesson)
        .options(
            selectinload(ConductedLesson.teacher),
            selectinload(ConductedLesson.club)
        )
        .where(ConductedLesson.id == conducted_lesson.id)
    )
    lesson = result.scalar_one()
    
    logger.info(f"Created conducted lesson {lesson.id} for lesson_event {lesson_data.lesson_event_id}")
    
    return ConductedLessonResponse(
        id=lesson.id,
        teacher_id=lesson.teacher_id,
        teacher_name=lesson.teacher.full_name if lesson.teacher else "N/A",
        club_id=lesson.club_id,
        club_name=lesson.club.name if lesson.club else "N/A",
        lesson_event_id=lesson.lesson_event_id,
        lesson_date=lesson.lesson_date,
        lesson_duration_minutes=lesson.lesson_duration_minutes,
        total_students=lesson.total_students,
        present_students=lesson.present_students,
        absent_students=lesson.absent_students,
        attendance_rate=lesson.attendance_rate,
        notes=lesson.notes,
        lesson_topic=lesson.lesson_topic,
        is_salary_calculated=lesson.is_salary_calculated,
        is_valid_for_salary=lesson.is_valid_for_salary,
        created_at=lesson.created_at
    )


@router.post("/manual", response_model=ConductedLessonResponse)
async def create_manual_conducted_lesson(
    lesson_data: ManualConductedLessonCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a manual conducted lesson without lesson event."""
    
    # Перевіряємо чи існує schedule
    schedule_result = await db.execute(
        select(Schedule)
        .options(
            selectinload(Schedule.teacher),
            selectinload(Schedule.club)
        )
        .where(Schedule.id == lesson_data.schedule_id)
    )
    schedule = schedule_result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Створюємо conducted lesson через сервіс
    service = ConductedLessonService(db)
    conducted_lesson = await service.create_manual(
        schedule_id=lesson_data.schedule_id,
        lesson_date=lesson_data.lesson_date,
        student_attendance=lesson_data.student_attendance,
        notes=lesson_data.notes,
        lesson_duration_minutes=lesson_data.lesson_duration_minutes,
        auto_calculate_payroll=lesson_data.auto_calculate_payroll
    )
    
    if not conducted_lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create manual conducted lesson"
        )
    
    # Завантажуємо з зв'язками для response
    result = await db.execute(
        select(ConductedLesson)
        .options(
            selectinload(ConductedLesson.teacher),
            selectinload(ConductedLesson.club)
        )
        .where(ConductedLesson.id == conducted_lesson.id)
    )
    lesson = result.scalar_one()
    
    logger.info(f"Created manual conducted lesson {lesson.id} for schedule {lesson_data.schedule_id}")
    
    return ConductedLessonResponse(
        id=lesson.id,
        teacher_id=lesson.teacher_id,
        teacher_name=lesson.teacher.full_name if lesson.teacher else "N/A",
        club_id=lesson.club_id,
        club_name=lesson.club.name if lesson.club else "N/A",
        lesson_event_id=lesson.lesson_event_id,
        lesson_date=lesson.lesson_date,
        lesson_duration_minutes=lesson.lesson_duration_minutes,
        total_students=lesson.total_students,
        present_students=lesson.present_students,
        absent_students=lesson.absent_students,
        attendance_rate=lesson.attendance_rate,
        notes=lesson.notes,
        lesson_topic=lesson.lesson_topic,
        is_salary_calculated=lesson.is_salary_calculated,
        is_valid_for_salary=lesson.is_valid_for_salary,
        created_at=lesson.created_at
    )


@router.put("/{conducted_lesson_id}", response_model=ConductedLessonResponse)
async def update_conducted_lesson(
    conducted_lesson_id: int,
    lesson_data: ConductedLessonUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a conducted lesson."""
    
    # Знаходимо урок
    result = await db.execute(
        select(ConductedLesson)
        .options(
            selectinload(ConductedLesson.teacher),
            selectinload(ConductedLesson.club)
        )
        .where(ConductedLesson.id == conducted_lesson_id)
    )
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conducted lesson not found"
        )
    
    # Оновлюємо поля
    update_data = lesson_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(lesson, field):
            setattr(lesson, field, value)
    
    # Валідація
    if lesson.present_students and lesson.total_students and lesson.present_students > lesson.total_students:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Present students cannot exceed total students"
        )
    
    # Автоматично обчислюємо відсутніх якщо задано загальну к-сть та присутніх
    if lesson.total_students is not None and lesson.present_students is not None:
        lesson.absent_students = lesson.total_students - lesson.present_students
    
    try:
        await db.commit()
        await db.refresh(lesson)
        
        logger.info(f"Updated conducted lesson {lesson.id}")
        
        return ConductedLessonResponse(
            id=lesson.id,
            teacher_id=lesson.teacher_id,
            teacher_name=lesson.teacher.full_name if lesson.teacher else "N/A",
            club_id=lesson.club_id,
            club_name=lesson.club.name if lesson.club else "N/A",
            lesson_event_id=lesson.lesson_event_id,
            lesson_date=lesson.lesson_date,
            lesson_duration_minutes=lesson.lesson_duration_minutes,
            total_students=lesson.total_students,
            present_students=lesson.present_students,
            absent_students=lesson.absent_students,
            attendance_rate=lesson.attendance_rate,
            notes=lesson.notes,
            lesson_topic=lesson.lesson_topic,
            is_salary_calculated=lesson.is_salary_calculated,
            is_valid_for_salary=lesson.is_valid_for_salary,
            created_at=lesson.created_at
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating conducted lesson {conducted_lesson_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update conducted lesson"
        )


@router.put("/{conducted_lesson_id}/mark_salary_calculated")
async def mark_salary_calculated(
    conducted_lesson_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Mark a conducted lesson as having salary calculated."""
    
    service = ConductedLessonService(db)
    success = await service.mark_salary_calculated(conducted_lesson_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to mark lesson as salary calculated"
        )
    
    return {"message": "Lesson marked as salary calculated successfully"}


@router.get("/statistics/teacher/{teacher_id}", response_model=TeacherStatisticsResponse)
async def get_teacher_statistics(
    teacher_id: int,
    start_date: date = Query(..., description="Start date for statistics"),
    end_date: date = Query(..., description="End date for statistics"),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for a teacher for a specific period."""
    
    # Перевіряємо чи існує вчитель
    teacher_result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id)
    )
    teacher = teacher_result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    # Отримуємо статистику через сервіс
    service = ConductedLessonService(db)
    stats = await service.get_teacher_statistics(
        teacher_id=teacher_id,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.max.time())
    )
    
    return TeacherStatisticsResponse(
        teacher_id=teacher_id,
        teacher_name=teacher.full_name,
        period_start=start_date,
        period_end=end_date,
        total_lessons=stats['total_lessons'],
        total_students=stats['total_students'],
        present_students=stats['present_students'],
        absent_students=stats['absent_students'],
        attendance_rate=stats['attendance_rate'],
        lessons_with_attendance=stats['lessons_with_attendance']
    )


@router.get("/statistics/uncalculated_count")
async def get_uncalculated_lessons_count(
    teacher_id: Optional[int] = Query(None, description="Filter by teacher ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get count of lessons that haven't had salary calculated yet."""
    
    service = ConductedLessonService(db)
    lessons = await service.get_uncalculated_lessons(teacher_id=teacher_id)
    
    return {
        "count": len(lessons),
        "lessons": [
            {
                "id": lesson.id,
                "teacher_name": lesson.teacher.full_name if lesson.teacher else "N/A",
                "club_name": lesson.club.name if lesson.club else "N/A",
                "lesson_date": lesson.lesson_date.isoformat(),
                "present_students": lesson.present_students
            }
            for lesson in lessons
        ]
    }


@router.delete("/{conducted_lesson_id}", status_code=status.HTTP_200_OK)
async def delete_conducted_lesson(
    conducted_lesson_id: int,
    force: bool = Query(False, description="Force delete with cascade removal of attendance and payroll"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conducted lesson with cascade removal of related data."""
    from app.models import Attendance, Payroll
    from sqlalchemy import delete
    
    # Перевіряємо чи існує conducted lesson
    try:
        result = await db.execute(
            select(ConductedLesson)
            .options(
                selectinload(ConductedLesson.teacher),
                selectinload(ConductedLesson.club),
                selectinload(ConductedLesson.lesson_event)
            )
            .where(ConductedLesson.id == conducted_lesson_id)
        )
        lesson = result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error loading conducted lesson {conducted_lesson_id}: {e}")
        # Спробуємо завантажити без club якщо є проблема
        result = await db.execute(
            select(ConductedLesson)
            .options(
                selectinload(ConductedLesson.teacher),
                selectinload(ConductedLesson.lesson_event)
            )
            .where(ConductedLesson.id == conducted_lesson_id)
        )
        lesson = result.scalar_one_or_none()
    
    if not lesson:
        logger.error(f"Conducted lesson {conducted_lesson_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conducted lesson not found"
        )
    
    logger.info(f"Processing delete request for conducted lesson {conducted_lesson_id}, force={force}")
    
    # Перевіряємо пов'язані дані
    logger.info(f"Checking dependencies for lesson_event_id: {lesson.lesson_event_id}")
    
    attendance_result = await db.execute(
        select(Attendance.id).where(Attendance.lesson_event_id == lesson.lesson_event_id)
    )
    attendance_count = len(attendance_result.scalars().all())
    logger.info(f"Found {attendance_count} attendance records")
    
    payroll_result = await db.execute(
        select(Payroll.id).where(Payroll.lesson_event_id == lesson.lesson_event_id)
    )
    payroll_count = len(payroll_result.scalars().all())
    logger.info(f"Found {payroll_count} payroll records")
    
    if not force and (attendance_count > 0 or payroll_count > 0):
        logger.info(f"Returning warning for conducted lesson {conducted_lesson_id}: {attendance_count} attendance, {payroll_count} payroll")
        return {
            "error": "Cannot delete conducted lesson",
            "message": f"Проведений урок має {attendance_count} записів відвідуваності та {payroll_count} записів зарплати. Для видалення використайте force=true",
            "conducted_lesson": {
                "id": lesson.id,
                "teacher_name": lesson.teacher.full_name if lesson.teacher else "N/A",
                "club_name": lesson.club.name if (lesson.club and hasattr(lesson.club, 'name')) else "Видалений гурток", 
                "lesson_date": lesson.lesson_date.strftime("%d.%m.%Y %H:%M") if lesson.lesson_date else "N/A",
                "total_students": lesson.total_students,
                "present_students": lesson.present_students
            },
            "dependencies": {
                "attendance_records": attendance_count,
                "payroll_records": payroll_count
            },
            "warning": "⚠️ Видалення видалить ВСІ відмітки відвідуваності та записи зарплати для цього уроку!"
        }
    
    # Якщо немає залежностей та force=False, запитуємо підтвердження
    if not force:
        logger.info(f"No dependencies found for conducted lesson {conducted_lesson_id}, asking for confirmation")
        return {
            "error": "Cannot delete conducted lesson",
            "message": f"Проведений урок не має залежностей, але потрібне підтвердження. Для видалення використайте force=true",
            "conducted_lesson": {
                "id": lesson.id,
                "teacher_name": lesson.teacher.full_name if lesson.teacher else "N/A",
                "club_name": lesson.club.name if (lesson.club and hasattr(lesson.club, 'name')) else "Видалений гурток", 
                "lesson_date": lesson.lesson_date.strftime("%d.%m.%Y %H:%M") if lesson.lesson_date else "N/A",
                "total_students": lesson.total_students,
                "present_students": lesson.present_students
            },
            "dependencies": {
                "attendance_records": attendance_count,
                "payroll_records": payroll_count
            },
            "warning": "⚠️ Видалення проведеного уроку є незворотним!"
        }
    
    try:
        # Каскадне видалення пов'язаних даних
        if force:
            # 1. Видаляємо attendance записи
            await db.execute(
                delete(Attendance).where(Attendance.lesson_event_id == lesson.lesson_event_id)
            )
            logger.info(f"Deleted {attendance_count} attendance records for lesson_event {lesson.lesson_event_id}")
            
            # 2. Видаляємо payroll записи  
            await db.execute(
                delete(Payroll).where(Payroll.lesson_event_id == lesson.lesson_event_id)
            )
            logger.info(f"Deleted {payroll_count} payroll records for lesson_event {lesson.lesson_event_id}")
            
            # 3. Видаляємо conducted lesson
            await db.execute(
                delete(ConductedLesson).where(ConductedLesson.id == conducted_lesson_id)
            )
            
            # 📝 AUDIT LOG: Видалення проведеного уроку (МАКСИМАЛЬНО ДЕТАЛЬНО)
            try:
                from app.services.audit_service import log_audit
                
                teacher_name = lesson.teacher.full_name if lesson.teacher else "(викладач не вказаний)"
                club_name = lesson.club.name if (lesson.club and hasattr(lesson.club, 'name')) else "(гурток видалений)"
                lesson_date_str = lesson.lesson_date.strftime("%d.%m.%Y %H:%M") if lesson.lesson_date else "(дата не вказана)"
                
                # Детальний опис з усіма параметрами
                detailed_description = (
                    f"Видалено проведений урок: {club_name}, викладач: {teacher_name}, "
                    f"дата: {lesson_date_str}. "
                    f"Присутніх учнів: {lesson.present_students}/{lesson.total_students}. "
                    f"Каскадно видалено: {attendance_count} записів відвідуваності, {payroll_count} записів зарплати."
                )
                
                await log_audit(
                    db=db,
                    action_type="DELETE",
                    entity_type="conducted_lesson",
                    entity_id=conducted_lesson_id,
                    entity_name=f"{club_name} - {lesson_date_str} ({teacher_name})",
                    description=detailed_description,
                    user_name="Адміністратор",
                    changes={
                        "deleted": {
                            "conducted_lesson_id": conducted_lesson_id,
                            "teacher": teacher_name,
                            "club": club_name,
                            "lesson_date": lesson_date_str,
                            "total_students": lesson.total_students,
                            "present_students": lesson.present_students,
                            "absent_students": lesson.absent_students if hasattr(lesson, 'absent_students') else 0,
                            "lesson_event_id": lesson.lesson_event_id,
                            "cascade_deleted": {
                                "attendance_records": attendance_count,
                                "payroll_records": payroll_count
                            }
                        }
                    }
                )
            except Exception as e:
                logger.error(f"❌ AUDIT LOG ERROR (conducted_lesson DELETE): {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            await db.commit()
            logger.info(f"Successfully deleted conducted lesson {conducted_lesson_id} with cascade data")
            
            return {
                "success": True,
                "message": f"Проведений урок #{conducted_lesson_id} успішно видалено",
                "deleted": {
                    "conducted_lesson": 1,
                    "attendance_records": attendance_count,
                    "payroll_records": payroll_count
                }
            }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting conducted lesson {conducted_lesson_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conducted lesson: {str(e)}"
        )


@router.get("/export/excel")
async def export_conducted_lessons_excel(
    teacher_id: Optional[int] = Query(None, description="Filter by teacher ID"),
    club_id: Optional[int] = Query(None, description="Filter by club ID"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """Export conducted lessons data to Excel."""
    
    try:
        import io
        import pandas as pd
        from fastapi.responses import StreamingResponse
        
        # Базовий запит
        query = (
            select(ConductedLesson)
            .options(
                selectinload(ConductedLesson.teacher),
                selectinload(ConductedLesson.club)
            )
            .order_by(ConductedLesson.lesson_date.desc())
        )
        
        # Фільтри
        if teacher_id:
            query = query.where(ConductedLesson.teacher_id == teacher_id)
        if club_id:
            query = query.where(ConductedLesson.club_id == club_id)
        if start_date:
            query = query.where(ConductedLesson.lesson_date >= start_date)
        if end_date:
            query = query.where(ConductedLesson.lesson_date <= end_date)
        
        result = await db.execute(query)
        lessons = result.scalars().all()
        
        if not lessons:
            raise HTTPException(status_code=404, detail="No conducted lessons found")
        
        # Підготуємо дані для Excel
        lessons_data = []
        for lesson in lessons:
            lessons_data.append({
                # === ОСНОВНА ІНФОРМАЦІЯ ===
                "Дата уроку": lesson.lesson_date.strftime("%d.%m.%Y") if lesson.lesson_date else "—",
                "Вчитель": lesson.teacher.full_name if lesson.teacher else "—",
                "Гурток": lesson.club.name if lesson.club else "—",
                "Тривалість (хв)": lesson.lesson_duration_minutes or "—",
                
                # === ВІДВІДУВАНІСТЬ ===
                "Всього учнів": lesson.total_students or 0,
                "Присутніх": lesson.present_students or 0,
                "Відсутніх": lesson.absent_students or 0,
                "Відсоток присутності": f"{(lesson.present_students / lesson.total_students * 100):.1f}%" if lesson.total_students > 0 else "—",
                
                # === ФІНАНСИ ===
                "Зарплата нарахована": "Так" if lesson.is_salary_calculated else "Ні",
                
                # === ДОДАТКОВА ІНФОРМАЦІЯ ===
                "Тема уроку": lesson.lesson_topic or "—",
                "Нотатки": lesson.notes or "—",
                
                # === СИСТЕМНА ІНФОРМАЦІЯ ===
                "Дата створення": lesson.created_at.strftime("%d.%m.%Y %H:%M") if lesson.created_at else "—"
            })
        
        # Створюємо DataFrame
        df = pd.DataFrame(lessons_data)
        
        # Створюємо Excel файл в пам'яті
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Проведені уроки', index=False)
            
            # Налаштовуємо ширину колонок
            worksheet = writer.sheets['Проведені уроки']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Додаємо статистику по вчителях
            teacher_stats = {}
            for lesson in lessons:
                teacher_name = lesson.teacher.full_name if lesson.teacher else "Невідомий"
                if teacher_name not in teacher_stats:
                    teacher_stats[teacher_name] = {
                        'lessons': 0, 
                        'total_students': 0, 
                        'present_students': 0,
                        'salary_calculated': 0
                    }
                teacher_stats[teacher_name]['lessons'] += 1
                teacher_stats[teacher_name]['total_students'] += lesson.total_students or 0
                teacher_stats[teacher_name]['present_students'] += lesson.present_students or 0
                if lesson.is_salary_calculated:
                    teacher_stats[teacher_name]['salary_calculated'] += 1
            
            stats_data = {
                'Вчитель': list(teacher_stats.keys()),
                'Проведених уроків': [stats['lessons'] for stats in teacher_stats.values()],
                'Всього учнів': [stats['total_students'] for stats in teacher_stats.values()],
                'Присутніх учнів': [stats['present_students'] for stats in teacher_stats.values()],
                'Зарплата нарахована': [stats['salary_calculated'] for stats in teacher_stats.values()],
                'Середня відвідуваність': [f"{(stats['present_students'] / stats['total_students'] * 100):.1f}%" if stats['total_students'] > 0 else "0%" for stats in teacher_stats.values()]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Статистика по вчителях', index=False)
        
        output.seek(0)
        
        # Генеруємо ім'я файлу з поточною датою
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"conducted_lessons_export_{today}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting conducted lessons: {str(e)}"
        )


@router.get("/{conducted_lesson_id}/students", response_model=List[StudentAttendanceResponse])
async def get_conducted_lesson_students(
    conducted_lesson_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get students with their attendance status for a conducted lesson."""
    
    # Перевіряємо чи існує conducted lesson
    lesson_result = await db.execute(
        select(ConductedLesson).where(ConductedLesson.id == conducted_lesson_id)
    )
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conducted lesson not found"
        )
    
    # Отримуємо всіх учнів з їх attendance для цього уроку
    result = await db.execute(
        select(Student, Attendance)
        .join(Attendance, Student.id == Attendance.student_id)
        .where(Attendance.lesson_event_id == lesson.lesson_event_id)
        .order_by(Student.first_name, Student.last_name)
    )
    
    students_data = []
    for student, attendance in result:
        students_data.append(StudentAttendanceResponse(
            student_id=student.id,
            first_name=student.first_name,
            last_name=student.last_name,
            full_name=f"{student.first_name} {student.last_name}",
            attendance_id=attendance.id,
            status=attendance.status.value  # Convert enum to string
        ))
    
    return students_data


@router.put("/{conducted_lesson_id}/students/{student_id}/status")
async def update_student_attendance_status(
    conducted_lesson_id: int,
    student_id: int,
    status_data: AttendanceUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update student attendance status for a conducted lesson."""
    
    # Перевіряємо чи існує conducted lesson
    lesson_result = await db.execute(
        select(ConductedLesson).where(ConductedLesson.id == conducted_lesson_id)
    )
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conducted lesson not found"
        )
    
    # Знаходимо attendance запис
    attendance_result = await db.execute(
        select(Attendance)
        .where(
            Attendance.lesson_event_id == lesson.lesson_event_id,
            Attendance.student_id == student_id
        )
    )
    attendance = attendance_result.scalar_one_or_none()
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    # Валідація статусу
    if status_data.status not in ['PRESENT', 'ABSENT']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be PRESENT or ABSENT"
        )
    
    try:
        # Зберігаємо старий статус для аудиту
        old_status = attendance.status.value if attendance.status else "не вказано"
        
        # Оновлюємо статус attendance
        from app.models.attendance import AttendanceStatus
        attendance.status = AttendanceStatus(status_data.status)
        
        # Пересчитуємо статистику conducted_lesson
        await _recalculate_lesson_statistics(lesson, db)
        
        # 📝 AUDIT LOG: Зміна статусу відвідуваності в проведеному уроці
        try:
            from app.services.audit_service import log_audit
            from app.models import Student, Club, Teacher
            
            # Завантажуємо додаткову інформацію
            student_result = await db.execute(select(Student).where(Student.id == student_id))
            student = student_result.scalar_one_or_none()
            student_name = f"{student.first_name} {student.last_name}" if student else "(учень видалений)"
            
            # Завантажуємо інформацію про урок
            lesson_with_relations = await db.execute(
                select(ConductedLesson)
                .options(selectinload(ConductedLesson.teacher), selectinload(ConductedLesson.club))
                .where(ConductedLesson.id == conducted_lesson_id)
            )
            lesson_full = lesson_with_relations.scalar_one_or_none()
            
            teacher_name = lesson_full.teacher.full_name if lesson_full and lesson_full.teacher else "(викладач не вказаний)"
            club_name = lesson_full.club.name if lesson_full and lesson_full.club else "(гурток не вказаний)"
            lesson_date_str = lesson_full.lesson_date.strftime("%d.%m.%Y %H:%M") if lesson_full and lesson_full.lesson_date else "(дата не вказана)"
            
            status_ua = {"PRESENT": "Присутній", "ABSENT": "Відсутній"}
            old_status_ua = status_ua.get(old_status, old_status)
            new_status_ua = status_ua.get(status_data.status, status_data.status)
            
            await log_audit(
                db=db,
                action_type="UPDATE",
                entity_type="attendance",
                entity_id=attendance.id,
                entity_name=f"{student_name} → {club_name} ({lesson_date_str})",
                description=f"Змінено відвідуваність учня {student_name} на уроці '{club_name}' ({teacher_name}, {lesson_date_str}): {old_status_ua} → {new_status_ua}",
                user_name="Адміністратор",
                changes={
                    "before": {"status": old_status, "status_ua": old_status_ua},
                    "after": {"status": status_data.status, "status_ua": new_status_ua},
                    "context": {
                        "student": student_name,
                        "club": club_name,
                        "teacher": teacher_name,
                        "lesson_date": lesson_date_str
                    }
                }
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (attendance UPDATE in conducted_lesson): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        
        logger.info(f"Updated attendance status for student {student_id} in lesson {conducted_lesson_id} to {status_data.status}")
        
        return {"success": True, "message": f"Статус відвідуваності оновлено на {status_data.status}"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating attendance status: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update attendance status"
        )


@router.delete("/{conducted_lesson_id}/students/{student_id}")
async def remove_student_from_lesson(
    conducted_lesson_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove student from conducted lesson (delete attendance record)."""
    
    # Перевіряємо чи існує conducted lesson
    lesson_result = await db.execute(
        select(ConductedLesson).where(ConductedLesson.id == conducted_lesson_id)
    )
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conducted lesson not found"
        )
    
    # Знаходимо attendance запис
    attendance_result = await db.execute(
        select(Attendance)
        .where(
            Attendance.lesson_event_id == lesson.lesson_event_id,
            Attendance.student_id == student_id
        )
    )
    attendance = attendance_result.scalar_one_or_none()
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in this lesson"
        )
    
    # Отримуємо ім'я учня для логування
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    try:
        # Зберігаємо дані для аудиту перед видаленням
        student_name = f"{student.first_name} {student.last_name}" if student else "(учень видалений)"
        attendance_status = attendance.status.value if attendance.status else "не вказано"
        
        # Завантажуємо інформацію про урок для деталей
        lesson_with_relations = await db.execute(
            select(ConductedLesson)
            .options(selectinload(ConductedLesson.teacher), selectinload(ConductedLesson.club))
            .where(ConductedLesson.id == conducted_lesson_id)
        )
        lesson_full = lesson_with_relations.scalar_one_or_none()
        
        teacher_name = lesson_full.teacher.full_name if lesson_full and lesson_full.teacher else "(викладач не вказаний)"
        club_name = lesson_full.club.name if lesson_full and lesson_full.club else "(гурток не вказаний)"
        lesson_date_str = lesson_full.lesson_date.strftime("%d.%m.%Y %H:%M") if lesson_full and lesson_full.lesson_date else "(дата не вказана)"
        
        # Видаляємо attendance запис
        await db.delete(attendance)
        
        # 📝 AUDIT LOG: Видалення учня з проведеного уроку
        try:
            from app.services.audit_service import log_audit
            
            status_ua = {"PRESENT": "Присутній", "ABSENT": "Відсутній"}
            status_ua_str = status_ua.get(attendance_status, attendance_status)
            
            await log_audit(
                db=db,
                action_type="DELETE",
                entity_type="attendance",
                entity_id=attendance.id,
                entity_name=f"{student_name} → {club_name} ({lesson_date_str})",
                description=f"Видалено учня {student_name} з проведеного уроку '{club_name}' ({teacher_name}, {lesson_date_str}). Статус був: {status_ua_str}",
                user_name="Адміністратор",
                changes={
                    "deleted": {
                        "student": student_name,
                        "club": club_name,
                        "teacher": teacher_name,
                        "lesson_date": lesson_date_str,
                        "status": attendance_status,
                        "status_ua": status_ua_str,
                        "conducted_lesson_id": conducted_lesson_id
                    }
                }
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (attendance DELETE from conducted_lesson): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Пересчитуємо статистику conducted_lesson
        await _recalculate_lesson_statistics(lesson, db)
        
        await db.commit()
        
        logger.info(f"Removed student {student_name} from conducted lesson {conducted_lesson_id}")
        
        return {"success": True, "message": f"Учня {student_name} видалено з уроку"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error removing student from lesson: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove student from lesson"
        )


async def _recalculate_lesson_statistics(lesson: ConductedLesson, db: AsyncSession):
    """Recalculate total, present, and absent students for a conducted lesson."""
    
    # Підраховуємо attendance
    result = await db.execute(
        select(Attendance)
        .where(Attendance.lesson_event_id == lesson.lesson_event_id)
    )
    attendance_records = result.scalars().all()
    
    total_students = len(attendance_records)
    present_students = sum(1 for a in attendance_records if a.status.value == 'PRESENT')
    absent_students = total_students - present_students
    
    # Оновлюємо conducted_lesson
    lesson.total_students = total_students
    lesson.present_students = present_students
    lesson.absent_students = absent_students
