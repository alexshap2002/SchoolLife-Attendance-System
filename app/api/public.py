"""Public API endpoints for web admin interface (no auth required)."""

import logging
from datetime import datetime, time, date, timezone, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, status, Query, Response, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, update, text, func, extract, case, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.api.dependencies import DbSession, get_db
from app.models import Student, Teacher, Club, Schedule, Enrollment, ScheduleEnrollment, Attendance, LessonEvent, AttendanceStatus, LessonEventStatus, ConductedLesson, Payroll

router = APIRouter(prefix="/api", tags=["public"])


# === STUDENTS ===
class StudentCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    age: Optional[int] = None
    grade: Optional[str] = None
    phone_child: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    parent_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    phone_mother: Optional[str] = None
    phone_father: Optional[str] = None
    settlement_type: Optional[str] = None
    
    # Пільги для діаграм
    benefit_low_income: bool = False
    benefit_large_family: bool = False
    benefit_military_family: bool = False
    benefit_internally_displaced: bool = False
    benefit_orphan: bool = False
    benefit_disability: bool = False
    benefit_social_risk: bool = False
    benefit_other: Optional[str] = None


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = None
    phone_child: Optional[str] = None
    parent_name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    phone_mother: Optional[str] = None
    phone_father: Optional[str] = None
    settlement_type: Optional[str] = None
    birth_date: Optional[date] = None
    
    # Пільги для діаграм
    benefit_low_income: Optional[bool] = None
    benefit_large_family: Optional[bool] = None
    benefit_military_family: Optional[bool] = None
    benefit_internally_displaced: Optional[bool] = None
    benefit_orphan: Optional[bool] = None
    benefit_disability: Optional[bool] = None
    benefit_social_risk: Optional[bool] = None
    benefit_other: Optional[str] = None


class StudentResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    birth_date: Optional[date]
    age: Optional[int]
    grade: Optional[str]
    phone_child: Optional[str]
    location: Optional[str]
    address: Optional[str]
    parent_name: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    phone_mother: Optional[str]
    phone_father: Optional[str]
    settlement_type: Optional[str]
    created_at: datetime
    
    # Пільги для діаграм (без default значень щоб брались з БД)
    benefit_low_income: bool
    benefit_large_family: bool
    benefit_military_family: bool
    benefit_internally_displaced: bool
    benefit_orphan: bool
    benefit_disability: bool
    benefit_social_risk: bool
    benefit_other: Optional[str]

    class Config:
        from_attributes = True


@router.get("/students", response_model=List[StudentResponse])
async def get_students(db: DbSession) -> List[Student]:
    """Get all students."""
    result = await db.execute(select(Student).order_by(Student.first_name, Student.last_name))
    return result.scalars().all()


@router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: DbSession) -> Student:
    """Get student by ID."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.post("/students", response_model=StudentResponse, status_code=201)
async def create_student(student_data: StudentCreate, db: DbSession) -> Student:
    """Create new student."""
    student = Student(**student_data.model_dump())
    db.add(student)
    await db.flush()  # Отримуємо ID
    
    # 📝 AUDIT LOG: Створення учня (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        from datetime import date
        
        # Конвертуємо дати в строки для JSON
        birth_date_str = student.birth_date.isoformat() if isinstance(student.birth_date, date) else student.birth_date
        
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="student",
            entity_id=student.id,
            entity_name=f"{student.first_name} {student.last_name}",
            description=f"Створено нового учня: {student.first_name} {student.last_name}, клас {student.grade or 'не вказано'}",
            user_name="Адміністратор",
            changes={"after": {"first_name": student.first_name, "last_name": student.last_name, "grade": student.grade, "birth_date": birth_date_str}}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (student CREATE in public.py): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(student)
    return student


@router.put("/students/{student_id}", response_model=StudentResponse)
async def update_student(student_id: int, student_data: StudentUpdate, db: DbSession) -> Student:
    """Update student."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    update_data = student_data.model_dump(exclude_unset=True)
    for field in update_data.keys():
        old_values[field] = getattr(student, field, None)
    
    # Оновлення полів
    for field, value in update_data.items():
        if hasattr(student, field):
            setattr(student, field, value)
    
    # 📝 AUDIT LOG: Оновлення учня (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        from datetime import date
        
        # Конвертуємо дати в строки для JSON
        def serialize_for_json(obj):
            if isinstance(obj, date):
                return obj.isoformat()
            return obj
        
        old_values_json = {k: serialize_for_json(v) for k, v in old_values.items()}
        update_data_json = {k: serialize_for_json(v) for k, v in update_data.items()}
        
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {v}" for k, v in update_data.items() if old_values.get(k) != v])
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="student",
            entity_id=student.id,
            entity_name=f"{student.first_name} {student.last_name}",
            description=f"Оновлено дані учня: {student.first_name} {student.last_name}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values_json, "after": update_data_json}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (student UPDATE in public.py): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(student)
    return student


@router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: DbSession) -> Student:
    """Get student by ID."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.delete("/students/{student_id}", status_code=204)
async def delete_student(student_id: int, db: DbSession) -> None:
    """Delete student with proper cascade handling."""
    from app.models import Enrollment, ScheduleEnrollment, Attendance
    
    # Перевіряємо чи існує студент
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Зберігаємо ім'я для аудиту перед видаленням
    student_name = f"{student.first_name} {student.last_name}"
    
    try:
        # 1. Видаляємо attendance records
        await db.execute(
            delete(Attendance).where(Attendance.student_id == student_id)
        )
        
        # 2. Видаляємо enrollments  
        await db.execute(
            delete(Enrollment).where(Enrollment.student_id == student_id)
        )
        
        # 3. Видаляємо schedule enrollments
        await db.execute(
            delete(ScheduleEnrollment).where(ScheduleEnrollment.student_id == student_id)
        )
        
        # 4. Тепер можемо безпечно видалити студента
        await db.execute(delete(Student).where(Student.id == student_id))
        
        # 📝 AUDIT LOG: Видалення учня (ПЕРЕД commit!)
        try:
            from app.services.audit_service import log_audit
            await log_audit(
                db=db,
                action_type="DELETE",
                entity_type="student",
                entity_id=student_id,
                entity_name=student_name,
                description=f"Видалено учня: {student_name}",
                user_name="Адміністратор",
                changes={"deleted": {"id": student_id, "name": student_name}}
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (student DELETE in public.py): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting student: {str(e)}"
        )


# === TEACHERS ===
class TeacherCreate(BaseModel):
    full_name: str
    tg_username: Optional[str] = None
    tg_chat_id: Optional[int] = None
    active: bool = True


class TeacherUpdate(BaseModel):
    full_name: Optional[str] = None
    tg_username: Optional[str] = None
    tg_chat_id: Optional[int] = None
    active: Optional[bool] = None


class TeacherResponse(BaseModel):
    id: int
    full_name: str
    tg_chat_id: Optional[int]
    tg_username: Optional[str]
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/teachers", response_model=List[TeacherResponse])
async def get_teachers(db: DbSession) -> List[Teacher]:
    """Get all teachers."""
    result = await db.execute(select(Teacher).order_by(Teacher.full_name))
    return result.scalars().all()


@router.get("/teachers/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(teacher_id: int, db: DbSession) -> Teacher:
    """Get teacher by ID."""
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.post("/teachers", response_model=TeacherResponse, status_code=201)
async def create_teacher(teacher_data: TeacherCreate, db: DbSession) -> Teacher:
    """Create new teacher with automatic default pay rate."""
    try:
        # Перевіряємо чи не існує вчитель з таким tg_chat_id
        if teacher_data.tg_chat_id:
            existing_teacher_result = await db.execute(
                select(Teacher).where(Teacher.tg_chat_id == teacher_data.tg_chat_id)
            )
            existing_teacher = existing_teacher_result.scalar_one_or_none()
            
            if existing_teacher:
                raise HTTPException(
                    status_code=400,
                    detail=f"Вчитель з Telegram Chat ID {teacher_data.tg_chat_id} вже існує. "
                           f"Ім'я: '{existing_teacher.full_name}', Username: '@{existing_teacher.tg_username}'. "
                           f"Використайте функцію редагування для оновлення даних існуючого вчителя."
                )
        
        # Створюємо вчителя
        teacher = Teacher(**teacher_data.model_dump())
        db.add(teacher)
        await db.commit()
        await db.refresh(teacher)
        
        # 💰 АВТОМАТИЧНО СТВОРЮЄМО БАЗОВИЙ ТАРИФ 200₴ ЗА УРОК
        from app.models.pay_rate import PayRate, PayRateType
        from decimal import Decimal
        from datetime import date
        
        default_pay_rate = PayRate(
            teacher_id=teacher.id,
            rate_type=PayRateType.PER_LESSON,
            amount_decimal=Decimal("200.00"),
            active_from=date.today(),
            active_to=None  # Безстроковий
        )
        
        db.add(default_pay_rate)
        
        # 📝 AUDIT LOG: Створення вчителя (ПЕРЕД commit!)
        try:
            from app.services.audit_service import log_audit
            await log_audit(
                db=db,
                action_type="CREATE",
                entity_type="teacher",
                entity_id=teacher.id,
                entity_name=teacher.full_name,
                description=f"Створено нового вчителя: {teacher.full_name}, Telegram: @{teacher.tg_username or 'не вказано'}. Автоматично створено базовий тариф 200₴ за урок.",
                user_name="Адміністратор",
                changes={"after": {
                    "full_name": teacher.full_name,
                    "tg_username": teacher.tg_username,
                    "tg_chat_id": teacher.tg_chat_id,
                    "active": teacher.active,
                    "default_pay_rate": "200₴ за урок"
                }}
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (teacher CREATE in public.py): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        
        logger.info(f"💰 Created default pay rate 200₴ per lesson for teacher {teacher.full_name} (ID: {teacher.id})")
        
        return teacher
        
    except HTTPException:
        # Пропускаємо наші власні HTTPException
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating teacher: {e}")
        
        # Перевіряємо конкретні типи помилок SQLAlchemy
        if "duplicate key value violates unique constraint" in str(e):
            if "teachers_tg_chat_id_key" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail=f"Вчитель з Telegram Chat ID {teacher_data.tg_chat_id} вже існує в системі. "
                           "Кожен вчитель повинен мати унікальний Chat ID."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Вчитель з такими даними вже існує в системі."
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Помилка створення вчителя: {str(e)}"
            )


@router.put("/teachers/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(teacher_id: int, teacher_data: TeacherUpdate, db: DbSession) -> Teacher:
    """Update teacher."""
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    update_data = teacher_data.model_dump(exclude_unset=True)
    for field in update_data.keys():
        old_values[field] = getattr(teacher, field, None)
    
    # Оновлення полів
    for field, value in update_data.items():
        if hasattr(teacher, field):
            setattr(teacher, field, value)
    
    # 📝 AUDIT LOG: Оновлення вчителя (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {v}" for k, v in update_data.items() if old_values.get(k) != v])
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="teacher",
            entity_id=teacher.id,
            entity_name=teacher.full_name,
            description=f"Оновлено дані вчителя: {teacher.full_name}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": update_data}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (teacher UPDATE in public.py): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(teacher)
    return teacher


@router.delete("/teachers/{teacher_id}", status_code=200)
async def delete_teacher(
    teacher_id: int, 
    db: DbSession,
    force: bool = Query(False, description="Force delete with all dependencies")
) -> dict:
    """Delete teacher with dependency check and physical removal."""
    print(f"🎯 PUBLIC DELETE TEACHER: id={teacher_id}, force={force}")
    from sqlalchemy import update, func
    from app.models import Schedule, LessonEvent, Payroll, ConductedLesson, PayRate, BotSchedule
    
    # Перевіряємо чи існує вчитель
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Зберігаємо ім'я для аудиту
    teacher_name = teacher.full_name
    
    # Перевіряємо залежності
    schedules_count = await db.execute(
        select(func.count(Schedule.id)).where(Schedule.teacher_id == teacher_id)
    )
    schedules_count = schedules_count.scalar() or 0
    
    lesson_events_count = await db.execute(
        select(func.count(LessonEvent.id)).where(LessonEvent.teacher_id == teacher_id)
    )
    lesson_events_count = lesson_events_count.scalar() or 0
    
    # Додаємо перевірку PayRate
    pay_rates_count = await db.execute(
        select(func.count(PayRate.id)).where(PayRate.teacher_id == teacher_id)
    )
    pay_rates_count = pay_rates_count.scalar() or 0
    
    has_dependencies = schedules_count > 0 or lesson_events_count > 0 or pay_rates_count > 0
    
    try:
        if has_dependencies and not force:
            # Якщо є залежності і НЕ force - деактивуємо
            teacher.active = False
            
            # Деактивуємо всі його розклади
            await db.execute(
                update(Schedule)
                .where(Schedule.teacher_id == teacher_id)
                .values(active=False)
            )
            
            # 📝 AUDIT LOG: Деактивація вчителя (ПЕРЕД commit!)
            try:
                from app.services.audit_service import log_audit
                await log_audit(
                    db=db,
                    action_type="UPDATE",
                    entity_type="teacher",
                    entity_id=teacher_id,
                    entity_name=teacher_name,
                    description=f"Деактивовано вчителя: {teacher_name} (через наявність залежностей: розкладів={schedules_count}, уроків={lesson_events_count}, ставок={pay_rates_count})",
                    user_name="Адміністратор",
                    changes={"action": "deactivated", "active": {"before": True, "after": False}, "dependencies": {"schedules": schedules_count, "lesson_events": lesson_events_count, "pay_rates": pay_rates_count}}
                )
            except Exception as e:
                logger.error(f"❌ AUDIT LOG ERROR (teacher DEACTIVATE in public.py): {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            await db.commit()
            
            return {
                "success": True,
                "action": "deactivated",
                "message": f"Вчитель '{teacher.full_name}' деактивовано через наявність залежностей",
                "teacher": teacher.full_name,
                "dependencies": {
                    "schedules": schedules_count,
                    "lesson_events": lesson_events_count,
                    "pay_rates": pay_rates_count
                },
                "note": "Для повного видалення використайте force=true"
            }
        elif force and has_dependencies:
            # 🎯 РОЗУМНЕ ВИДАЛЕННЯ З ЗБЕРЕЖЕННЯМ ІСТОРІЇ
            print(f"🚨 SMART DELETE teacher {teacher_id}: {teacher.full_name}")
            print(f"📊 Dependencies: schedules={schedules_count}, events={lesson_events_count}, pay_rates={pay_rates_count}")
            
            # ✨ КРОК 1: Створюємо placeholder для видаленого вчителя
            deleted_teacher_name = f"[ВИДАЛЕНО] {teacher.full_name}"
            
            # Перевіряємо чи існує вже placeholder
            placeholder_result = await db.execute(
                select(Teacher).where(Teacher.full_name == deleted_teacher_name)
            )
            placeholder_teacher = placeholder_result.scalar_one_or_none()
            
            if not placeholder_teacher:
                # Створюємо placeholder вчителя
                placeholder_teacher = Teacher(
                    full_name=deleted_teacher_name,
                    active=False,
                    tg_chat_id=None,
                    tg_username=None
                )
                db.add(placeholder_teacher)
                await db.flush()  # Отримуємо ID
            
            placeholder_id = placeholder_teacher.id
            
            # 🗑️ КРОК 2: Видаляємо non-historical дані
            
            # 2.1. Видаляємо bot schedules (автоматичні нагадування)
            await db.execute(
                delete(BotSchedule).where(BotSchedule.schedule_id.in_(
                    select(Schedule.id).where(Schedule.teacher_id == teacher_id)
                ))
            )
            
            # 2.2. Видаляємо pay rates (налаштування ставок)
            await db.execute(
                delete(PayRate).where(PayRate.teacher_id == teacher_id)
            )
            
            # 2.3. Видаляємо ТІЛЬКИ lesson events БЕЗ attendance (майбутні уроки)
            future_events_result = await db.execute(
                delete(LessonEvent)
                .where(
                    LessonEvent.teacher_id == teacher_id,
                    ~LessonEvent.id.in_(
                        select(Attendance.lesson_event_id).distinct()
                    )
                )
                .returning(LessonEvent.id)
            )
            deleted_future_events = len(future_events_result.all())
            
            # 🔄 КРОК 3: Переносимо історичні дані на placeholder
            
            # 3.1. Переносимо conducted lessons на placeholder
            await db.execute(
                update(ConductedLesson)
                .where(ConductedLesson.teacher_id == teacher_id)
                .values(teacher_id=placeholder_id)
            )
            
            # 3.2. Переносимо payroll на placeholder
            await db.execute(
                update(Payroll)
                .where(Payroll.teacher_id == teacher_id)
                .values(teacher_id=placeholder_id)
            )
            
            # 3.3. Переносимо lesson events з attendance на placeholder
            await db.execute(
                update(LessonEvent)
                .where(
                    LessonEvent.teacher_id == teacher_id,
                    LessonEvent.id.in_(
                        select(Attendance.lesson_event_id).distinct()
                    )
                )
                .values(teacher_id=placeholder_id)
            )
            
            # 3.4. Деактивуємо schedules (але залишаємо для історії lesson_events)
            await db.execute(
                update(Schedule)
                .where(Schedule.teacher_id == teacher_id)
                .values(active=False, teacher_id=placeholder_id)
            )
            
            # 🗑️ КРОК 4: Видаляємо основного вчителя
            await db.execute(
                delete(Teacher).where(Teacher.id == teacher_id)
            )
            
            # 📝 AUDIT LOG: Видалення вчителя з force (ПЕРЕД commit!)
            try:
                from app.services.audit_service import log_audit
                await log_audit(
                    db=db,
                    action_type="DELETE",
                    entity_type="teacher",
                    entity_id=teacher_id,
                    entity_name=teacher_name,
                    description=f"Видалено вчителя: {teacher_name} (з force=true). Створено placeholder '{deleted_teacher_name}' для збереження історії. Видалено: ставки зарплати={pay_rates_count}, майбутні уроки={deleted_future_events}.",
                    user_name="Адміністратор",
                    changes={"action": "smart_deleted", "force": True, "deleted": {"pay_rates": pay_rates_count, "future_events": deleted_future_events}, "placeholder": deleted_teacher_name}
                )
            except Exception as e:
                logger.error(f"❌ AUDIT LOG ERROR (teacher FORCE DELETE in public.py): {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            await db.commit()
            
            return {
                "success": True,
                "action": "smart_deleted",
                "message": f"Вчитель '{teacher.full_name}' видалено з збереженням історичних даних",
                "teacher": teacher.full_name,
                "placeholder_created": deleted_teacher_name,
                "deleted": {
                    "teacher": teacher.full_name,
                    "pay_rates": pay_rates_count,
                    "future_lesson_events": deleted_future_events,
                    "bot_schedules": "автоматично"
                },
                "preserved_on_placeholder": {
                    "conducted_lessons": "Проведені уроки для звітності",
                    "payroll": "Зарплатні нарахування для бухгалтерії", 
                    "attendance": "Записи відвідуваності (через lesson_events)",
                    "historical_lesson_events": "Проведені уроки з відвідуваністю",
                    "schedules": "Деактивовані розклади для зв'язку з lesson_events"
                }
            }
        else:
            # Немає залежностей - видаляємо повністю (через SQL щоб уникнути ORM cascade)
            await db.execute(
                delete(Teacher).where(Teacher.id == teacher_id)
            )
            
            # 📝 AUDIT LOG: Видалення вчителя (ПЕРЕД commit!)
            try:
                from app.services.audit_service import log_audit
                await log_audit(
                    db=db,
                    action_type="DELETE",
                    entity_type="teacher",
                    entity_id=teacher_id,
                    entity_name=teacher_name,
                    description=f"Видалено вчителя: {teacher_name} (без залежностей)",
                    user_name="Адміністратор",
                    changes={"action": "simple_deleted", "no_dependencies": True}
                )
            except Exception as e:
                logger.error(f"❌ AUDIT LOG ERROR (teacher SIMPLE DELETE in public.py): {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            await db.commit()
            
            return {
                "success": True,
                "action": "deleted",
                "message": f"Вчитель '{teacher.full_name}' повністю видалено",
                "teacher": teacher.full_name
            }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing teacher: {str(e)}"
        )


@router.get("/teachers/{teacher_id}/dependencies")
async def get_teacher_dependencies(teacher_id: int, db: DbSession) -> dict:
    """Get teacher dependencies for smart deletion warning."""
    from sqlalchemy import func
    from app.models import Schedule, LessonEvent, Payroll, ConductedLesson, PayRate, BotSchedule, Attendance
    
    # Перевіряємо чи існує вчитель
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Збираємо детальну інформацію про залежності
    
    # 1. Schedules (поточні розклади)
    schedules_count = await db.execute(
        select(func.count(Schedule.id)).where(Schedule.teacher_id == teacher_id)
    )
    schedules_count = schedules_count.scalar() or 0
    
    # 2. Lesson Events (плановані уроки) 
    lesson_events_count = await db.execute(
        select(func.count(LessonEvent.id)).where(LessonEvent.teacher_id == teacher_id)
    )
    lesson_events_count = lesson_events_count.scalar() or 0
    
    # 3. Lesson Events з attendance (проведені уроки з відвідуваністю)
    lesson_events_with_attendance = await db.execute(
        select(func.count(func.distinct(LessonEvent.id)))
        .select_from(LessonEvent)
        .join(Attendance, Attendance.lesson_event_id == LessonEvent.id)
        .where(LessonEvent.teacher_id == teacher_id)
    )
    lesson_events_with_attendance_count = lesson_events_with_attendance.scalar() or 0
    
    # 4. Attendance records (записи відвідуваності)
    attendance_count = await db.execute(
        select(func.count(Attendance.id))
        .select_from(Attendance)
        .join(LessonEvent, Attendance.lesson_event_id == LessonEvent.id)
        .where(LessonEvent.teacher_id == teacher_id)
    )
    attendance_count = attendance_count.scalar() or 0
    
    # 5. Conducted Lessons (проведені уроки)
    conducted_lessons_count = await db.execute(
        select(func.count(ConductedLesson.id)).where(ConductedLesson.teacher_id == teacher_id)
    )
    conducted_lessons_count = conducted_lessons_count.scalar() or 0
    
    # 6. Payroll (зарплатні нарахування)
    payroll_count = await db.execute(
        select(func.count(Payroll.id)).where(Payroll.teacher_id == teacher_id)
    )
    payroll_count = payroll_count.scalar() or 0
    
    # 7. Pay Rates (ставки оплати)
    pay_rates_count = await db.execute(
        select(func.count(PayRate.id)).where(PayRate.teacher_id == teacher_id)
    )
    pay_rates_count = pay_rates_count.scalar() or 0
    
    # Визначаємо чи можна безпечно видалити
    has_historical_data = (
        lesson_events_with_attendance_count > 0 or 
        attendance_count > 0 or 
        conducted_lessons_count > 0 or 
        payroll_count > 0
    )
    
    can_delete_safely = not has_historical_data and pay_rates_count == 0 and schedules_count == 0
    
    return {
        "teacher_id": teacher_id,
        "teacher_name": teacher.full_name,
        "can_delete_safely": can_delete_safely,
        "has_historical_data": has_historical_data,
        "dependencies": {
            "schedules": schedules_count,
            "lesson_events": lesson_events_count,
            "lesson_events_with_attendance": lesson_events_with_attendance_count,
            "attendance_records": attendance_count,
            "conducted_lessons": conducted_lessons_count,
            "payroll_records": payroll_count,
            "pay_rates": pay_rates_count
        },
        "deletion_plan": {
            "will_be_deleted": [
                {"item": "PayRates", "count": pay_rates_count, "reason": "Налаштування ставок"} if pay_rates_count > 0 else None,
                {"item": "Schedules", "count": schedules_count, "reason": "Поточні розклади"} if schedules_count > 0 else None,
                {"item": "LessonEvents без attendance", "count": lesson_events_count - lesson_events_with_attendance_count, "reason": "Майбутні незаплановані уроки"} if (lesson_events_count - lesson_events_with_attendance_count) > 0 else None,
                {"item": "BotSchedules", "count": "автоматично", "reason": "Автоматичні нагадування"}
            ],
            "will_be_preserved": [
                {"item": "Conducted Lessons", "count": conducted_lessons_count, "reason": "Для звітності про проведені заняття"} if conducted_lessons_count > 0 else None,
                {"item": "Payroll", "count": payroll_count, "reason": "Для бухгалтерії та податкової"} if payroll_count > 0 else None,
                {"item": "Attendance", "count": attendance_count, "reason": "Для історії відвідуваності"} if attendance_count > 0 else None,
                {"item": "LessonEvents з attendance", "count": lesson_events_with_attendance_count, "reason": "Проведені уроки з відвідуваністю"} if lesson_events_with_attendance_count > 0 else None
            ]
        }
    }


# === CLUBS ===
class ClubCreate(BaseModel):
    name: str
    duration_min: int = 60
    location: str


class ClubUpdate(BaseModel):
    name: Optional[str] = None
    duration_min: Optional[int] = None
    location: Optional[str] = None


class ClubResponse(BaseModel):
    id: int
    name: str
    duration_min: int
    location: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/clubs", response_model=List[ClubResponse])
async def get_clubs(db: DbSession) -> List[Club]:
    """Get all clubs."""
    result = await db.execute(select(Club).order_by(Club.name))
    return result.scalars().all()


@router.get("/clubs/{club_id}", response_model=ClubResponse)
async def get_club(club_id: int, db: DbSession) -> Club:
    """Get club by ID."""
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club


@router.post("/clubs", response_model=ClubResponse, status_code=201)
async def create_club(club_data: ClubCreate, db: DbSession) -> Club:
    """Create new club."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Creating club with data: {club_data.model_dump()}")
        club = Club(**club_data.model_dump())
        db.add(club)
        await db.flush()  # Отримуємо ID
        
        # 📝 AUDIT LOG: Створення гуртка (ПЕРЕД commit!)
        try:
            from app.services.audit_service import log_audit
            await log_audit(
                db=db,
                action_type="CREATE",
                entity_type="club",
                entity_id=club.id,
                entity_name=club.name,
                description=f"Створено новий гурток: {club.name}, тривалість {club.duration_min} хв, локація: {club.location}",
                user_name="Адміністратор",
                changes={"after": {"name": club.name, "duration_min": club.duration_min, "location": club.location}}
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (club CREATE in public.py): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        await db.refresh(club)
        logger.info(f"Club created successfully: {club.id}")
        return club
    except Exception as e:
        logger.error(f"Error creating club: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating club: {str(e)}")


@router.put("/clubs/{club_id}", response_model=ClubResponse)
async def update_club(club_id: int, club_data: ClubUpdate, db: DbSession) -> Club:
    """Update club."""
    import logging
    logger = logging.getLogger(__name__)
    
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    update_data = club_data.model_dump(exclude_unset=True)
    for field in update_data.keys():
        old_values[field] = getattr(club, field, None)
    
    # Оновлення полів
    for field, value in update_data.items():
        if hasattr(club, field):
            setattr(club, field, value)
    
    # 📝 AUDIT LOG: Оновлення гуртка (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {v}" for k, v in update_data.items() if old_values.get(k) != v])
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="club",
            entity_id=club.id,
            entity_name=club.name,
            description=f"Оновлено дані гуртка: {club.name}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": update_data}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (club UPDATE in public.py): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(club)
    return club


@router.get("/clubs/{club_id}/dependencies")
async def get_club_dependencies(club_id: int, db: DbSession, include_students: bool = False) -> dict:
    """Get club dependencies before deletion."""
    # Перевіряємо чи існує гурток
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    # Рахуємо кількість прив'язаних учнів
    enrolled_students_result = await db.execute(
        select(func.count(Enrollment.id))
        .where(Enrollment.club_id == club_id)
    )
    enrolled_students_count = enrolled_students_result.scalar()
    
    # Отримуємо список учнів якщо потрібно
    students_list = []
    if include_students and enrolled_students_count > 0:
        students_result = await db.execute(
            select(Student)
            .join(Enrollment, Student.id == Enrollment.student_id)
            .where(Enrollment.club_id == club_id)
            .order_by(Student.first_name, Student.last_name)
        )
        students = students_result.scalars().all()
        students_list = [
            {
                "id": student.id,
                "full_name": f"{student.first_name} {student.last_name}",
                "grade": student.grade,
                "age": student.age
            }
            for student in students
        ]
    
    # Рахуємо кількість розкладів
    schedules_result = await db.execute(
        select(func.count(Schedule.id))
        .where(Schedule.club_id == club_id)
    )
    schedules_count = schedules_result.scalar()
    
    # Отримуємо назви розкладів якщо потрібно
    schedules_list = []
    if include_students and schedules_count > 0:
        schedules_names_result = await db.execute(
            select(Schedule.id, Schedule.weekday, Schedule.start_time)
            .where(Schedule.club_id == club_id)
            .order_by(Schedule.weekday, Schedule.start_time)
        )
        schedules_data = schedules_names_result.fetchall()
        
        weekdays = {
            1: "Понеділок", 2: "Вівторок", 3: "Середа", 4: "Четвер", 
            5: "П'ятниця", 6: "Субота", 7: "Неділя"
        }
        
        schedules_list = [
            {
                "id": schedule.id,
                "display": f"{weekdays.get(schedule.weekday, 'Невідомо')} {schedule.start_time.strftime('%H:%M')}"
            }
            for schedule in schedules_data
        ]
    
    # Рахуємо кількість проведених уроків
    conducted_lessons_result = await db.execute(
        select(func.count(ConductedLesson.id))
        .where(ConductedLesson.club_id == club_id)
    )
    conducted_lessons_count = conducted_lessons_result.scalar()
    
    # Рахуємо кількість attendance записів
    attendance_result = await db.execute(
        select(func.count(Attendance.id))
        .join(LessonEvent, Attendance.lesson_event_id == LessonEvent.id)
        .where(LessonEvent.club_id == club_id)
    )
    attendance_count = attendance_result.scalar()
    
    response = {
        "club_id": club_id,
        "club_name": club.name,
        "can_delete_safely": enrolled_students_count == 0 and schedules_count == 0,
        "dependencies": {
            "enrolled_students": enrolled_students_count,
            "schedules": schedules_count,
            "conducted_lessons": conducted_lessons_count,
            "attendance_records": attendance_count
        },
        "impact_summary": {
            "students_will_be_unenrolled": enrolled_students_count,
            "schedules_will_be_deleted": schedules_count,
            "lesson_history_will_remain": conducted_lessons_count > 0,
            "attendance_history_will_remain": attendance_count > 0
        }
    }
    
    # Додаємо детальну інформацію якщо потрібно
    if include_students:
        response["details"] = {
            "students": students_list,
            "schedules": schedules_list
        }
    
    return response


@router.delete("/clubs/{club_id}", status_code=204)
async def delete_club(club_id: int, db: DbSession, force: bool = False) -> None:
    """Delete club with optional cascade deletion."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Перевіряємо чи існує гурток
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    # Зберігаємо ім'я для аудиту
    club_name = club.name
    
    # Перевіряємо залежності
    enrolled_students_result = await db.execute(
        select(func.count(Enrollment.id))
        .where(Enrollment.club_id == club_id)
    )
    enrolled_students_count = enrolled_students_result.scalar()
    
    schedules_result = await db.execute(
        select(func.count(Schedule.id))
        .where(Schedule.club_id == club_id)
    )
    schedules_count = schedules_result.scalar()
    
    # Якщо є залежності і не форсуємо видалення
    if (enrolled_students_count > 0 or schedules_count > 0) and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete club. It has {enrolled_students_count} enrolled students and {schedules_count} schedules. Use force=true to cascade delete."
        )
    
    # КАСКАДНЕ ВИДАЛЕННЯ
    if force:
        logger.info(f"🗑️ Cascade deleting club {club.name} (ID: {club_id})")
        protected_schedule_ids = set()  # Ініціалізуємо для подальшого використання
        
        # 1. Видаляємо всі записи учнів на розклади цього гуртка
        schedule_enrollments_result = await db.execute(
            select(ScheduleEnrollment.id)
            .join(Schedule, Schedule.id == ScheduleEnrollment.schedule_id)
            .where(Schedule.club_id == club_id)
        )
        schedule_enrollment_ids = [row[0] for row in schedule_enrollments_result.fetchall()]
        
        if schedule_enrollment_ids:
            await db.execute(
                delete(ScheduleEnrollment)
                .where(ScheduleEnrollment.id.in_(schedule_enrollment_ids))
            )
            logger.info(f"🗑️ Deleted {len(schedule_enrollment_ids)} schedule enrollments")
        
        # 2. Видаляємо всі записи учнів на гурток загалом
        await db.execute(delete(Enrollment).where(Enrollment.club_id == club_id))
        logger.info(f"🗑️ Deleted {enrolled_students_count} general enrollments")
        
        # 3. Видаляємо всі lesson_events пов'язані з розкладами цього гуртка
        lesson_events_result = await db.execute(
            select(LessonEvent.id)
            .join(Schedule, Schedule.id == LessonEvent.schedule_id)
            .where(Schedule.club_id == club_id)
        )
        lesson_event_ids = [row[0] for row in lesson_events_result.fetchall()]
        
        if lesson_event_ids:
            # 💰📚 ПЕРЕВІРЯЄМО ЧИ Є HISTORICAL DATA НА lesson_events
            from app.models import Payroll, Attendance, ConductedLesson
            
            # Знаходимо lesson_events які мають historical data (payroll/attendance/conducted)
            events_with_payroll = await db.execute(
                select(Payroll.lesson_event_id).where(Payroll.lesson_event_id.in_(lesson_event_ids))
            )
            payroll_event_ids = {row[0] for row in events_with_payroll.fetchall()}
            
            events_with_attendance = await db.execute(
                select(Attendance.lesson_event_id).where(Attendance.lesson_event_id.in_(lesson_event_ids))
            )
            attendance_event_ids = {row[0] for row in events_with_attendance.fetchall()}
            
            events_with_conducted = await db.execute(
                select(ConductedLesson.lesson_event_id).where(ConductedLesson.lesson_event_id.in_(lesson_event_ids))
            )
            conducted_event_ids = {row[0] for row in events_with_conducted.fetchall()}
            
            # События з historical data зберігаємо, решту видаляємо
            protected_event_ids = payroll_event_ids | attendance_event_ids | conducted_event_ids
            deletable_event_ids = [eid for eid in lesson_event_ids if eid not in protected_event_ids]
            
            if deletable_event_ids:
                await db.execute(
                    delete(LessonEvent).where(LessonEvent.id.in_(deletable_event_ids))
                )
                logger.info(f"🗑️ Deleted {len(deletable_event_ids)} lesson events (no historical data)")
            
            if protected_event_ids:
                # Обнуляємо club_id в protected lesson_events (зберігаємо історію)
                await db.execute(
                    update(LessonEvent)
                    .where(LessonEvent.id.in_(list(protected_event_ids)))
                    .values(club_id=None)
                )
                logger.info(f"📚 Updated {len(protected_event_ids)} protected lesson_events: club_id set to NULL (history preserved)")
                
                # Знаходимо schedule_ids які мають historical lesson_events
                protected_schedules_result = await db.execute(
                    select(LessonEvent.schedule_id)
                    .where(LessonEvent.id.in_(list(protected_event_ids)))
                    .distinct()
                )
                protected_schedule_ids = {row[0] for row in protected_schedules_result.fetchall()}
                logger.info(f"📋 Found {len(protected_schedule_ids)} schedules with historical data - will deactivate instead of delete")
            
            # ПРИМІТКА: Payroll, Attendance та ConductedLesson записи ЗБЕРІГАЮТЬСЯ
        
        # 4. Видаляємо всі bot_schedules пов'язані з розкладами цього гуртка
        from app.models.bot_schedule import BotSchedule
        bot_schedules_result = await db.execute(
            select(BotSchedule.id)
            .join(Schedule, Schedule.id == BotSchedule.schedule_id)
            .where(Schedule.club_id == club_id)
        )
        bot_schedule_ids = [row[0] for row in bot_schedules_result.fetchall()]
        
        if bot_schedule_ids:
            await db.execute(
                delete(BotSchedule)
                .where(BotSchedule.id.in_(bot_schedule_ids))
            )
            logger.info(f"🗑️ Deleted {len(bot_schedule_ids)} bot schedules")
        
        # 4.5. ОБРОБЛЯЄМО CONDUCTED LESSONS: зберігаємо історію, але очищаємо club_id
        from app.models import ConductedLesson
        conducted_lessons_result = await db.execute(
            select(func.count(ConductedLesson.id))
            .where(ConductedLesson.club_id == club_id)
        )
        conducted_lessons_count = conducted_lessons_result.scalar() or 0
        
        if conducted_lessons_count > 0:
            # Обнуляємо club_id в conducted_lessons (зберігаємо історію, але видаляємо зв'язок)
            await db.execute(
                update(ConductedLesson)
                .where(ConductedLesson.club_id == club_id)
                .values(club_id=None)
            )
            logger.info(f"📚 Updated {conducted_lessons_count} conducted_lessons: club_id set to NULL (history preserved)")
        
        # 5. ВИДАЛЯЄМО schedules БЕЗ historical data, деактивуємо решту
        if 'protected_schedule_ids' in locals() and protected_schedule_ids:
            # Деактивуємо schedules з historical data і обнуляємо club_id
            await db.execute(
                update(Schedule)
                .where(Schedule.id.in_(list(protected_schedule_ids)))
                .values(active=False, club_id=None)
            )
            
            # Видаляємо тільки schedules БЕЗ historical data
            await db.execute(
                delete(Schedule)
                .where(Schedule.club_id == club_id)
                .where(~Schedule.id.in_(list(protected_schedule_ids)))
            )
            logger.info(f"📋 Deactivated {len(protected_schedule_ids)} schedules with historical data")
            logger.info(f"🗑️ Deleted {schedules_count - len(protected_schedule_ids)} schedules without historical data")
        else:
            # Немає historical data - видаляємо всі schedules
            await db.execute(
                delete(Schedule).where(Schedule.club_id == club_id)
            )
            logger.info(f"🗑️ Deleted all {schedules_count} schedules (no historical data found)")
        
        # ПРИМІТКА: Зберігаємо звітні дані (payroll, attendance, conducted lessons)
        # Видаляємо тільки активні зв'язки (enrollments, schedules, bot_schedules)
        
    # 6. Рішення щодо самого гуртка
    # ЗАВЖДИ видаляємо гурток повністю з БД
    # Історичні дані зберігаються в lesson_events, attendance, payroll, conducted_lessons
    await db.execute(delete(Club).where(Club.id == club_id))
    
    if 'protected_schedule_ids' in locals() and protected_schedule_ids:
        logger.info(f"🗑️ Club completely deleted (historical data preserved in {len(protected_schedule_ids)} lesson_events)")
    else:
        logger.info(f"🗑️ Club completely deleted (no historical data)")
    
    # 📝 AUDIT LOG: Видалення гуртка (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        has_historical = 'protected_schedule_ids' in locals() and len(protected_schedule_ids) > 0
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="club",
            entity_id=club_id,
            entity_name=club_name,
            description=f"Видалено гурток: {club_name} (force={force}). Відписано {enrolled_students_count} учнів, видалено/деактивовано {schedules_count} розкладів. Історичні дані збережено: {'так' if has_historical else 'ні'}.",
            user_name="Адміністратор",
            changes={
                "action": "deleted",
                "force": force,
                "deleted": {
                    "enrollments": enrolled_students_count,
                    "schedules": schedules_count
                },
                "historical_data_preserved": has_historical
            }
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (club DELETE in public.py): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    
    logger.info(f"✅ Successfully deleted club {club.name} (ID: {club_id})")


# === SCHEDULES ===
class ScheduleCreate(BaseModel):
    club_id: int
    weekday: int  # 1=Monday, 2=Tuesday, ..., 5=Friday  
    start_time: time
    teacher_id: int
    group_name: Optional[str] = "Група 1"
    active: bool = True


class ScheduleUpdate(BaseModel):
    club_id: Optional[int] = None
    weekday: Optional[int] = None
    start_time: Optional[time] = None
    teacher_id: Optional[int] = None
    group_name: Optional[str] = None
    active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    id: int
    club_id: int
    weekday: int
    start_time: time
    teacher_id: int
    group_name: Optional[str] = None
    active: bool
    created_at: datetime
    # Вкладені об'єкти
    club: Optional[ClubResponse] = None
    teacher: Optional[TeacherResponse] = None

    class Config:
        from_attributes = True


@router.get("/schedules", response_model=List[ScheduleResponse])
async def get_schedules(
    db: DbSession,
    include_inactive: bool = Query(False, description="Include deactivated schedules")
) -> List[Schedule]:
    """Get all schedules."""
    query = select(Schedule).options(
        selectinload(Schedule.club),
        selectinload(Schedule.teacher),
    )
    
    # ⚠️ Завжди фільтруємо schedules з club_id=NULL (історичні після видалення гуртка)
    query = query.where(Schedule.club_id.isnot(None))
    
    # 🔍 Фільтр активних розкладів за замовчуванням
    if not include_inactive:
        query = query.where(Schedule.active == True)
    
    result = await db.execute(
        query.order_by(Schedule.weekday, Schedule.start_time)
    )
    return result.scalars().all()


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int, db: DbSession) -> Schedule:
    """Get schedule by ID."""
    result = await db.execute(
        select(Schedule)
        .options(
            selectinload(Schedule.club),
            selectinload(Schedule.teacher),
        )
        .where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(schedule_data: ScheduleCreate, db: DbSession) -> Schedule:
    """Create new schedule."""
    # Перевірка існування club та teacher
    club_result = await db.execute(select(Club).where(Club.id == schedule_data.club_id))
    if not club_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Club not found")
    
    teacher_result = await db.execute(select(Teacher).where(Teacher.id == schedule_data.teacher_id))
    if not teacher_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    schedule = Schedule(**schedule_data.model_dump())
    db.add(schedule)
    await db.flush()  # Отримуємо ID
    
    # Завантажуємо зв'язані об'єкти для аудиту
    await db.refresh(schedule, ['club', 'teacher'])
    
    # 📝 AUDIT LOG: Створення розкладу (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        import logging
        logger = logging.getLogger(__name__)
        
        weekdays = {1: "Понеділок", 2: "Вівторок", 3: "Середа", 4: "Четвер", 5: "П'ятниця", 6: "Субота", 7: "Неділя"}
        weekday_name = weekdays.get(schedule.weekday, f"День {schedule.weekday}")
        
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="schedule",
            entity_id=schedule.id,
            entity_name=f"{schedule.club.name} - {weekday_name} {schedule.start_time.strftime('%H:%M')}",
            description=f"Створено новий розклад: гурток '{schedule.club.name}', викладач '{schedule.teacher.full_name}', {weekday_name} о {schedule.start_time.strftime('%H:%M')}, група '{schedule.group_name or 'Група 1'}'",
            user_name="Адміністратор",
            changes={"after": {
                "club": schedule.club.name,
                "teacher": schedule.teacher.full_name,
                "weekday": weekday_name,
                "start_time": schedule.start_time.strftime('%H:%M'),
                "group_name": schedule.group_name
            }}
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ AUDIT LOG ERROR (schedule CREATE in public.py): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(schedule)
    
    # 🤖 АВТОМАТИЧНО створюємо bot_schedule з нагадуванням через 5 хвилин після початку
    from app.models import BotSchedule
    
    # Обчислюємо час нагадування: start_time + 5 хвилин
    schedule_start = datetime.combine(datetime.today(), schedule.start_time)
    notification_time = schedule_start + timedelta(minutes=5)
    
    bot_schedule = BotSchedule(
        schedule_id=schedule.id,
        enabled=True,
        offset_minutes=5,  # 5 хвилин після початку уроку
        custom_time=notification_time.time(),  # Точний час для lesson_event_manager
        custom_message="Нагадування про відмітку присутності"
    )
    db.add(bot_schedule)
    
    # Створюємо lesson events для bot_schedule
    try:
        from app.services.lesson_event_manager import LessonEventManager
        manager = LessonEventManager(db)
        await db.commit()  # Спочатку commit bot_schedule
        await db.refresh(bot_schedule)
        await manager.ensure_bot_schedule_has_events(bot_schedule.id)
        logger.info(f"Auto-created bot_schedule {bot_schedule.id} for schedule {schedule.id}")
    except Exception as e:
        logger.warning(f"Could not auto-create lesson events for schedule {schedule.id}: {e}")
    
    await db.commit()
    # Завантажуємо зв'язані об'єкти
    await db.refresh(schedule, ['club', 'teacher'])
    return schedule


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, schedule_data: ScheduleUpdate, db: DbSession) -> Schedule:
    """Update schedule."""
    import logging
    logger = logging.getLogger(__name__)
    
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Завантажуємо зв'язані об'єкти для аудиту
    await db.refresh(schedule, ['club', 'teacher'])
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    update_data = schedule_data.model_dump(exclude_unset=True)
    for field in update_data.keys():
        old_values[field] = getattr(schedule, field, None)
    
    # Оновлення полів
    update_data = schedule_data.model_dump(exclude_unset=True)
    
    # 🔄 КАСКАДНЕ ОНОВЛЕННЯ: Якщо змінюється вчитель - оновити майбутні lesson_events
    if 'teacher_id' in update_data and update_data['teacher_id'] != schedule.teacher_id:
        from app.models import LessonEvent, Teacher, LessonEventStatus
        from sqlalchemy import update
        from datetime import date
        import logging
        
        logger = logging.getLogger(__name__)
        old_teacher_id = schedule.teacher_id
        new_teacher_id = update_data['teacher_id']
        
        logger.info(f"🎯 TEACHER CHANGE DETECTED: schedule {schedule_id}, {old_teacher_id} → {new_teacher_id}")
        
        # Перевіряємо чи існує новий вчитель
        new_teacher_result = await db.execute(
            select(Teacher).where(Teacher.id == new_teacher_id)
        )
        new_teacher = new_teacher_result.scalar_one_or_none()
        
        if not new_teacher:
            raise HTTPException(
                status_code=404,
                detail="New teacher not found"
            )
        
        logger.info(f"🔍 New teacher found: {new_teacher.full_name} (chat_id: {new_teacher.tg_chat_id})")
        
        # Оновлюємо ТІЛЬКИ майбутні lesson_events (зберігаємо історичні)
        future_events_result = await db.execute(
            update(LessonEvent)
            .where(
                LessonEvent.schedule_id == schedule_id,
                LessonEvent.date >= date.today(),
                LessonEvent.status == LessonEventStatus.PLANNED
            )
            .values(
                teacher_id=new_teacher_id,
                teacher_chat_id=new_teacher.tg_chat_id
            )
            .returning(LessonEvent.id)
        )
        
        updated_events = future_events_result.fetchall()
        updated_count = len(updated_events)
        
        logger.info(f"🔄 CASCADE UPDATE: Schedule {schedule_id} teacher changed from {old_teacher_id} to {new_teacher_id}")
        logger.info(f"📅 Updated {updated_count} future lesson_events to new teacher: {new_teacher.full_name}")
        logger.info(f"🎯 Updated event IDs: {[event.id for event in updated_events]}")
    
    for field, value in update_data.items():
        if hasattr(schedule, field):
            setattr(schedule, field, value)
    
    # Перезавантажуємо для оновлених зв'язків
    await db.refresh(schedule, ['club', 'teacher'])
    
    # 📝 AUDIT LOG: Оновлення розкладу (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        from datetime import time
        
        weekdays = {1: "Понеділок", 2: "Вівторок", 3: "Середа", 4: "Четвер", 5: "П'ятниця", 6: "Субота", 7: "Неділя"}
        
        # Форматуємо зміни для зручного читання
        changes_desc_parts = []
        for k, v in update_data.items():
            old_val = old_values.get(k)
            if old_val != v:
                if k == 'weekday':
                    old_val_str = weekdays.get(old_val, str(old_val))
                    new_val_str = weekdays.get(v, str(v))
                    changes_desc_parts.append(f"день: {old_val_str} → {new_val_str}")
                elif k == 'start_time':
                    old_val_str = old_val.strftime('%H:%M') if isinstance(old_val, time) else str(old_val)
                    new_val_str = v.strftime('%H:%M') if isinstance(v, time) else str(v)
                    changes_desc_parts.append(f"час: {old_val_str} → {new_val_str}")
                elif k == 'active':
                    changes_desc_parts.append(f"статус: {'активний' if old_val else 'неактивний'} → {'активний' if v else 'неактивний'}")
                else:
                    changes_desc_parts.append(f"{k}: {old_val} → {v}")
        
        changes_desc = ", ".join(changes_desc_parts) if changes_desc_parts else "без змін"
        
        weekday_name = weekdays.get(schedule.weekday, f"День {schedule.weekday}")
        
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="schedule",
            entity_id=schedule.id,
            entity_name=f"{schedule.club.name} - {weekday_name} {schedule.start_time.strftime('%H:%M')}",
            description=f"Оновлено розклад: гурток '{schedule.club.name}', викладач '{schedule.teacher.full_name}'. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": update_data}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (schedule UPDATE in public.py): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(schedule, ['club', 'teacher'])
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: int, db: DbSession) -> None:
    """Delete schedule with proper cascade handling."""
    from app.models import BotSchedule, LessonEvent, ScheduleEnrollment
    
    # Перевіряємо чи існує розклад
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        from app.models import Attendance, Payroll, ConductedLesson
        
        # Перевіряємо чи є історичні дані (attendance, payroll, conducted_lessons)
        historical_data_query = await db.execute(
            select(LessonEvent.id)
            .where(LessonEvent.schedule_id == schedule_id)
            .where(
                LessonEvent.id.in_(select(Attendance.lesson_event_id)) |
                LessonEvent.id.in_(select(Payroll.lesson_event_id)) |
                LessonEvent.id.in_(select(ConductedLesson.lesson_event_id))
            )
            .limit(1)
        )
        has_historical_data = historical_data_query.scalar_one_or_none() is not None
        
        if has_historical_data:
            # Якщо є історичні дані - тільки деактивуємо розклад
            schedule.active = False
            await db.commit()
            logger.info(f"Schedule {schedule_id} deactivated due to historical data")
        else:
            # Якщо немає історичних даних - повністю видаляємо
            
            # 1. Видаляємо schedule enrollments
            await db.execute(
                delete(ScheduleEnrollment).where(ScheduleEnrollment.schedule_id == schedule_id)
            )
            
            # 2. Видаляємо lesson events (без історичних даних)
            await db.execute(
                delete(LessonEvent).where(LessonEvent.schedule_id == schedule_id)
            )
            
            # 3. Видаляємо bot schedule
            await db.execute(
                delete(BotSchedule).where(BotSchedule.schedule_id == schedule_id)
            )
            
            # 4. Видаляємо сам розклад
            await db.execute(delete(Schedule).where(Schedule.id == schedule_id))
            
            await db.commit()
            logger.info(f"Schedule {schedule_id} completely deleted")
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting schedule: {str(e)}"
        )


# === LESSON EVENTS ===
class LessonEventResponse(BaseModel):
    id: int
    schedule_id: int
    date: datetime
    club_id: Optional[int]  # Nullable після видалення гуртка
    teacher_id: int
    status: str
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    # Вкладені об'єкти
    club: Optional[ClubResponse] = None
    teacher: Optional[TeacherResponse] = None
    display_name: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/lesson-events", response_model=List[LessonEventResponse])
async def get_lesson_events(db: DbSession) -> List[LessonEvent]:
    """Get all lesson events."""
    result = await db.execute(
        select(LessonEvent)
        .options(
            selectinload(LessonEvent.club),
            selectinload(LessonEvent.teacher),
        )
        .where(LessonEvent.club_id.isnot(None))  # ⚠️ Фільтруємо історичні після видалення гуртка
        .order_by(LessonEvent.date.desc(), LessonEvent.created_at.desc())
    )
    events = result.scalars().all()
    
    # Додати display_name для зручності
    for event in events:
        if event.club and event.teacher:
            event.display_name = f"{event.club.name} - {event.teacher.full_name} ({event.date})"
    
    return events


@router.get("/lesson-events/{event_id}", response_model=LessonEventResponse)
async def get_lesson_event(event_id: int, db: DbSession) -> LessonEvent:
    """Get lesson event by ID."""
    result = await db.execute(
        select(LessonEvent)
        .options(
            selectinload(LessonEvent.club),
            selectinload(LessonEvent.teacher),
        )
        .where(LessonEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Lesson event not found")
    return event


# === ATTENDANCE ===
class AttendanceCreate(BaseModel):
    lesson_event_id: int
    student_id: int
    status: str  # "PRESENT" or "ABSENT" (case insensitive)
    marked_by: Optional[int] = 1
    update_if_exists: bool = False  # Якщо True - оновлює існуючий запис замість помилки


class AttendanceUpdate(BaseModel):
    status: Optional[str] = None
    marked_by: Optional[int] = None


class AttendanceResponse(BaseModel):
    id: int
    lesson_event_id: int
    student_id: int
    status: str
    marked_by: Optional[int]
    marked_at: datetime
    # Вкладені об'єкти
    student: Optional[StudentResponse] = None
    lesson_event: Optional[LessonEventResponse] = None

    class Config:
        from_attributes = True


@router.get("/attendance", response_model=List[AttendanceResponse])
async def get_attendance(
    db: DbSession,
    lesson_event_id: Optional[int] = None,
    date_from: Optional[date] = Query(None, description="Дата початку (фільтр за lesson_event.date)"),
    date_to: Optional[date] = Query(None, description="Дата кінця (фільтр за lesson_event.date)"),
    limit: Optional[int] = None
) -> List[Attendance]:
    """Get attendance records with optional filters."""
    query = select(Attendance).options(
        selectinload(Attendance.student),
        selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
        selectinload(Attendance.lesson_event).selectinload(LessonEvent.teacher),
    )
    
    if lesson_event_id:
        query = query.where(Attendance.lesson_event_id == lesson_event_id)
    
    # Фільтр за датами через підзапит
    if date_from or date_to:
        # Створюємо підзапит для фільтрації lesson_event_id
        event_query = select(LessonEvent.id)
        if date_from:
            event_query = event_query.where(LessonEvent.date >= date_from)
        if date_to:
            event_query = event_query.where(LessonEvent.date <= date_to)
        
        query = query.where(Attendance.lesson_event_id.in_(event_query))
    
    query = query.order_by(Attendance.marked_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/attendance/{attendance_id}", response_model=AttendanceResponse)
async def get_attendance_record(attendance_id: int, db: DbSession) -> Attendance:
    """Get attendance record by ID."""
    result = await db.execute(
        select(Attendance)
        .options(
            selectinload(Attendance.student),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.teacher),
        )
        .where(Attendance.id == attendance_id)
    )
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return attendance


@router.post("/attendance", response_model=AttendanceResponse, status_code=201)
async def create_attendance(attendance_data: AttendanceCreate, db: DbSession) -> Attendance:
    """Create new attendance record."""
    # Перевірка існування lesson_event та student
    lesson_event_result = await db.execute(select(LessonEvent).where(LessonEvent.id == attendance_data.lesson_event_id))
    if not lesson_event_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lesson event not found")
    
    student_result = await db.execute(select(Student).where(Student.id == attendance_data.student_id))
    if not student_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Перевірка валідного статусу
    if attendance_data.status.upper() not in ["PRESENT", "ABSENT"]:
        raise HTTPException(status_code=400, detail="Status must be 'PRESENT' or 'ABSENT'")
    
    # Перевірка на дублікат
    existing_result = await db.execute(
        select(Attendance)
        .options(selectinload(Attendance.student))
        .where(
            Attendance.lesson_event_id == attendance_data.lesson_event_id,
            Attendance.student_id == attendance_data.student_id
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        if attendance_data.update_if_exists:
            # Оновлюємо існуючий запис
            existing.status = AttendanceStatus(attendance_data.status.upper())
            if attendance_data.marked_by:
                existing.marked_by = attendance_data.marked_by
            existing.marked_at = datetime.now()
            
            await db.commit()
            
            # Завантажуємо оновлений запис з усіма зв'язками
            result = await db.execute(
                select(Attendance)
                .options(
                    selectinload(Attendance.student),
                    selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
                    selectinload(Attendance.lesson_event).selectinload(LessonEvent.teacher)
                )
                .where(Attendance.id == existing.id)
            )
            existing = result.scalar_one()
            
            # Автоматично пересчитуємо conducted lesson
            try:
                from app.services.conducted_lesson_service import ConductedLessonService
                conducted_lesson_service = ConductedLessonService(db)
                await conducted_lesson_service.recalculate_from_attendance(existing.lesson_event_id)
            except Exception as e:
                logger.warning(f"Failed to recalculate ConductedLesson: {e}")
            
            return existing
        else:
            # Повідомляємо про існуючий запис з деталями
            student_name = f"{existing.student.first_name} {existing.student.last_name}" if existing.student else "студент"
            raise HTTPException(
                status_code=400, 
                detail=f"Запис відвідуваності для {student_name} на цьому уроці вже існує (ID: {existing.id}, статус: {existing.status.value}). Використайте редагування або встановіть update_if_exists=true."
            )
    
    # Створюємо новий запис
    attendance = Attendance(
        lesson_event_id=attendance_data.lesson_event_id,
        student_id=attendance_data.student_id,
        status=AttendanceStatus(attendance_data.status.upper()),
        marked_by=attendance_data.marked_by
    )
    
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)
    
    # Завантажуємо зв'язані об'єкти
    result = await db.execute(
        select(Attendance)
        .options(
            selectinload(Attendance.student),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.teacher)
        )
        .where(Attendance.id == attendance.id)
    )
    return result.scalar_one()


@router.put("/attendance/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(attendance_id: int, attendance_data: AttendanceUpdate, db: DbSession) -> Attendance:
    """Update attendance record."""
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Зберігаємо старий статус для аудиту
    old_status = attendance.status.value if attendance.status else None
    
    # Оновлення полів
    update_data = attendance_data.model_dump(exclude_unset=True)
    
    if "status" in update_data:
        status_value = update_data["status"]
        if status_value not in ["present", "absent"]:
            raise HTTPException(status_code=400, detail="Status must be 'present' or 'absent'")
        attendance.status = AttendanceStatus.PRESENT if status_value == "present" else AttendanceStatus.ABSENT
    
    if "marked_by" in update_data:
        attendance.marked_by = update_data["marked_by"]
    
    await db.commit()
    
    # 📝 AUDIT LOG: Оновлення відвідуваності
    try:
        from app.services.audit_service import log_audit
        # Завантажуємо student для відображення
        student_result = await db.execute(select(Student).where(Student.id == attendance.student_id))
        student = student_result.scalar_one_or_none()
        student_name = f"{student.first_name} {student.last_name}" if student else "(учень видалений)"
        new_status = attendance.status.value if attendance.status else None
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="attendance",
            entity_id=attendance.id,
            entity_name=f"{student_name} - {new_status}",
            description=f"Змінено відвідуваність: {student_name}, {old_status} → {new_status}",
            user_name=attendance_data.marked_by or "Адміністратор",
            changes={"before": {"status": old_status}, "after": {"status": new_status}}
        )
    except Exception as e:
        pass
    
    # 🔄 АВТОМАТИЧНО ПЕРЕСЧИТУЄМО CONDUCTED_LESSON
    try:
        from app.services.conducted_lesson_service import ConductedLessonService
        conducted_lesson_service = ConductedLessonService(db)
        await conducted_lesson_service.recalculate_from_attendance(attendance.lesson_event_id)
    except Exception as e:
        # Не блокуємо основну операцію якщо пересчитування не спрацювало
        print(f"Warning: Failed to recalculate ConductedLesson: {e}")
    
    # Перезавантажуємо запис з усіма зв'язками
    result = await db.execute(
        select(Attendance)
        .options(
            selectinload(Attendance.student),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.teacher)
        )
        .where(Attendance.id == attendance_id)
    )
    return result.scalar_one()


@router.delete("/attendance/{attendance_id}", status_code=204)
async def delete_attendance(attendance_id: int, db: DbSession) -> None:
    """Delete attendance record."""
    result = await db.execute(
        select(Attendance)
        .options(selectinload(Attendance.student), selectinload(Attendance.lesson_event))
        .where(Attendance.id == attendance_id)
    )
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Зберігаємо дані для аудиту перед видаленням
    student_name = f"{attendance.student.first_name} {attendance.student.last_name}" if attendance.student else "(учень видалений)"
    status_value = attendance.status.value if attendance.status else "не вказано"
    
    # Завантажуємо інформацію про урок
    if attendance.lesson_event:
        lesson_event = attendance.lesson_event
        # Завантажуємо schedule для деталей
        if lesson_event.schedule_id:
            schedule_result = await db.execute(
                select(Schedule)
                .options(selectinload(Schedule.club), selectinload(Schedule.teacher))
                .where(Schedule.id == lesson_event.schedule_id)
            )
            schedule = schedule_result.scalar_one_or_none()
            club_name = schedule.club.name if schedule and schedule.club else "(гурток не вказаний)"
            teacher_name = schedule.teacher.full_name if schedule and schedule.teacher else "(викладач не вказаний)"
        else:
            club_name = "(гурток не вказаний)"
            teacher_name = "(викладач не вказаний)"
        
        lesson_date_str = lesson_event.start_at.strftime("%d.%m.%Y %H:%M") if lesson_event.start_at else "(дата не вказана)"
    else:
        club_name = "(урок видалений)"
        teacher_name = "(викладач не вказаний)"
        lesson_date_str = "(дата не вказана)"
    
    await db.execute(delete(Attendance).where(Attendance.id == attendance_id))
    
    # 📝 AUDIT LOG: Видалення запису відвідуваності
    try:
        from app.services.audit_service import log_audit
        
        status_ua = {"PRESENT": "Присутній", "ABSENT": "Відсутній"}
        status_ua_str = status_ua.get(status_value, status_value)
        
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="attendance",
            entity_id=attendance_id,
            entity_name=f"{student_name} → {club_name} ({lesson_date_str})",
            description=f"Видалено запис відвідуваності: {student_name}, урок '{club_name}' ({teacher_name}, {lesson_date_str}). Статус був: {status_ua_str}",
            user_name="Адміністратор",
            changes={
                "deleted": {
                    "student": student_name,
                    "club": club_name,
                    "teacher": teacher_name,
                    "lesson_date": lesson_date_str,
                    "status": status_value,
                    "status_ua": status_ua_str
                }
            }
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (attendance DELETE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()


@router.get("/attendance/export/excel")
async def export_attendance_excel(
    db: DbSession,
    date_from: Optional[date] = Query(None, description="Дата початку"),
    date_to: Optional[date] = Query(None, description="Дата кінця"),
    club_id: Optional[int] = Query(None, description="ID гуртка"),
    teacher_id: Optional[int] = Query(None, description="ID вчителя"),
    status: Optional[str] = Query(None, description="Статус відвідуваності")
) -> StreamingResponse:
    """Export attendance records to Excel with optional filters."""
    
    # Базовий запит
    query = (
        select(Attendance)
        .options(
            selectinload(Attendance.student),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
            selectinload(Attendance.lesson_event).selectinload(LessonEvent.teacher),
        )
        .order_by(Attendance.marked_at.desc())
    )
    
    # Застосувати фільтри
    if date_from:
        query = query.where(LessonEvent.date >= date_from)
    
    if date_to:
        query = query.where(LessonEvent.date <= date_to)
    
    if club_id:
        query = query.where(LessonEvent.club_id == club_id)
    
    if teacher_id:
        query = query.where(LessonEvent.teacher_id == teacher_id)
    
    if status:
        query = query.where(Attendance.status == AttendanceStatus(status))
    
    # Виконати запит
    result = await db.execute(query)
    attendance_records = result.scalars().all()
    
    if not attendance_records:
        raise HTTPException(status_code=404, detail="No attendance records found")
    
    # Підготувати дані для Excel
    data = []
    for record in attendance_records:
        data.append({
            'Дата': record.lesson_event.date.strftime('%d.%m.%Y') if record.lesson_event.date else '',
            'Студент': record.student.full_name if record.student else '',
            'Гурток': record.lesson_event.club.name if record.lesson_event.club else '',
            'Вчитель': record.lesson_event.teacher.full_name if record.lesson_event.teacher else '',
            'Статус': 'Присутній' if record.status == AttendanceStatus.PRESENT else 'Відсутній',
            'Відмітив': record.marked_by or 'Система',
            'Час відмітки': record.marked_at.strftime('%d.%m.%Y %H:%M') if record.marked_at else ''
        })
    
    # Створити Excel файл в пам'яті
    try:
        import pandas as pd
        
        df = pd.DataFrame(data)
        
        # Створити Excel файл в пам'яті
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Відвідуваність', index=False)
            
            # Налаштувати ширину колонок
            worksheet = writer.sheets['Відвідуваність']
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
        
        output.seek(0)
        
        # Генерувати ім'я файлу
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"attendance_{today}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ImportError:
        # Fallback до CSV якщо pandas не доступний
        import csv
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        csv_content = output.getvalue()
        
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"attendance_{today}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


# === ENROLLMENTS ===
class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    club_id: int
    is_primary: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/enrollments", response_model=List[EnrollmentResponse])
async def get_enrollments(db: DbSession) -> List[Enrollment]:
    """Get all enrollments."""
    result = await db.execute(select(Enrollment))
    return result.scalars().all()


class EnrollmentCreate(BaseModel):
    """Enrollment creation model."""
    student_id: int
    club_id: int
    is_primary: bool = False


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=201)
async def create_enrollment(enrollment_data: EnrollmentCreate, db: DbSession) -> Enrollment:
    """Enroll student in a club."""
    # Перевірка що студент та гурток існують
    student_result = await db.execute(select(Student).where(Student.id == enrollment_data.student_id))
    if not student_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")
    
    club_result = await db.execute(select(Club).where(Club.id == enrollment_data.club_id))
    if not club_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Club not found")
    
    # Перевірка чи студент вже записаний на цей гурток
    existing_result = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == enrollment_data.student_id,
            Enrollment.club_id == enrollment_data.club_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Student already enrolled in this club")
    
    enrollment = Enrollment(**enrollment_data.model_dump())
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    
    # 📝 AUDIT LOG: Запис учня на гурток
    try:
        from app.services.audit_service import log_audit
        student = await db.get(Student, enrollment_data.student_id)
        club = await db.get(Club, enrollment_data.club_id)
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="enrollment",
            entity_id=enrollment.id,
            entity_name=f"{student.first_name} {student.last_name} → {club.name}",
            description=f"Учня {student.first_name} {student.last_name} записано на гурток '{club.name}'",
            user_name="Адміністратор",
            changes={"student_id": enrollment_data.student_id, "club_id": enrollment_data.club_id}
        )
    except Exception as e:
        pass
    
    return enrollment


@router.delete("/enrollments/{enrollment_id}", status_code=204)
async def delete_enrollment(enrollment_id: int, db: DbSession) -> None:
    """Remove student from club and all related schedules."""
    # Отримуємо інформацію про запис
    enrollment_result = await db.execute(
        select(Enrollment)
        .options(
            selectinload(Enrollment.student),
            selectinload(Enrollment.club)
        )
        .where(Enrollment.id == enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Знаходимо всі розклади цього гуртка, на які записаний учень
    schedule_enrollments_result = await db.execute(
        select(ScheduleEnrollment)
        .join(Schedule, Schedule.id == ScheduleEnrollment.schedule_id)
        .where(
            ScheduleEnrollment.student_id == enrollment.student_id,
            Schedule.club_id == enrollment.club_id
        )
    )
    schedule_enrollments = schedule_enrollments_result.scalars().all()
    
    # Видаляємо всі записи на розклади цього гуртка
    for schedule_enrollment in schedule_enrollments:
        await db.delete(schedule_enrollment)
    
    # Видаляємо загальний запис на гурток
    await db.delete(enrollment)
    
    # Логування каскадного видалення
    student_name = f"{enrollment.student.first_name} {enrollment.student.last_name}"
    club_name = enrollment.club.name
    schedule_count = len(schedule_enrollments)
    
    print(f"🗑️ Каскадне видалення: {student_name} видалено з гуртка '{club_name}' та {schedule_count} розкладів")
    
    await db.commit()
    
    # 📝 AUDIT LOG: Видалення запису на гурток
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="enrollment",
            entity_id=enrollment_id,
            entity_name=f"{student_name} → {club_name}",
            description=f"Учня {student_name} відписано від гуртка '{club_name}' (видалено {schedule_count} розкладів)",
            user_name="Адміністратор",
            changes={"student": student_name, "club": club_name, "schedules_removed": schedule_count}
        )
    except Exception as e:
        pass


@router.delete("/enrollments/student/{student_id}/club/{club_id}", status_code=204)
async def delete_enrollment_by_ids(student_id: int, club_id: int, db: DbSession) -> None:
    """Remove student from club by student and club IDs."""
    # Знаходимо запис
    enrollment_result = await db.execute(
        select(Enrollment)
        .options(
            selectinload(Enrollment.student),
            selectinload(Enrollment.club)
        )
        .where(
            Enrollment.student_id == student_id,
            Enrollment.club_id == club_id
        )
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this club")
    
    # Знаходимо всі розклади цього гуртка, на які записаний учень
    schedule_enrollments_result = await db.execute(
        select(ScheduleEnrollment)
        .join(Schedule, Schedule.id == ScheduleEnrollment.schedule_id)
        .where(
            ScheduleEnrollment.student_id == student_id,
            Schedule.club_id == club_id
        )
    )
    schedule_enrollments = schedule_enrollments_result.scalars().all()
    
    # Видаляємо всі записи на розклади цього гуртка
    for schedule_enrollment in schedule_enrollments:
        await db.delete(schedule_enrollment)
    
    # Видаляємо загальний запис на гурток
    await db.delete(enrollment)
    
    # Логування каскадного видалення
    student_name = f"{enrollment.student.first_name} {enrollment.student.last_name}"
    club_name = enrollment.club.name
    schedule_count = len(schedule_enrollments)
    
    print(f"🗑️ Каскадне видалення: {student_name} видалено з гуртка '{club_name}' та {schedule_count} розкладів")
    
    await db.commit()


# === SCHEDULE ENROLLMENTS ===
class ScheduleEnrollmentCreate(BaseModel):
    """Schedule enrollment creation model."""
    student_id: int
    schedule_id: int


class ScheduleEnrollmentResponse(BaseModel):
    """Schedule enrollment response model."""
    id: int
    student_id: int
    schedule_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/schedule-enrollments", response_model=List[ScheduleEnrollmentResponse])
async def get_schedule_enrollments(db: DbSession) -> List[ScheduleEnrollment]:
    """Get all schedule enrollments."""
    result = await db.execute(
        select(ScheduleEnrollment)
        .options(
            selectinload(ScheduleEnrollment.student),
            selectinload(ScheduleEnrollment.schedule)
        )
    )
    return result.scalars().all()


@router.get("/schedule-enrollments/{schedule_id}", response_model=List[ScheduleEnrollmentResponse])
async def get_schedule_enrollments_by_schedule(schedule_id: int, db: DbSession) -> List[ScheduleEnrollment]:
    """Get all students enrolled in a specific schedule."""
    result = await db.execute(
        select(ScheduleEnrollment)
        .where(ScheduleEnrollment.schedule_id == schedule_id)
        .options(
            selectinload(ScheduleEnrollment.student),
            selectinload(ScheduleEnrollment.schedule)
        )
    )
    return result.scalars().all()


@router.post("/schedule-enrollments", response_model=ScheduleEnrollmentResponse, status_code=201)
async def create_schedule_enrollment(enrollment_data: ScheduleEnrollmentCreate, db: DbSession) -> ScheduleEnrollment:
    """Enroll student in a schedule."""
    # Перевірка що студент та розклад існують
    student_result = await db.execute(select(Student).where(Student.id == enrollment_data.student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    schedule_result = await db.execute(
        select(Schedule)
        .options(selectinload(Schedule.club))
        .where(Schedule.id == enrollment_data.schedule_id)
    )
    schedule = schedule_result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Перевірка чи студент вже записаний на цей розклад
    existing_schedule_enrollment = await db.execute(
        select(ScheduleEnrollment).where(
            ScheduleEnrollment.student_id == enrollment_data.student_id,
            ScheduleEnrollment.schedule_id == enrollment_data.schedule_id
        )
    )
    if existing_schedule_enrollment.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Student already enrolled in this schedule")
    
    # Перевірка чи студент записаний на цей гурток (загальний Enrollment)
    existing_enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == enrollment_data.student_id,
            Enrollment.club_id == schedule.club_id
        )
    )
    
    # Якщо студент ще не записаний на цей гурток - створюємо загальний запис
    if not existing_enrollment.scalar_one_or_none():
        club_enrollment = Enrollment(
            student_id=enrollment_data.student_id,
            club_id=schedule.club_id,
            is_primary=False  # Не робимо основним автоматично
        )
        db.add(club_enrollment)
        # Логування автоматичного створення запису на гурток
        print(f"🔄 Автоматично записано на гурток: {student.first_name} {student.last_name} → {schedule.club.name}")
    
    # Створюємо запис на конкретний розклад
    schedule_enrollment = ScheduleEnrollment(**enrollment_data.model_dump())
    db.add(schedule_enrollment)
    await db.flush()  # Flush щоб отримати ID
    
    # 📝 AUDIT LOG: Запис учня на розклад (КРИТИЧНО ВАЖЛИВО!)
    try:
        from app.services.audit_service import log_audit
        student_name = f"{student.first_name} {student.last_name}"
        club_name = schedule.club.name if schedule.club else "(гурток не вказаний)"
        schedule_info = f"{schedule.weekday} {schedule.start_time.strftime('%H:%M')}"
        
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="schedule_enrollment",
            entity_id=schedule_enrollment.id,
            entity_name=f"{student_name} → {club_name} ({schedule_info})",
            description=f"Учня {student_name} записано на розклад '{club_name}' ({schedule_info})",
            user_name="Адміністратор",
            changes={
                "student_id": enrollment_data.student_id,
                "student_name": student_name,
                "schedule_id": enrollment_data.schedule_id,
                "club_name": club_name,
                "schedule_time": schedule_info
            }
        )
    except Exception as e:
        pass
    
    await db.commit()
    await db.refresh(schedule_enrollment)
    return schedule_enrollment


@router.delete("/schedule-enrollments/{enrollment_id}", status_code=204)
async def delete_schedule_enrollment(enrollment_id: int, db: DbSession) -> None:
    """Remove student from schedule."""
    # Отримуємо інформацію про запис
    result = await db.execute(
        select(ScheduleEnrollment)
        .options(selectinload(ScheduleEnrollment.schedule).selectinload(Schedule.club))
        .where(ScheduleEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Schedule enrollment not found")
    
    student_id = enrollment.student_id
    club_id = enrollment.schedule.club_id
    
    # Зберігаємо інформацію для аудиту перед видаленням
    student_result = await db.execute(select(Student).where(Student.id == student_id))
    student = student_result.scalar_one_or_none()
    student_name = f"{student.first_name} {student.last_name}" if student else "(учень видалений)"
    club_name = enrollment.schedule.club.name if enrollment.schedule and enrollment.schedule.club else "(гурток видалений)"
    schedule_info = f"{enrollment.schedule.weekday} {enrollment.schedule.start_time.strftime('%H:%M')}" if enrollment.schedule else "(розклад видалений)"
    
    # Видаляємо запис з розкладу
    await db.delete(enrollment)
    
    # 📝 AUDIT LOG: Відписування учня від розкладу (КРИТИЧНО ВАЖЛИВО!)
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="schedule_enrollment",
            entity_id=enrollment_id,
            entity_name=f"{student_name} → {club_name} ({schedule_info})",
            description=f"Учня {student_name} відписано від розкладу '{club_name}' ({schedule_info})",
            user_name="Адміністратор",
            changes={
                "student_id": student_id,
                "student_name": student_name,
                "schedule_id": enrollment.schedule_id,
                "club_name": club_name,
                "schedule_time": schedule_info
            }
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (schedule_enrollment DELETE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Перевіряємо чи є ще записи цього учня на інші розклади цього ж гуртка
    other_schedule_enrollments = await db.execute(
        select(ScheduleEnrollment)
        .join(Schedule, Schedule.id == ScheduleEnrollment.schedule_id)
        .where(
            ScheduleEnrollment.student_id == student_id,
            Schedule.club_id == club_id,
            ScheduleEnrollment.id != enrollment_id
        )
    )
    
    # Якщо це був останній розклад цього гуртка для цього учня - видаляємо загальний Enrollment
    if not other_schedule_enrollments.scalars().all():
        # Знаходимо та видаляємо загальний запис на гурток
        general_enrollment_result = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.student))
            .where(
                Enrollment.student_id == student_id,
                Enrollment.club_id == club_id
            )
        )
        general_enrollment = general_enrollment_result.scalar_one_or_none()
        
        if general_enrollment:
            await db.delete(general_enrollment)
            student_name = f"{general_enrollment.student.first_name} {general_enrollment.student.last_name}"
            club_name = enrollment.schedule.club.name
            print(f"🗑️ Автоматично видалено загальний запис: {student_name} більше не записаний на {club_name}")
    
    await db.commit()


@router.delete("/schedule-enrollments/student/{student_id}/schedule/{schedule_id}", status_code=204)
async def delete_schedule_enrollment_by_ids(student_id: int, schedule_id: int, db: DbSession) -> None:
    """Remove student from schedule by student and schedule IDs."""
    result = await db.execute(
        select(ScheduleEnrollment).where(
            ScheduleEnrollment.student_id == student_id,
            ScheduleEnrollment.schedule_id == schedule_id
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this schedule")
    
    # Отримуємо інформацію про розклад та гурток
    schedule_result = await db.execute(
        select(Schedule)
        .options(selectinload(Schedule.club))
        .where(Schedule.id == schedule_id)
    )
    schedule = schedule_result.scalar_one_or_none()
    
    # Завантажуємо дані учня для аудиту
    student_result = await db.execute(select(Student).where(Student.id == student_id))
    student = student_result.scalar_one_or_none()
    student_name = f"{student.first_name} {student.last_name}" if student else "(учень видалений)"
    club_name = schedule.club.name if schedule and schedule.club else "(гурток не вказаний)"
    schedule_info = f"{schedule.weekday} {schedule.start_time.strftime('%H:%M')}" if schedule else "(розклад не знайдений)"
    
    # Видаляємо запис з розкладу
    await db.delete(enrollment)
    
    # 📝 AUDIT LOG: Відписування учня від розкладу (КРИТИЧНО ВАЖЛИВО!)
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="schedule_enrollment",
            entity_id=enrollment.id,
            entity_name=f"{student_name} → {club_name} ({schedule_info})",
            description=f"Учня {student_name} відписано від розкладу '{club_name}' ({schedule_info})",
            user_name="Адміністратор",
            changes={
                "student_id": student_id,
                "student_name": student_name,
                "schedule_id": schedule_id,
                "club_name": club_name,
                "schedule_time": schedule_info
            }
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (schedule_enrollment DELETE by IDs): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Перевіряємо чи є ще записи цього учня на інші розклади цього ж гуртка
    if schedule:
        other_schedule_enrollments = await db.execute(
            select(ScheduleEnrollment)
            .join(Schedule, Schedule.id == ScheduleEnrollment.schedule_id)
            .where(
                ScheduleEnrollment.student_id == student_id,
                Schedule.club_id == schedule.club_id,
                ScheduleEnrollment.id != enrollment.id
            )
        )
        
        # Якщо це був останній розклад цього гуртка для цього учня - видаляємо загальний Enrollment
        if not other_schedule_enrollments.scalars().all():
            # Знаходимо та видаляємо загальний запис на гурток
            general_enrollment_result = await db.execute(
                select(Enrollment)
                .options(selectinload(Enrollment.student))
                .where(
                    Enrollment.student_id == student_id,
                    Enrollment.club_id == schedule.club_id
                )
            )
            general_enrollment = general_enrollment_result.scalar_one_or_none()
            
            if general_enrollment:
                await db.delete(general_enrollment)
                student_name = f"{general_enrollment.student.first_name} {general_enrollment.student.last_name}"
                print(f"🗑️ Автоматично видалено загальний запис: {student_name} більше не записаний на {schedule.club.name}")
            else:
                print(f"ℹ️ Загальний запис для учня {student_id} на гурток {schedule.club.name} не знайдено")
    
    await db.commit()


# === ANALYTICS ===

@router.get("/analytics/club/{club_id}")
async def get_club_attendance_analytics(club_id: int, db: DbSession):
    """Get attendance analytics for a specific club - separated by schedules in Google Sheets style."""
    
    # Перевіряємо чи існує гурток
    club_result = await db.execute(select(Club).where(Club.id == club_id))
    club = club_result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    # Отримуємо всі АКТИВНІ розклади для цього гуртка
    schedules_result = await db.execute(
        select(Schedule)
        .options(selectinload(Schedule.teacher))
        .where(Schedule.club_id == club_id, Schedule.active == True)
        .order_by(Schedule.weekday, Schedule.start_time)
    )
    schedules = schedules_result.scalars().all()
    
    if not schedules:
        return {
            "club": {
                "id": club.id,
                "name": club.name,
                "location": club.location
            },
            "schedules": []
        }
    
    # Формуємо результат з окремими таблицями для кожного розкладу
    analytics_data = {
        "club": {
            "id": club.id,
            "name": club.name,
            "location": club.location
        },
        "schedules": []
    }
    
    from app.models import ScheduleEnrollment
    
    # Дні тижня для відображення
    weekdays = {1: "Понеділок", 2: "Вівторок", 3: "Середа", 4: "Четвер", 5: "П'ятниця"}
    
    for schedule in schedules:
        # Отримуємо учнів записаних на КОНКРЕТНИЙ розклад
        students_result = await db.execute(
            select(Student)
            .join(ScheduleEnrollment, ScheduleEnrollment.student_id == Student.id)
            .where(ScheduleEnrollment.schedule_id == schedule.id)
            .order_by(Student.last_name, Student.first_name)
        )
        students = students_result.scalars().all()
        
        # Отримуємо всі дати проведених уроків для ЦЬОГО розкладу
        lesson_dates_result = await db.execute(
            select(LessonEvent.date, LessonEvent.id)
            .where(
                LessonEvent.schedule_id == schedule.id,
                LessonEvent.status == LessonEventStatus.COMPLETED
            )
            .order_by(LessonEvent.date)
        )
        lesson_events = lesson_dates_result.fetchall()
        
        # Створюємо список дат та lesson_event_ids для цього розкладу
        lesson_dates = []
        lesson_event_ids = []
        for row in lesson_events:
            date_str = row[0].strftime("%d.%m.%Y") if isinstance(row[0], date) else str(row[0])
            lesson_dates.append(date_str)
            lesson_event_ids.append(row[1])
        
        # Отримуємо attendance записи для цього розкладу
        attendance_map = {}
        if lesson_event_ids:
            attendance_result = await db.execute(
                select(Attendance)
                .where(Attendance.lesson_event_id.in_(lesson_event_ids))
            )
            attendance_records = attendance_result.scalars().all()
            
            # Створюємо словник для швидкого пошуку attendance
            for att in attendance_records:
                key = f"{att.student_id}_{att.lesson_event_id}"
                attendance_map[key] = att.status.value
        
        # Формуємо дані для цього розкладу
        schedule_data = {
            "schedule_id": schedule.id,
            "schedule_name": f"{weekdays.get(schedule.weekday, f'День {schedule.weekday}')} {schedule.start_time}",
            "weekday": schedule.weekday,
            "start_time": str(schedule.start_time),
            "teacher": {
                "id": schedule.teacher.id,
                "name": schedule.teacher.full_name
            } if schedule.teacher else None,
            "group_name": schedule.group_name or "Основна група",
            "lesson_dates": lesson_dates,
            "lesson_event_ids": lesson_event_ids,
            "students": []
        }
        
        # Додаємо учнів з їх відвідуваністю
        for student in students:
            student_data = {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "birth_date": student.birth_date.strftime("%d.%m.%Y") if student.birth_date else "—",
                "school_class": student.grade or "—",
                "phone_child": student.phone_child,
                "phone_mother": student.phone_mother,
                "phone_father": student.phone_father,
                "attendance": []
            }
            
            # Додаємо відмітки відвідуваності для кожної дати цього розкладу
            for i, lesson_event_id in enumerate(lesson_event_ids):
                key = f"{student.id}_{lesson_event_id}"
                status = attendance_map.get(key, None)
                
                student_data["attendance"].append({
                    "date": lesson_dates[i],
                    "lesson_event_id": lesson_event_id,
                    "status": status,
                    "icon": "✅" if status == "PRESENT" else "❌" if status == "ABSENT" else "⚪"
                })
            
            schedule_data["students"].append(student_data)
        
        # Додаємо розклад до результату тільки якщо є учні
        if students:
            analytics_data["schedules"].append(schedule_data)
    
    return analytics_data


@router.get("/dashboard/charts")
async def get_dashboard_charts(db: DbSession):
    """Get comprehensive dashboard charts data."""
    try:
        charts_data = {}
        
        # 1. 🎯 Розподіл учнів по гуртках (кругова діаграма)
        club_enrollment_query = select(
            Club.name,
            func.count(Enrollment.student_id).label('student_count')
        ).select_from(
            Club
        ).outerjoin(
            Enrollment, Club.id == Enrollment.club_id
        ).group_by(Club.id, Club.name).order_by(func.count(Enrollment.student_id).desc())
        
        result = await db.execute(club_enrollment_query)
        club_data = result.fetchall()
        charts_data["students_by_clubs"] = {
            "labels": [row.name for row in club_data],
            "data": [row.student_count for row in club_data],
            "type": "pie"
        }
        
        # 2. 📊 Активність вчителів (стовпчаста діаграма)
        teacher_activity_query = select(
            Teacher.full_name,
            func.count(ConductedLesson.id).label('lessons_count'),
            func.coalesce(func.sum(ConductedLesson.present_students), 0).label('total_present')
        ).select_from(
            Teacher
        ).outerjoin(
            ConductedLesson, Teacher.id == ConductedLesson.teacher_id
        ).group_by(Teacher.id, Teacher.full_name).order_by(func.count(ConductedLesson.id).desc())
        
        result = await db.execute(teacher_activity_query)
        teacher_data = result.fetchall()
        charts_data["teacher_activity"] = {
            "labels": [row.full_name for row in teacher_data],
            "lessons": [row.lessons_count for row in teacher_data],
            "students": [row.total_present for row in teacher_data],
            "type": "bar"
        }
        
        # 3. 📈 Динаміка відвідуваності по місяцях (лінійна діаграма)
        attendance_trend_query = select(
            extract('year', ConductedLesson.lesson_date).label('year'),
            extract('month', ConductedLesson.lesson_date).label('month'),
            func.avg(
                case(
                    (ConductedLesson.total_students > 0, 
                     ConductedLesson.present_students * 100.0 / ConductedLesson.total_students),
                    else_=0
                )
            ).label('avg_attendance')
        ).where(
            ConductedLesson.lesson_date.isnot(None)
        ).group_by(
            extract('year', ConductedLesson.lesson_date),
            extract('month', ConductedLesson.lesson_date)
        ).order_by('year', 'month')
        
        result = await db.execute(attendance_trend_query)
        attendance_trend = result.fetchall()
        charts_data["attendance_trend"] = {
            "labels": [f"{int(row.month):02d}/{int(row.year)}" for row in attendance_trend],
            "data": [round(float(row.avg_attendance), 1) for row in attendance_trend],
            "type": "line"
        }
        
        # 4. 💰 Розподіл зарплат по вчителях (кругова діаграма)
        salary_distribution_query = select(
            Teacher.full_name,
            func.coalesce(func.sum(Payroll.amount_decimal), 0).label('total_salary')
        ).select_from(
            Teacher
        ).outerjoin(
            Payroll, Teacher.id == Payroll.teacher_id
        ).group_by(Teacher.id, Teacher.full_name).order_by(func.sum(Payroll.amount_decimal).desc())
        
        result = await db.execute(salary_distribution_query)
        salary_data = result.fetchall()
        charts_data["salary_distribution"] = {
            "labels": [row.full_name for row in salary_data if row.total_salary > 0],
            "data": [float(row.total_salary) for row in salary_data if row.total_salary > 0],
            "type": "doughnut"
        }
        
        # 5. 📅 Кількість уроків по днях тижня (стовпчаста діаграма)
        weekday_lessons_query = select(
            extract('dow', ConductedLesson.lesson_date).label('weekday'),
            func.count(ConductedLesson.id).label('lessons_count')
        ).where(
            ConductedLesson.lesson_date.isnot(None)
        ).group_by(
            extract('dow', ConductedLesson.lesson_date)
        ).order_by('weekday')
        
        result = await db.execute(weekday_lessons_query)
        weekday_data = result.fetchall()
        weekday_names = ['Неділя', 'Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота']
        charts_data["lessons_by_weekday"] = {
            "labels": [weekday_names[int(row.weekday)] for row in weekday_data],
            "data": [row.lessons_count for row in weekday_data],
            "type": "bar"
        }
        
        # 6. 🎓 Розподіл учнів по класах (кругова діаграма)
        logger.info("📚 Starting students by grade chart...")
        grade_distribution_query = select(
            func.coalesce(Student.grade, 'Не вказано').label('grade'),
            func.count(Student.id).label('student_count')
        ).select_from(Student).group_by(Student.grade).order_by(func.count(Student.id).desc())
        
        result = await db.execute(grade_distribution_query)
        grade_data = result.fetchall()
        charts_data["students_by_grade"] = {
            "labels": [row.grade for row in grade_data],
            "data": [row.student_count for row in grade_data],
            "type": "pie"
        }
        logger.info(f"📚 Completed students by grade: {len(grade_data)} grades")
        
        # 7. 🔒 Розподіл учнів по критеріям вразливості (кругова діаграма)
        logger.info("🔒 Starting vulnerability chart calculation...")
        try:
            # ПРОСТИЙ ПІДХІД - спочатку отримуємо дані з БД
            students_result = await db.execute(
                select(
                    Student.benefit_internally_displaced,
                    Student.benefit_disability,
                    Student.benefit_large_family,
                    Student.benefit_military_family,
                    Student.benefit_low_income,
                    Student.benefit_orphan,
                    Student.benefit_social_risk
                ).select_from(Student)
            )
            students_data = students_result.fetchall()
            logger.info(f"🔒 Retrieved {len(students_data)} student records")
            
            # Підраховуємо в Python
            counts = {
                "ВПО (переселенці)": 0,
                "Діти з інвалідністю": 0,
                "Багатодітні сім'ї": 0,
                "Сім'ї ЗСУ": 0,
                "Малозабезпечені": 0,
                "Сироти/під опікою": 0,
                "Соціальний ризик": 0,
                "Без пільг": 0
            }
            
            for row in students_data:
                has_benefit = False
                if row[0]:  # benefit_internally_displaced
                    counts["ВПО (переселенці)"] += 1
                    has_benefit = True
                if row[1]:  # benefit_disability
                    counts["Діти з інвалідністю"] += 1
                    has_benefit = True
                if row[2]:  # benefit_large_family
                    counts["Багатодітні сім'ї"] += 1
                    has_benefit = True
                if row[3]:  # benefit_military_family
                    counts["Сім'ї ЗСУ"] += 1
                    has_benefit = True
                if row[4]:  # benefit_low_income
                    counts["Малозабезпечені"] += 1
                    has_benefit = True
                if row[5]:  # benefit_orphan
                    counts["Сироти/під опікою"] += 1
                    has_benefit = True
                if row[6]:  # benefit_social_risk
                    counts["Соціальний ризик"] += 1
                    has_benefit = True
                
                if not has_benefit:
                    counts["Без пільг"] += 1
            
            # Фільтруємо категорії з студентами
            filtered_labels = []
            filtered_data = []
            for label, count in counts.items():
                if count > 0:
                    filtered_labels.append(label)
                    filtered_data.append(count)
            
            logger.info(f"🔒 Vulnerability counts: {counts}")
            
            charts_data["students_by_vulnerability"] = {
                "labels": filtered_labels,
                "data": filtered_data,
                "type": "pie",
                "colors": [
                    "#DC3545",  # ВПО - червоний
                    "#6F42C1",  # Інвалідність - фіолетовий
                    "#28A745",  # Багатодітні - зелений
                    "#FFC107",  # ЗСУ - жовтий
                    "#FD7E14",  # Малозабезпечені - помаранчевий
                    "#17A2B8",  # Сироти - блакитний
                    "#E83E8C",  # Соціальний ризик - рожевий
                    "#6C757D"   # Без пільг - сірий
                ][:len(filtered_labels)]
            }
            logger.info(f"✅ Vulnerability chart created with {len(filtered_labels)} categories")
        except Exception as e:
            logger.error(f"❌ Error in vulnerability query: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            charts_data["students_by_vulnerability"] = {
                "labels": ["Без даних"],
                "data": [0],
                "type": "pie"
            }
        
        # 8. 🏠 Детальний розподіл пільг (стовпчаста діаграма)
        try:
            benefits_detailed_query = select(
                func.count(case((Student.benefit_internally_displaced == True, 1))).label('displaced'),
                func.count(case((Student.benefit_disability == True, 1))).label('disability'),
                func.count(case((Student.benefit_large_family == True, 1))).label('large_family'),
                func.count(case((Student.benefit_military_family == True, 1))).label('military'),
                func.count(case((Student.benefit_low_income == True, 1))).label('low_income'),
                func.count(case((Student.benefit_orphan == True, 1))).label('orphan'),
                func.count(case((Student.benefit_social_risk == True, 1))).label('social_risk')
            ).select_from(Student)
            
            result = await db.execute(benefits_detailed_query)
            benefits_data = result.fetchone()
            charts_data["benefits_detailed"] = {
                "labels": ["ВПО", "Інвалідність", "Багатодітні", "Сім'ї ЗСУ", "Малозабезпечені", "Сироти", "Соц. ризик"],
                "data": [
                    benefits_data.displaced,
                    benefits_data.disability,
                    benefits_data.large_family,
                    benefits_data.military,
                    benefits_data.low_income,
                    benefits_data.orphan,
                    benefits_data.social_risk
                ],
                "type": "bar",
                "backgroundColor": [
                    "#DC3545", "#6F42C1", "#28A745", "#FFC107", 
                    "#FD7E14", "#17A2B8", "#E83E8C"
                ]
            }
            logger.info(f"✅ Benefits detailed data: {benefits_data}")
        except Exception as e:
            logger.error(f"❌ Error in benefits detailed query: {e}")
            charts_data["benefits_detailed"] = {
                "labels": ["Без даних"],
                "data": [0],
                "type": "bar"
            }
        
        # 9. 🏘️ Розподіл учнів по населених пунктах (стовпчаста діаграма)
        location_distribution_query = select(
            func.coalesce(Student.location, 'Не вказано').label('location'),
            func.count(Student.id).label('student_count')
        ).select_from(Student).group_by(Student.location).order_by(func.count(Student.id).desc()).limit(10)
        
        result = await db.execute(location_distribution_query)
        location_data = result.fetchall()
        charts_data["students_by_location"] = {
            "labels": [row.location for row in location_data],
            "data": [row.student_count for row in location_data],
            "type": "horizontalBar"
        }
        
        # 8. 💸 Динаміка зарплат по місяцях (лінійна діаграма)
        salary_trend_query = select(
            extract('year', Payroll.created_at).label('year'),
            extract('month', Payroll.created_at).label('month'),
            func.sum(Payroll.amount_decimal).label('total_salary')
        ).group_by(
            extract('year', Payroll.created_at),
            extract('month', Payroll.created_at)
        ).order_by('year', 'month')
        
        result = await db.execute(salary_trend_query)
        salary_trend = result.fetchall()
        charts_data["salary_trend"] = {
            "labels": [f"{int(row.month):02d}/{int(row.year)}" for row in salary_trend],
            "data": [float(row.total_salary) for row in salary_trend],
            "type": "line"
        }
        
        # 9. 🏆 Топ-10 найактивніших учнів (стовпчаста діаграма)
        top_students_query = select(
            Student.first_name,
            Student.last_name,
            func.count(
                case(
                    (Attendance.status == 'PRESENT', 1),
                    else_=None
                )
            ).label('attendance_count')
        ).select_from(
            Student
        ).outerjoin(
            Attendance, Student.id == Attendance.student_id
        ).group_by(Student.id, Student.first_name, Student.last_name).order_by(
            func.count(
                case(
                    (Attendance.status == 'PRESENT', 1),
                    else_=None
                )
            ).desc()
        ).limit(10)
        
        result = await db.execute(top_students_query)
        top_students = result.fetchall()
        charts_data["top_students"] = {
            "labels": [f"{row.first_name} {row.last_name}" for row in top_students],
            "data": [row.attendance_count for row in top_students],
            "type": "bar"
        }
        
        # 10. 🎯 Загальна статистика відвідуваності (кругова діаграма)
        overall_attendance_query = select(
            func.sum(
                case(
                    (Attendance.status == 'PRESENT', 1),
                    else_=0
                )
            ).label('present_count'),
            func.sum(
                case(
                    (Attendance.status == 'ABSENT', 1),
                    else_=0
                )
            ).label('absent_count')
        ).select_from(Attendance)
        
        result = await db.execute(overall_attendance_query)
        attendance_stats = result.fetchone()
        charts_data["overall_attendance"] = {
            "labels": ['Присутні', 'Відсутні'],
            "data": [attendance_stats.present_count or 0, attendance_stats.absent_count or 0],
            "type": "doughnut"
        }
        
        # Логування перед поверненням
        logger.info(f"✅ Charts data keys: {list(charts_data.keys())}")
        logger.info(f"📊 Students by vulnerability: {'students_by_vulnerability' in charts_data}")
        logger.info(f"🏠 Benefits detailed: {'benefits_detailed' in charts_data}")
        
        # Логування конкретних даних вразливості
        if 'students_by_vulnerability' in charts_data:
            vuln_data = charts_data['students_by_vulnerability']
            logger.info(f"📊 Vulnerability data: {vuln_data}")
        
        if 'benefits_detailed' in charts_data:
            benefits_data = charts_data['benefits_detailed']
            logger.info(f"🏠 Benefits data: {benefits_data}")
        
        return charts_data
        
    except Exception as e:
        logger.error(f"Error fetching dashboard charts: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard charts: {e}")


@router.get("/statistics")
async def get_advanced_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    club_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive statistics with time-based filtering."""
    
    try:
        logger.info(f"📊 Fetching advanced statistics with filters: start_date={start_date}, end_date={end_date}, club_id={club_id}, teacher_id={teacher_id}")
        
        # Парсимо дати
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # === ЗАГАЛЬНА СТАТИСТИКА ===
        
        # Кількість студентів
        students_query = select(func.count(Student.id))
        students_result = await db.execute(students_query)
        total_students = students_result.scalar()
        
        # Кількість вчителів
        teachers_query = select(func.count(Teacher.id)).where(Teacher.active == True)
        teachers_result = await db.execute(teachers_query)
        total_teachers = teachers_result.scalar()
        
        # Кількість гуртків
        clubs_query = select(func.count(Club.id))
        clubs_result = await db.execute(clubs_query)
        total_clubs = clubs_result.scalar()
        
        # Кількість активних розкладів
        schedules_query = select(func.count(Schedule.id)).where(Schedule.active == True)
        schedules_result = await db.execute(schedules_query)
        total_schedules = schedules_result.scalar()
        
        # === СТАТИСТИКА ГУРТКІВ ===
        
        clubs_stats_query = select(
            Club.id,
            Club.name,
            func.count(Enrollment.id).label('enrolled_students')
        ).select_from(Club)\
         .outerjoin(Enrollment)\
         .group_by(Club.id, Club.name)\
         .order_by(Club.name)
        
        if club_id:
            clubs_stats_query = clubs_stats_query.where(Club.id == club_id)
        
        clubs_stats_result = await db.execute(clubs_stats_query)
        clubs_stats = []
        for row in clubs_stats_result:
            # Розраховуємо відвідуваність для гуртка
            club_attendance_query = select(
                func.count(Attendance.id).label('total_attendance'),
                func.count(case((Attendance.status == 'PRESENT', 1))).label('present_count')
            ).select_from(Attendance)\
             .join(LessonEvent)\
             .where(LessonEvent.club_id == row.id)
            
            if start_dt:
                club_attendance_query = club_attendance_query.where(func.date(LessonEvent.start_at) >= start_dt)
            if end_dt:
                club_attendance_query = club_attendance_query.where(func.date(LessonEvent.start_at) <= end_dt)
            
            club_attendance_result = await db.execute(club_attendance_query)
            club_attendance_data = club_attendance_result.first()
            
            club_attendance_rate = 0
            if club_attendance_data.total_attendance and club_attendance_data.total_attendance > 0:
                club_attendance_rate = round((club_attendance_data.present_count / club_attendance_data.total_attendance * 100), 2)
            
            club_data = {
                "id": row.id,
                "name": row.name,
                "enrolled_students": row.enrolled_students or 0,
                "attendance_rate": club_attendance_rate
            }
            clubs_stats.append(club_data)
        
        # === СТАТИСТИКА ВЧИТЕЛІВ ===
        
        teachers_stats_query = select(
            Teacher.id,
            Teacher.full_name,
            func.count(Schedule.id).label('schedules_count')
        ).select_from(Teacher)\
         .outerjoin(Schedule, and_(Schedule.teacher_id == Teacher.id, Schedule.active == True))\
         .where(Teacher.active == True)\
         .group_by(Teacher.id, Teacher.full_name)\
         .order_by(Teacher.full_name)
        
        if teacher_id:
            teachers_stats_query = teachers_stats_query.where(Teacher.id == teacher_id)
        
        teachers_stats_result = await db.execute(teachers_stats_query)
        teachers_stats = []
        for row in teachers_stats_result:
            # Розраховуємо кількість проведених уроків (ТІЛЬКИ COMPLETED, унікальні lesson_events)
            teacher_lessons_query = select(
                func.count(func.distinct(LessonEvent.id)).label('lessons_conducted')
            ).select_from(LessonEvent)\
             .where(LessonEvent.teacher_id == row.id)\
             .where(LessonEvent.status == LessonEventStatus.COMPLETED)
            
            if start_dt:
                teacher_lessons_query = teacher_lessons_query.where(func.date(LessonEvent.start_at) >= start_dt)
            if end_dt:
                teacher_lessons_query = teacher_lessons_query.where(func.date(LessonEvent.start_at) <= end_dt)
            if club_id:
                teacher_lessons_query = teacher_lessons_query.where(LessonEvent.club_id == club_id)
            
            teacher_lessons_result = await db.execute(teacher_lessons_query)
            lessons_conducted = teacher_lessons_result.scalar() or 0
            
            # Розраховуємо кількість унікальних студентів, яких навчав вчитель
            teacher_students_query = select(
                func.count(func.distinct(Attendance.student_id)).label('students_taught')
            ).select_from(Attendance)\
             .join(LessonEvent)\
             .where(LessonEvent.teacher_id == row.id)
            
            if start_dt:
                teacher_students_query = teacher_students_query.where(func.date(LessonEvent.start_at) >= start_dt)
            if end_dt:
                teacher_students_query = teacher_students_query.where(func.date(LessonEvent.start_at) <= end_dt)
            if club_id:
                teacher_students_query = teacher_students_query.where(LessonEvent.club_id == club_id)
            
            teacher_students_result = await db.execute(teacher_students_query)
            students_taught = teacher_students_result.scalar() or 0
            
            teacher_data = {
                "id": row.id,
                "name": row.full_name,
                "schedules_count": row.schedules_count or 0,
                "lessons_conducted": lessons_conducted,
                "students_taught": students_taught
            }
            teachers_stats.append(teacher_data)
        
        # === СТАТИСТИКА ПІЛЬГ ===
        
        benefits_query = select(
            func.count(case((Student.benefit_low_income == True, 1))).label('low_income'),
            func.count(case((Student.benefit_large_family == True, 1))).label('large_family'),
            func.count(case((Student.benefit_military_family == True, 1))).label('military_family'),
            func.count(case((Student.benefit_internally_displaced == True, 1))).label('internally_displaced'),
            func.count(case((Student.benefit_orphan == True, 1))).label('orphan'),
            func.count(case((Student.benefit_disability == True, 1))).label('disability'),
            func.count(case((Student.benefit_social_risk == True, 1))).label('social_risk')
        ).select_from(Student)
        
        benefits_result = await db.execute(benefits_query)
        benefits_row = benefits_result.first()
        
        benefits_data = {
            "low_income": benefits_row.low_income or 0,
            "large_family": benefits_row.large_family or 0,
            "military_family": benefits_row.military_family or 0,
            "internally_displaced": benefits_row.internally_displaced or 0,
            "orphan": benefits_row.orphan or 0,
            "disability": benefits_row.disability or 0,
            "social_risk": benefits_row.social_risk or 0,
        }
        
        # Загальна кількість студентів без пільг
        total_benefits = sum(benefits_data.values())
        benefits_data["no_benefits"] = max(0, total_students - total_benefits)
        
        # === СТАТИСТИКА ВІДВІДУВАНОСТІ ===
        
        # Базовий запит для відвідуваності з фільтрами
        attendance_query = select(Attendance).options(selectinload(Attendance.lesson_event))
        
        if start_dt or end_dt or club_id or teacher_id:
            attendance_query = attendance_query.join(LessonEvent)
            if start_dt:
                attendance_query = attendance_query.where(func.date(LessonEvent.start_at) >= start_dt)
            if end_dt:
                attendance_query = attendance_query.where(func.date(LessonEvent.start_at) <= end_dt)
            if club_id:
                attendance_query = attendance_query.where(LessonEvent.club_id == club_id)
            if teacher_id:
                attendance_query = attendance_query.where(LessonEvent.teacher_id == teacher_id)
        
        attendance_result = await db.execute(attendance_query)
        attendance_records = attendance_result.scalars().all()
        
        total_attendance_records = len(attendance_records)
        present_count = len([a for a in attendance_records if a.status.value == "PRESENT"])
        absent_count = len([a for a in attendance_records if a.status.value == "ABSENT"])
        attendance_rate = round((present_count / total_attendance_records * 100), 2) if total_attendance_records > 0 else 0
        
        # Статистика по днях тижня (1=Понеділок, 7=Неділя)
        weekday_stats = {}
        weekday_names = {
            1: "Понеділок", 2: "Вівторок", 3: "Середа", 4: "Четвер", 
            5: "П'ятниця", 6: "Субота", 7: "Неділя"
        }
        
        for attendance in attendance_records:
            if attendance.lesson_event and attendance.lesson_event.start_at:
                # PostgreSQL EXTRACT(dow FROM date) повертає 0=Неділя, 1=Понеділок...6=Субота
                # Конвертуємо в 1=Понеділок...7=Неділя
                lesson_date = attendance.lesson_event.start_at
                weekday = lesson_date.weekday() + 1  # Python weekday: 0=Понеділок, додаємо 1
                
                if weekday not in weekday_stats:
                    weekday_stats[weekday] = {"total": 0, "present": 0, "absent": 0}
                
                weekday_stats[weekday]["total"] += 1
                if attendance.status.value == "PRESENT":
                    weekday_stats[weekday]["present"] += 1
                else:
                    weekday_stats[weekday]["absent"] += 1
        
        # Конвертуємо у список для frontend
        weekday_list = []
        for day_num in range(1, 8):  # 1-7
            day_data = weekday_stats.get(day_num, {"total": 0, "present": 0, "absent": 0})
            attendance_rate_day = round((day_data["present"] / day_data["total"] * 100), 2) if day_data["total"] > 0 else 0
            weekday_list.append({
                "day": weekday_names[day_num],
                "day_number": day_num,
                "total": day_data["total"],
                "present": day_data["present"],
                "absent": day_data["absent"],
                "attendance_rate": attendance_rate_day
            })
        
        # === ФІНАНСОВА СТАТИСТИКА ===
        
        payroll_query = select(
            func.count(Payroll.id).label('total_payroll_records'),
            func.sum(Payroll.amount_decimal).label('total_amount')
        ).select_from(Payroll)
        
        # ВИПРАВЛЕНО: Фільтруємо по даті УРОКУ, а не по created_at
        if start_dt or end_dt:
            payroll_query = payroll_query.join(LessonEvent, Payroll.lesson_event_id == LessonEvent.id)
        if start_dt:
                payroll_query = payroll_query.where(LessonEvent.date >= start_dt)
        if end_dt:
                payroll_query = payroll_query.where(LessonEvent.date <= end_dt)
        if teacher_id:
            payroll_query = payroll_query.where(Payroll.teacher_id == teacher_id)
        
        payroll_result = await db.execute(payroll_query)
        payroll_row = payroll_result.first()
        
        financial_stats = {
            "total_payroll_records": payroll_row.total_payroll_records or 0,
            "total_amount": float(payroll_row.total_amount) if payroll_row.total_amount else 0.0
        }
        
        # === ТОП СТУДЕНТИ ===
        
        # Запит для топ студентів по відвідуваності
        top_students_query = select(
            Student.id,
            Student.first_name,
            Student.last_name,
            func.count(case((Attendance.status == 'PRESENT', 1))).label('present_count'),
            func.count(Attendance.id).label('total_attendance'),
            (func.count(case((Attendance.status == 'PRESENT', 1))) * 100.0 / func.count(Attendance.id)).label('attendance_rate')
        ).select_from(Student)\
         .join(Attendance)\
         .join(LessonEvent)
        
        if start_dt:
            top_students_query = top_students_query.where(func.date(LessonEvent.start_at) >= start_dt)
        if end_dt:
            top_students_query = top_students_query.where(func.date(LessonEvent.start_at) <= end_dt)
        if club_id:
            top_students_query = top_students_query.where(LessonEvent.club_id == club_id)
        if teacher_id:
            top_students_query = top_students_query.where(LessonEvent.teacher_id == teacher_id)
        
        top_students_query = top_students_query.group_by(Student.id, Student.first_name, Student.last_name)\
                                               .having(func.count(Attendance.id) >= 2)\
                                               .order_by(text('attendance_rate DESC'))\
                                               .limit(10)
        
        top_students_result = await db.execute(top_students_query)
        top_students_data = []
        for row in top_students_result:
            student_data = {
                "id": row.id,
                "name": f"{row.first_name} {row.last_name}",
                "present_count": row.present_count or 0,
                "total_attendance": row.total_attendance or 0,
                "attendance_rate": round(float(row.attendance_rate), 2) if row.attendance_rate else 0
            }
            top_students_data.append(student_data)
        
        # === НОВІ МЕТРИКИ ===
        
        # 1. ТРЕНДИ ВІДВІДУВАНОСТІ (по місяцях)
        # ВИПРАВЛЕНО: Рахуємо унікальні уроки, а не записи attendance
        logger.info("📈 Calculating attendance trends...")
        
        # Спочатку отримуємо всі уроки за період
        lessons_query = select(
            func.to_char(LessonEvent.start_at, 'YYYY-MM').label('month'),
            func.count(func.distinct(LessonEvent.id)).label('total_lessons')
        ).select_from(LessonEvent)\
         .where(LessonEvent.status == LessonEventStatus.COMPLETED)
        
        if start_dt:
            lessons_query = lessons_query.where(func.date(LessonEvent.start_at) >= start_dt)
        if end_dt:
            lessons_query = lessons_query.where(func.date(LessonEvent.start_at) <= end_dt)
        if club_id:
            lessons_query = lessons_query.where(LessonEvent.club_id == club_id)
        if teacher_id:
            lessons_query = lessons_query.where(LessonEvent.teacher_id == teacher_id)
        
        lessons_query = lessons_query.group_by('month').order_by('month')
        lessons_result = await db.execute(lessons_query)
        
        # Тепер рахуємо відвідуваність
        attendance_trends = []
        for row in lessons_result:
            month = row.month
            
            # Рахуємо attendance для цього місяця
            att_query = select(
                func.count(Attendance.id).label('total_records'),
                func.count(case((Attendance.status == 'PRESENT', 1))).label('present_count')
            ).select_from(Attendance)\
             .join(LessonEvent)\
             .where(func.to_char(LessonEvent.start_at, 'YYYY-MM') == month)
            
            if club_id:
                att_query = att_query.where(LessonEvent.club_id == club_id)
            if teacher_id:
                att_query = att_query.where(LessonEvent.teacher_id == teacher_id)
            
            att_result = await db.execute(att_query)
            att_data = att_result.first()
            
            total_records = att_data.total_records or 0
            present_count = att_data.present_count or 0
            rate = round((present_count / total_records * 100), 2) if total_records > 0 else 0
            
            attendance_trends.append({
                "period": month,
                "total": row.total_lessons,  # Кількість УРОКІВ, а не записів
                "present": present_count,
                "absent": total_records - present_count,
                "attendance_rate": rate,
                "total_attendance_records": total_records  # Для інформації
            })
        
        # 2. ПІКОВІ ГОДИНИ ЗАНЯТЬ
        # ВИПРАВЛЕНО: Конвертуємо час з UTC в Київський (Europe/Kiev)
        logger.info("⏰ Calculating peak hours...")
        peak_hours_query = select(
            func.extract('hour', func.timezone('Europe/Kiev', LessonEvent.start_at)).label('hour'),
            func.count(LessonEvent.id).label('lessons_count')
        ).select_from(LessonEvent)\
         .where(LessonEvent.status == LessonEventStatus.COMPLETED)
        
        if start_dt:
            peak_hours_query = peak_hours_query.where(func.date(LessonEvent.start_at) >= start_dt)
        if end_dt:
            peak_hours_query = peak_hours_query.where(func.date(LessonEvent.start_at) <= end_dt)
        if club_id:
            peak_hours_query = peak_hours_query.where(LessonEvent.club_id == club_id)
        if teacher_id:
            peak_hours_query = peak_hours_query.where(LessonEvent.teacher_id == teacher_id)
        
        peak_hours_query = peak_hours_query.group_by('hour').order_by('hour')
        peak_hours_result = await db.execute(peak_hours_query)
        
        peak_hours_data = []
        max_lessons = 0
        for row in peak_hours_result:
            if row.hour is not None:
                hour = int(row.hour)
                lessons = row.lessons_count
                if lessons > max_lessons:
                    max_lessons = lessons
                peak_hours_data.append({
                    "hour": f"{hour:02d}:00-{hour+1:02d}:00",
                    "hour_number": hour,
                    "lessons_count": lessons
                })
        
        # Додаємо інформацію про пікову годину
        peak_hour_info = None
        if peak_hours_data:
            peak_hour_info = max(peak_hours_data, key=lambda x: x['lessons_count'])
        
        # 3. СТУДЕНТИ ЗІ ЗОНИ РИЗИКУ (відвідуваність < 60%)
        logger.info("⚠️ Identifying at-risk students...")
        at_risk_query = select(
            Student.id,
            Student.first_name,
            Student.last_name,
            Student.phone_mother,
            Student.phone_father,
            func.count(case((Attendance.status == 'PRESENT', 1))).label('present_count'),
            func.count(Attendance.id).label('total_attendance'),
            (func.count(case((Attendance.status == 'PRESENT', 1))) * 100.0 / func.count(Attendance.id)).label('attendance_rate')
        ).select_from(Student)\
         .join(Attendance)\
         .join(LessonEvent)
        
        if start_dt:
            at_risk_query = at_risk_query.where(func.date(LessonEvent.start_at) >= start_dt)
        if end_dt:
            at_risk_query = at_risk_query.where(func.date(LessonEvent.start_at) <= end_dt)
        if club_id:
            at_risk_query = at_risk_query.where(LessonEvent.club_id == club_id)
        if teacher_id:
            at_risk_query = at_risk_query.where(LessonEvent.teacher_id == teacher_id)
        
        at_risk_query = at_risk_query.group_by(Student.id, Student.first_name, Student.last_name, Student.phone_mother, Student.phone_father)\
                                     .having(func.count(Attendance.id) >= 3)\
                                     .having((func.count(case((Attendance.status == 'PRESENT', 1))) * 100.0 / func.count(Attendance.id)) < 60)\
                                     .order_by(text('attendance_rate ASC'))
        
        at_risk_result = await db.execute(at_risk_query)
        at_risk_students = []
        for row in at_risk_result:
            # Використовуємо телефон матері або батька (якщо є)
            phone = row.phone_mother or row.phone_father or None
            at_risk_students.append({
                "id": row.id,
                "name": f"{row.first_name} {row.last_name}",
                "phone": phone,
                "present_count": row.present_count or 0,
                "total_attendance": row.total_attendance or 0,
                "attendance_rate": round(float(row.attendance_rate), 2) if row.attendance_rate else 0
            })
        
        # 4. АЛЕРТИ ТА ПОПЕРЕДЖЕННЯ
        logger.info("🔔 Generating alerts...")
        alerts = []
        
        # Алерт: Студенти з дуже низькою відвідуваністю (< 50%)
        critical_students = [s for s in at_risk_students if s['attendance_rate'] < 50]
        if critical_students:
            alerts.append({
                "type": "danger",
                "icon": "exclamation-triangle-fill",
                "message": f"{len(critical_students)} студентів з критично низькою відвідуваністю (< 50%)",
                "count": len(critical_students),
                "action": "view_at_risk_students"
            })
        
        # Алерт: Вчителі без уроків останні 7 днів
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        inactive_teachers_query = select(Teacher.id, Teacher.full_name)\
            .select_from(Teacher)\
            .outerjoin(LessonEvent, and_(
                LessonEvent.teacher_id == Teacher.id,
                LessonEvent.start_at >= seven_days_ago
            ))\
            .where(Teacher.active == True)\
            .group_by(Teacher.id, Teacher.full_name)\
            .having(func.count(LessonEvent.id) == 0)
        
        inactive_teachers_result = await db.execute(inactive_teachers_query)
        inactive_teachers = inactive_teachers_result.fetchall()
        if inactive_teachers:
            alerts.append({
                "type": "warning",
                "icon": "person-x",
                "message": f"{len(inactive_teachers)} вчителів без уроків останні 7 днів",
                "count": len(inactive_teachers),
                "action": "view_inactive_teachers"
            })
        
        # Алерт: Гуртки з малою кількістю студентів (< 3)
        small_clubs_query = select(
            Club.id,
            Club.name,
            func.count(Enrollment.id).label('student_count')
        ).select_from(Club)\
         .outerjoin(Enrollment)\
         .group_by(Club.id, Club.name)\
         .having(func.count(Enrollment.id) < 3)\
         .having(func.count(Enrollment.id) > 0)
        
        small_clubs_result = await db.execute(small_clubs_query)
        small_clubs = small_clubs_result.fetchall()
        if small_clubs:
            alerts.append({
                "type": "warning",
                "icon": "collection",
                "message": f"{len(small_clubs)} гуртків з менше ніж 3 студентами",
                "count": len(small_clubs),
                "action": "view_small_clubs"
            })
        
        # Алерт: Розклади без студентів
        empty_schedules_query = select(
            Schedule.id,
            func.count(ScheduleEnrollment.id).label('enrollment_count')
        ).select_from(Schedule)\
         .outerjoin(ScheduleEnrollment)\
         .where(Schedule.active == True)\
         .group_by(Schedule.id)\
         .having(func.count(ScheduleEnrollment.id) == 0)
        
        empty_schedules_result = await db.execute(empty_schedules_query)
        empty_schedules = empty_schedules_result.fetchall()
        if empty_schedules:
            alerts.append({
                "type": "info",
                "icon": "calendar-x",
                "message": f"{len(empty_schedules)} розкладів без записаних студентів",
                "count": len(empty_schedules),
                "action": "view_empty_schedules"
            })
        
        # 5. KPI МЕТРИКИ
        logger.info("🎯 Calculating KPI metrics...")
        
        # KPI 1: Виконання плану уроків (ТІЛЬКИ МИНУЛІ уроки - заплановано vs проведено)
        # План = уроки що мали відбутись (PLANNED + COMPLETED + SKIPPED + CANCELLED з минулого)
        now = datetime.now(timezone.utc)
        
        planned_lessons_query = select(func.count(LessonEvent.id))\
            .where(LessonEvent.start_at < now)  # Тільки минулі уроки
        if start_dt:
            planned_lessons_query = planned_lessons_query.where(func.date(LessonEvent.start_at) >= start_dt)
        if end_dt:
            planned_lessons_query = planned_lessons_query.where(func.date(LessonEvent.start_at) <= end_dt)
        if club_id:
            planned_lessons_query = planned_lessons_query.where(LessonEvent.club_id == club_id)
        if teacher_id:
            planned_lessons_query = planned_lessons_query.where(LessonEvent.teacher_id == teacher_id)
        
        planned_result = await db.execute(planned_lessons_query)
        planned_lessons = planned_result.scalar() or 0
        
        # Факт = тільки COMPLETED уроки з минулого
        completed_lessons_query = select(func.count(LessonEvent.id))\
            .where(LessonEvent.status == LessonEventStatus.COMPLETED)\
            .where(LessonEvent.start_at < now)
        if start_dt:
            completed_lessons_query = completed_lessons_query.where(func.date(LessonEvent.start_at) >= start_dt)
        if end_dt:
            completed_lessons_query = completed_lessons_query.where(func.date(LessonEvent.start_at) <= end_dt)
        if club_id:
            completed_lessons_query = completed_lessons_query.where(LessonEvent.club_id == club_id)
        if teacher_id:
            completed_lessons_query = completed_lessons_query.where(LessonEvent.teacher_id == teacher_id)
        
        completed_result = await db.execute(completed_lessons_query)
        completed_lessons = completed_result.scalar() or 0
        
        lessons_completion_rate = round((completed_lessons / planned_lessons * 100), 2) if planned_lessons > 0 else 0
        
        # KPI 2: Цільова відвідуваність (85%)
        target_attendance = 85.0
        attendance_achievement = round((attendance_rate / target_attendance * 100), 2) if target_attendance > 0 else 0
        
        # KPI 3: Заповненість гуртків (середня кількість студентів vs максимум)
        # Припускаємо максимум 15 студентів на гурток
        avg_students_per_club = round(total_students / total_clubs, 2) if total_clubs > 0 else 0
        max_students_per_club = 15
        club_occupancy_rate = round((avg_students_per_club / max_students_per_club * 100), 2)
        
        kpi_metrics = {
            "lessons_plan": {
                "planned": planned_lessons,
                "completed": completed_lessons,
                "completion_rate": lessons_completion_rate
            },
            "attendance_target": {
                "target": target_attendance,
                "actual": attendance_rate,
                "achievement_rate": attendance_achievement
            },
            "club_occupancy": {
                "avg_students": avg_students_per_club,
                "max_students": max_students_per_club,
                "occupancy_rate": club_occupancy_rate
            }
        }
        
        # 6. КАЛЕНДАР АКТИВНОСТІ
        logger.info("📅 Building activity calendar...")
        calendar_query = select(
            func.date(LessonEvent.start_at).label('date'),
            func.count(LessonEvent.id).label('lessons_count')
        ).select_from(LessonEvent)\
         .where(LessonEvent.status == LessonEventStatus.COMPLETED)
        
        if start_dt:
            calendar_query = calendar_query.where(func.date(LessonEvent.start_at) >= start_dt)
        if end_dt:
            calendar_query = calendar_query.where(func.date(LessonEvent.start_at) <= end_dt)
        if club_id:
            calendar_query = calendar_query.where(LessonEvent.club_id == club_id)
        if teacher_id:
            calendar_query = calendar_query.where(LessonEvent.teacher_id == teacher_id)
        
        calendar_query = calendar_query.group_by(func.date(LessonEvent.start_at)).order_by(func.date(LessonEvent.start_at))
        calendar_result = await db.execute(calendar_query)
        
        activity_calendar = []
        for row in calendar_result:
            # Визначаємо рівень активності
            lessons = row.lessons_count
            if lessons >= 10:
                activity_level = "high"
            elif lessons >= 5:
                activity_level = "medium"
            else:
                activity_level = "low"
            
            activity_calendar.append({
                "date": str(row.date),
                "lessons_count": lessons,
                "activity_level": activity_level
            })
        
        logger.info(f"✅ All new metrics calculated successfully")
        
        # Компілюємо базові дані + нові метрики
        statistics_data = {
            "overview": {
                "total_students": total_students,
                "total_teachers": total_teachers,
                "total_clubs": total_clubs,
                "total_schedules": total_schedules,
                "filter_period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "club_id": club_id,
                    "teacher_id": teacher_id
                }
            },
            "clubs": clubs_stats,
            "teachers": teachers_stats,
            "top_students": top_students_data,
            "benefits": benefits_data,
            "financial": financial_stats,
            "attendance": {
                "total_records": total_attendance_records,
                "present_count": present_count,
                "absent_count": absent_count,
                "attendance_rate": attendance_rate,
                "weekday_stats": weekday_list
            },
            # НОВІ МЕТРИКИ
            "attendance_trends": attendance_trends,
            "peak_hours": {
                "hours": peak_hours_data,
                "peak_hour": peak_hour_info
            },
            "at_risk_students": at_risk_students,
            "alerts": alerts,
            "kpi_metrics": kpi_metrics,
            "activity_calendar": activity_calendar
        }
        
        logger.info(f"✅ All statistics compiled successfully (including new metrics)")
        
        return statistics_data
        
    except Exception as e:
        logger.error(f"Error fetching advanced statistics: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching advanced statistics: {e}")


