"""Service for managing conducted lessons."""

from datetime import datetime, date, timezone
from typing import Optional, List
from sqlalchemy import select, update, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ConductedLesson, LessonEvent, Teacher, Club, Attendance, AttendanceStatus, Schedule, Student, ScheduleEnrollment
from app.models.lesson_event import LessonEventStatus
import logging

logger = logging.getLogger(__name__)


class ConductedLessonService:
    """Service for managing conducted lessons."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_from_lesson_event(
        self, 
        lesson_event_id: int,
        notes: Optional[str] = None,
        lesson_topic: Optional[str] = None
    ) -> Optional[ConductedLesson]:
        """
        Create a conducted lesson record from a completed lesson event.
        This is called automatically when attendance is finished in Telegram bot.
        """
        try:
            # Завантажуємо lesson_event з усіма зв'язками
            result = await self.db.execute(
                select(LessonEvent)
                .options(
                    selectinload(LessonEvent.teacher),
                    selectinload(LessonEvent.club),
                    selectinload(LessonEvent.attendance_records).selectinload(Attendance.student)
                )
                .where(LessonEvent.id == lesson_event_id)
            )
            lesson_event = result.scalar_one_or_none()
            
            if not lesson_event:
                logger.error(f"LessonEvent {lesson_event_id} not found")
                return None
            
            # Перевіряємо чи вже існує запис проведеного уроку
            existing_result = await self.db.execute(
                select(ConductedLesson).where(ConductedLesson.lesson_event_id == lesson_event_id)
            )
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                logger.info(f"ConductedLesson for lesson_event {lesson_event_id} already exists")
                return existing
            
            # Рахуємо статистику присутності
            attendance_stats = self._calculate_attendance_stats(lesson_event.attendance_records)
            
            # Визначаємо тривалість уроку
            duration_minutes = lesson_event.club.duration_min if lesson_event.club else None
            
            # Створюємо запис проведеного уроку
            # Використовуємо start_at якщо є, інакше date з поточним часом
            lesson_datetime = lesson_event.start_at or lesson_event.date
            if isinstance(lesson_datetime, date) and not isinstance(lesson_datetime, datetime):
                lesson_datetime = datetime.combine(lesson_datetime, datetime.now().time()).replace(tzinfo=timezone.utc)
            
            # Автоматично нараховуємо зарплату якщо є хоча б 1 присутня дитина
            auto_calculate_salary = attendance_stats['present'] > 0
            
            conducted_lesson = ConductedLesson(
                teacher_id=lesson_event.teacher_id,
                club_id=lesson_event.club_id,
                lesson_event_id=lesson_event_id,
                lesson_date=lesson_datetime,
                lesson_duration_minutes=duration_minutes,
                total_students=attendance_stats['total'],
                present_students=attendance_stats['present'],
                absent_students=attendance_stats['absent'],
                notes=notes,
                lesson_topic=lesson_topic,
                is_salary_calculated=auto_calculate_salary
            )
            
            self.db.add(conducted_lesson)
            await self.db.commit()
            await self.db.refresh(conducted_lesson)
            
            logger.info(
                f"Created ConductedLesson {conducted_lesson.id} for lesson_event {lesson_event_id}: "
                f"{attendance_stats['present']}/{attendance_stats['total']} students present"
            )
            
            return conducted_lesson
            
        except Exception as e:
            logger.error(f"Error creating ConductedLesson for lesson_event {lesson_event_id}: {e}")
            await self.db.rollback()
            return None
    
    def _calculate_attendance_stats(self, attendance_records: List[Attendance]) -> dict:
        """Calculate attendance statistics from attendance records."""
        total = len(attendance_records)
        present = sum(1 for record in attendance_records if record.status == AttendanceStatus.PRESENT)
        absent = total - present
        
        return {
            'total': total,
            'present': present,
            'absent': absent
        }
    
    async def mark_salary_calculated(self, conducted_lesson_id: int) -> bool:
        """Mark a conducted lesson as having salary calculated."""
        try:
            await self.db.execute(
                update(ConductedLesson)
                .where(ConductedLesson.id == conducted_lesson_id)
                .values(is_salary_calculated=True)
            )
            await self.db.commit()
            logger.info(f"Marked ConductedLesson {conducted_lesson_id} as salary calculated")
            return True
        except Exception as e:
            logger.error(f"Error marking ConductedLesson {conducted_lesson_id} as salary calculated: {e}")
            await self.db.rollback()
            return False
    
    async def get_uncalculated_lessons(self, teacher_id: Optional[int] = None) -> List[ConductedLesson]:
        """Get conducted lessons that haven't had salary calculated yet."""
        query = (
            select(ConductedLesson)
            .options(
                selectinload(ConductedLesson.teacher),
                selectinload(ConductedLesson.club),
                selectinload(ConductedLesson.lesson_event)
            )
            .where(ConductedLesson.is_salary_calculated == False)
            .where(ConductedLesson.present_students > 0)  # Only lessons with at least 1 present student
        )
        
        if teacher_id:
            query = query.where(ConductedLesson.teacher_id == teacher_id)
        
        query = query.order_by(ConductedLesson.lesson_date.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_lessons_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime,
        teacher_id: Optional[int] = None,
        club_id: Optional[int] = None
    ) -> List[ConductedLesson]:
        """Get conducted lessons for a specific period."""
        query = (
            select(ConductedLesson)
            .options(
                selectinload(ConductedLesson.teacher),
                selectinload(ConductedLesson.club),
                selectinload(ConductedLesson.lesson_event)
            )
            .where(ConductedLesson.lesson_date >= start_date)
            .where(ConductedLesson.lesson_date <= end_date)
        )
        
        if teacher_id:
            query = query.where(ConductedLesson.teacher_id == teacher_id)
        
        if club_id:
            query = query.where(ConductedLesson.club_id == club_id)
        
        query = query.order_by(ConductedLesson.lesson_date.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_teacher_statistics(self, teacher_id: int, start_date: datetime, end_date: datetime) -> dict:
        """Get statistics for a teacher for a specific period."""
        lessons = await self.get_lessons_for_period(start_date, end_date, teacher_id=teacher_id)
        
        if not lessons:
            return {
                'total_lessons': 0,
                'total_students': 0,
                'present_students': 0,
                'absent_students': 0,
                'attendance_rate': 0.0,
                'lessons_with_attendance': 0
            }
        
        total_lessons = len(lessons)
        total_students = sum(lesson.total_students for lesson in lessons)
        present_students = sum(lesson.present_students for lesson in lessons)
        absent_students = sum(lesson.absent_students for lesson in lessons)
        lessons_with_attendance = sum(1 for lesson in lessons if lesson.present_students > 0)
        
        attendance_rate = (present_students / total_students * 100) if total_students > 0 else 0.0
        
        return {
            'total_lessons': total_lessons,
            'total_students': total_students,
            'present_students': present_students,
            'absent_students': absent_students,
            'attendance_rate': attendance_rate,
            'lessons_with_attendance': lessons_with_attendance
        }

    async def recalculate_from_attendance(self, lesson_event_id: int) -> Optional[ConductedLesson]:
        """Пересчитати проведений урок на основі актуальної відвідуваності."""
        try:
            from app.models.attendance import AttendanceStatus
            
            # Знаходимо існуючий ConductedLesson
            result = await self.db.execute(
                select(ConductedLesson)
                .where(ConductedLesson.lesson_event_id == lesson_event_id)
            )
            conducted_lesson = result.scalar_one_or_none()
            
            if not conducted_lesson:
                logger.warning(f"ConductedLesson not found for lesson_event_id {lesson_event_id}")
                return None
            
            # Рахуємо актуальну відвідуваність
            attendance_result = await self.db.execute(
                select(
                    func.count(Attendance.id).label('total_students'),
                    func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label('present_students')
                )
                .where(Attendance.lesson_event_id == lesson_event_id)
            )
            attendance_stats = attendance_result.first()
            
            if attendance_stats and attendance_stats.total_students > 0:
                total_students = attendance_stats.total_students
                present_students = attendance_stats.present_students or 0
                absent_students = total_students - present_students
                
                # Оновлюємо ConductedLesson та автоматично нараховуємо зарплату
                conducted_lesson.total_students = total_students
                conducted_lesson.present_students = present_students
                conducted_lesson.absent_students = absent_students
                conducted_lesson.is_salary_calculated = present_students > 0  # Автоматично нараховуємо якщо є присутні
                conducted_lesson.updated_at = datetime.now()
                
                await self.db.commit()
                logger.info(f"🔄 Recalculated ConductedLesson {conducted_lesson.id}: {present_students}/{total_students} present")
                
                return conducted_lesson
            else:
                logger.warning(f"No attendance data found for lesson_event_id {lesson_event_id}")
                return conducted_lesson
                
        except Exception as e:
            logger.error(f"Error recalculating ConductedLesson for lesson_event_id {lesson_event_id}: {e}")
            await self.db.rollback()
            return None
    
    async def create_manual(
        self,
        schedule_id: int,
        lesson_date: datetime,
        student_attendance: List[dict],
        notes: Optional[str] = None,
        lesson_duration_minutes: Optional[int] = None,
        auto_calculate_payroll: bool = True
    ) -> Optional[ConductedLesson]:
        """
        Create a manual conducted lesson without lesson event.
        Used when teacher manually adds a lesson that wasn't scheduled through bot.
        
        Args:
            schedule_id: ID of the schedule/club
            lesson_date: When the lesson was conducted
            student_attendance: List of {"student_id": int, "status": "present"|"absent"}
            notes: Optional notes about the lesson
            lesson_duration_minutes: Optional duration override
            auto_calculate_payroll: Whether to automatically calculate payroll for the lesson
        
        Returns:
            Created ConductedLesson or None if failed
        """
        try:
            # Завантажуємо schedule з усіма зв'язками
            result = await self.db.execute(
                select(Schedule)
                .options(
                    selectinload(Schedule.teacher),
                    selectinload(Schedule.club),
                    selectinload(Schedule.enrolled_students).selectinload(ScheduleEnrollment.student)
                )
                .where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return None
            
            # Валідуємо student_attendance
            valid_student_ids = {enrollment.student_id for enrollment in schedule.enrolled_students}
            attendance_dict = {}
            
            for attendance_item in student_attendance:
                student_id = attendance_item.get("student_id")
                status = attendance_item.get("status", "present")
                
                if student_id not in valid_student_ids:
                    logger.warning(f"Student {student_id} not enrolled in schedule {schedule_id}")
                    continue
                
                if status not in ["present", "absent"]:
                    logger.warning(f"Invalid attendance status '{status}' for student {student_id}")
                    status = "present"  # За замовчуванням
                
                attendance_dict[student_id] = AttendanceStatus.PRESENT if status == "present" else AttendanceStatus.ABSENT
            
            # Рахуємо статистику
            total_students = len(attendance_dict)
            present_students = sum(1 for status in attendance_dict.values() if status == AttendanceStatus.PRESENT)
            absent_students = total_students - present_students
            
            # Визначаємо тривалість (з розкладу або переданий параметр)
            duration = lesson_duration_minutes or (schedule.club.duration_min if schedule.club else None)
            
            # Створюємо фіктивний LessonEvent для зв'язку (для вручних уроків)
            fake_lesson_event = LessonEvent(
                schedule_id=schedule_id,
                club_id=schedule.club_id,
                teacher_id=schedule.teacher_id,
                date=lesson_date.date(),
                start_at=lesson_date,
                notify_at=lesson_date,  # Для вручних уроків ставимо той самий час
                teacher_chat_id=schedule.teacher.tg_chat_id if schedule.teacher else None,
                status=LessonEventStatus.COMPLETED
            )
            
            self.db.add(fake_lesson_event)
            await self.db.flush()  # Отримуємо ID
            
            # Створюємо запис проведеного уроку
            conducted_lesson = ConductedLesson(
                teacher_id=schedule.teacher_id,
                club_id=schedule.club_id,
                lesson_event_id=fake_lesson_event.id,  # Використовуємо фіктивний lesson_event
                lesson_date=lesson_date,
                lesson_duration_minutes=duration,
                total_students=total_students,
                present_students=present_students,
                absent_students=absent_students,
                notes=notes,
                lesson_topic=None,  # Тема уроку не використовується
                is_salary_calculated=auto_calculate_payroll and present_students > 0  # Автоматично нараховуємо якщо запрошено та є присутні студенти
            )
            
            self.db.add(conducted_lesson)
            await self.db.flush()  # Отримуємо ID, але не комітимо ще
            
            # Створюємо attendance записи для синхронізації
            attendance_records = []
            for student_id, status in attendance_dict.items():
                attendance_record = Attendance(
                    lesson_event_id=fake_lesson_event.id,  # Посилаємось на фіктивний lesson_event
                    student_id=student_id,
                    status=status,
                    marked_by=None,  # Адміністратор вручну
                    marked_at=datetime.now(timezone.utc)
                )
                attendance_records.append(attendance_record)
                self.db.add(attendance_record)
            
            await self.db.commit()
            await self.db.refresh(conducted_lesson)
            
            logger.info(
                f"Created manual ConductedLesson {conducted_lesson.id} for schedule {schedule_id}: "
                f"{present_students}/{total_students} students present"
            )
            
            # АВТОМАТИЧНЕ НАРАХУВАННЯ ЗАРПЛАТИ (якщо запрошено)
            if auto_calculate_payroll and present_students > 0:
                try:
                    from app.services.payroll_service import PayrollService
                    payroll_service = PayrollService(self.db)
                    # Використовуємо fake_lesson_event.id для payroll system
                    payroll_record = await payroll_service.create_automatic_payroll(fake_lesson_event.id)
                    if payroll_record:
                        logger.info(f"✅ Auto-created payroll {payroll_record.id} for manual lesson {conducted_lesson.id}: {payroll_record.amount_decimal} ₴")
                    else:
                        logger.info(f"ℹ️ No payroll created for manual lesson {conducted_lesson.id} (no active pay rate or already exists)")
                except Exception as payroll_error:
                    logger.warning(f"❌ Failed to auto-create payroll for manual lesson {conducted_lesson.id}: {payroll_error}")
                    # Не перериваємо процес якщо payroll не вдався, але логуємо помилку
            else:
                logger.info(f"ℹ️ Auto-payroll skipped for manual lesson {conducted_lesson.id}: auto_calculate={auto_calculate_payroll}, present_students={present_students}")
            
            return conducted_lesson
            
        except Exception as e:
            logger.error(f"Error creating manual ConductedLesson for schedule {schedule_id}: {e}")
            await self.db.rollback()
            return None
