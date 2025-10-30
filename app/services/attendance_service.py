"""Attendance service for managing student attendance."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Attendance,
    AttendanceStatus,
    LessonEvent,
    LessonEventStatus,
    Student,
    Enrollment,
    ScheduleEnrollment,
    Payroll,
)
from app.services.payroll_service import PayrollService

logger = logging.getLogger(__name__)


class AttendanceService:
    """Service for managing attendance operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.payroll_service = PayrollService(db)
    
    async def toggle_attendance(self, lesson_event_id: int, student_id: int) -> None:
        """Toggle student attendance status."""
        try:
            # Get existing attendance record
            result = await self.db.execute(
                select(Attendance).where(
                    Attendance.lesson_event_id == lesson_event_id,
                    Attendance.student_id == student_id,
                )
            )
            attendance = result.scalar_one_or_none()
            
            if attendance:
                # Toggle existing status
                new_status = (
                    AttendanceStatus.ABSENT
                    if attendance.status == AttendanceStatus.PRESENT
                    else AttendanceStatus.PRESENT
                )
                attendance.status = new_status
                attendance.marked_at = datetime.utcnow()
            else:
                # Create new attendance record (default to present)
                attendance = Attendance(
                    lesson_event_id=lesson_event_id,
                    student_id=student_id,
                    status=AttendanceStatus.PRESENT,
                )
                self.db.add(attendance)
            
            await self.db.commit()
            logger.info(
                f"Toggled attendance for student {student_id} "
                f"in lesson event {lesson_event_id}"
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error toggling attendance: {e}")
            raise
    
    async def save_attendance(self, lesson_event_id: int, marked_by: int) -> None:
        """Save attendance and complete lesson event."""
        try:
            # 1. Отримуємо lesson_event
            lesson_result = await self.db.execute(
                select(LessonEvent).where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = lesson_result.scalar_one_or_none()
            if not lesson_event:
                raise ValueError(f"LessonEvent {lesson_event_id} not found")
            
            # 2. Отримуємо всіх студентів записаних на цей розклад
            students_result = await self.db.execute(
                select(Student.id)
                .join(ScheduleEnrollment)
                .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
            )
            all_student_ids = [row[0] for row in students_result.fetchall()]
            
            # 3. Отримуємо студентів які вже мають attendance записи
            existing_result = await self.db.execute(
                select(Attendance.student_id)
                .where(Attendance.lesson_event_id == lesson_event_id)
            )
            existing_student_ids = [row[0] for row in existing_result.fetchall()]
            
            # 4. Створюємо attendance записи для студентів які їх не мають (за замовчуванням PRESENT)
            missing_student_ids = set(all_student_ids) - set(existing_student_ids)
            
            from sqlalchemy.dialects.postgresql import insert
            if missing_student_ids:
                for student_id in missing_student_ids:
                    stmt = insert(Attendance).values(
                        lesson_event_id=lesson_event_id,
                        student_id=student_id,
                        status=AttendanceStatus.PRESENT,  # За замовчуванням присутній
                        marked_by=marked_by,
                        marked_at=datetime.now()
                    )
                    # На випадок конфлікту (хоча не повинно бути)
                    stmt = stmt.on_conflict_do_nothing()
                    await self.db.execute(stmt)
                
                logger.info(f"Created {len(missing_student_ids)} default PRESENT attendance records")
            
            # 5. Update lesson event status
            await self.db.execute(
                update(LessonEvent)
                .where(LessonEvent.id == lesson_event_id)
                .values(
                    status=LessonEventStatus.COMPLETED,
                    completed_at=datetime.now(),
                )
            )
            
            # 6. Update attendance records with marked_by
            await self.db.execute(
                update(Attendance)
                .where(Attendance.lesson_event_id == lesson_event_id)
                .values(marked_by=marked_by)
            )
            
            # 7. Create payroll entry
            await self.payroll_service.create_automatic_payroll(lesson_event_id)
            
            await self.db.commit()
            logger.info(f"Saved attendance for lesson event {lesson_event_id} ({len(all_student_ids)} students total)")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error saving attendance: {e}")
            raise
    
    async def update_attendance(self, lesson_event_id: int, student_id: int, status: str) -> None:
        """Update attendance status for a specific student."""
        try:
            # Update attendance record
            await self.db.execute(
                update(Attendance)
                .where(
                    Attendance.lesson_event_id == lesson_event_id,
                    Attendance.student_id == student_id
                )
                .values(status=status, updated_at=datetime.utcnow())
            )
            
            logger.info(f"Updated attendance for student {student_id} in lesson {lesson_event_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error updating attendance: {e}")
            raise
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error saving attendance: {e}")
            raise
    
    async def get_lesson_attendance(
        self, lesson_event_id: int
    ) -> List[tuple[Student, Optional[AttendanceStatus]]]:
        """Get attendance data for a lesson event."""
        result = await self.db.execute(
            select(Student, Attendance.status)
            .join(ScheduleEnrollment)
            .join(LessonEvent, LessonEvent.schedule_id == ScheduleEnrollment.schedule_id)
            .outerjoin(
                Attendance,
                (Attendance.lesson_event_id == lesson_event_id)
                & (Attendance.student_id == Student.id),
            )
            .where(LessonEvent.id == lesson_event_id)
            .order_by(Student.first_name, Student.last_name)
        )
        
        return result.all()
    
    async def get_present_count(self, lesson_event_id: int) -> int:
        """Get count of present students for a lesson event."""
        result = await self.db.execute(
            select(Attendance).where(
                Attendance.lesson_event_id == lesson_event_id,
                Attendance.status == AttendanceStatus.PRESENT,
            )
        )
        return len(result.scalars().all())
    
    async def create_default_attendance(self, lesson_event_id: int) -> None:
        """Create default attendance records (all absent) for enrolled students."""
        try:
            # Get lesson event
            result = await self.db.execute(
                select(LessonEvent).where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = result.scalar_one_or_none()
            
            if not lesson_event:
                logger.error(f"Lesson event {lesson_event_id} not found")
                return
            
            # Get enrolled students
            result = await self.db.execute(
                select(Student.id)
                .join(ScheduleEnrollment)
                .where(ScheduleEnrollment.schedule_id == lesson_event.schedule_id)
            )
            student_ids = result.scalars().all()
            
            # Create attendance records
            for student_id in student_ids:
                # Check if attendance already exists
                existing = await self.db.execute(
                    select(Attendance).where(
                        Attendance.lesson_event_id == lesson_event_id,
                        Attendance.student_id == student_id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # Skip if already exists
                
                attendance = Attendance(
                    lesson_event_id=lesson_event_id,
                    student_id=student_id,
                    status=AttendanceStatus.ABSENT,  # Default to absent
                )
                self.db.add(attendance)
            
            await self.db.commit()
            logger.info(f"Created default attendance for lesson event {lesson_event_id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating default attendance: {e}")
            raise
