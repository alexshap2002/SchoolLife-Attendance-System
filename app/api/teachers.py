"""Teachers API endpoints."""

from datetime import datetime
from typing import List, Optional
import io
import pandas as pd

from fastapi import APIRouter, HTTPException, status, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

from app.api.dependencies import AdminUser, DbSession
from app.models import Teacher, Schedule, ConductedLesson, LessonEvent, PayRate, Payroll, BotSchedule

router = APIRouter(prefix="/teachers", tags=["teachers"])


class TeacherCreate(BaseModel):
    """Teacher creation model."""

    full_name: str
    tg_username: Optional[str] = None
    tg_chat_id: Optional[int] = None
    active: bool = True


class TeacherUpdate(BaseModel):
    """Teacher update model."""

    full_name: Optional[str] = None
    tg_username: Optional[str] = None
    tg_chat_id: Optional[int] = None
    active: Optional[bool] = None


class TeacherResponse(BaseModel):
    """Teacher response model."""

    id: int
    full_name: str
    tg_chat_id: Optional[int]
    tg_username: Optional[str]
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TeacherResponse])
async def get_teachers(
    db: DbSession,
    # admin: AdminUser,  # Тимчасово відключено для тестування
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
) -> List[Teacher]:
    """Get all teachers (by default only active)."""
    query = select(Teacher).options(selectinload(Teacher.schedules))
    
    # За замовчуванням показуємо тільки активних вчителів
    if not include_inactive:
        query = query.where(Teacher.active == True)
        
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    teacher_data: TeacherCreate,
    db: DbSession,
    admin: AdminUser,
) -> Teacher:
    """Create new teacher with automatic default pay rate."""
    # Створюємо вчителя
    teacher = Teacher(**teacher_data.model_dump())
    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)
    
    # 💰 АВТОМАТИЧНО СТВОРЮЄМО БАЗОВИЙ ТАРИФ 200₴ ЗА УРОК
    from app.models.pay_rate import PayRate, PayRateType
    from decimal import Decimal
    from datetime import date
    import logging
    
    logger = logging.getLogger(__name__)
    
    default_pay_rate = PayRate(
        teacher_id=teacher.id,
        rate_type=PayRateType.PER_LESSON,
        amount_decimal=Decimal("200.00"),
        active_from=date.today(),
        active_to=None  # Безстроковий
    )
    
    db.add(default_pay_rate)
    await db.commit()
    
    logger.info(f"💰 Created default pay rate 200₴ per lesson for teacher {teacher.full_name} (ID: {teacher.id})")
    
    # 📝 AUDIT LOG: Створення вчителя
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
        logger.error(f"❌ AUDIT LOG ERROR (teacher CREATE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return teacher


# === EXCEL IMPORT FOR TEACHERS ===

class ImportTeachersResponse(BaseModel):
    """Response model for teachers import."""
    
    created_count: int
    skipped_count: int
    errors: List[str]


@router.post("/import", response_model=ImportTeachersResponse)
async def import_teachers(
    db: DbSession,
    file: UploadFile = File(...),
    skip_duplicates: bool = True,
    # admin: AdminUser,  # Поки що відключаємо авторизацію для тестування
) -> ImportTeachersResponse:
    """Import teachers from Excel file."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be Excel format (.xlsx or .xls)"
        )
    
    try:
        # Читаємо Excel файл
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name='Вчителі')
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        # Мапінг колонок для вчителів
        column_mapping = {
            "Повне ім'я *": "full_name",
            "Telegram Username": "tg_username", 
            "Telegram Chat ID": "tg_chat_id",
            "Активний (так/ні)": "active"
        }
        
        for index, row in df.iterrows():
            try:
                # Перевіряємо обов'язкові поля
                if pd.isna(row.get("Повне ім'я *")):
                    errors.append(f"Рядок {index + 2}: Повне ім'я є обов'язковим")
                    continue
                
                full_name = str(row["Повне ім'я *"]).strip()
                
                # Перевіряємо дублікати
                if skip_duplicates:
                    result = await db.execute(
                        select(Teacher).where(
                            Teacher.full_name == full_name
                        )
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        skipped_count += 1
                        continue
                
                # Створюємо дані для вчителя
                teacher_data = {
                    "full_name": full_name
                }
                
                # Додаємо опціональні поля
                for excel_col, db_field in column_mapping.items():
                    if excel_col == "Повне ім'я *":
                        continue
                        
                    value = row.get(excel_col)
                    if not pd.isna(value):
                        if db_field == "tg_chat_id":
                            # Обробляємо Chat ID як число
                            try:
                                teacher_data[db_field] = int(value) if value else None
                            except (ValueError, TypeError):
                                errors.append(f"Рядок {index + 2}: Неправильний формат Chat ID")
                                continue
                        elif db_field == "active":
                            # Обробляємо булеве поле активності
                            if isinstance(value, str):
                                value_lower = value.lower().strip()
                                teacher_data[db_field] = value_lower in ["так", "yes", "true", "1", "+"]
                            else:
                                teacher_data[db_field] = bool(value)
                        elif db_field == "tg_username":
                            # Обробляємо username (прибираємо @ якщо є)
                            username = str(value).strip()
                            if username.startswith('@'):
                                username = username[1:]
                            teacher_data[db_field] = username if username else None
                        else:
                            teacher_data[db_field] = str(value).strip() if str(value).strip() else None
                
                # Встановлюємо значення за замовчуванням
                if "active" not in teacher_data:
                    teacher_data["active"] = True
                
                # Створюємо вчителя
                teacher = Teacher(**teacher_data)
                db.add(teacher)
                created_count += 1
                
            except Exception as e:
                errors.append(f"Рядок {index + 2}: Помилка обробки - {str(e)}")
                continue
        
        # Зберігаємо зміни
        await db.commit()
        
        return ImportTeachersResponse(
            created_count=created_count,
            skipped_count=skipped_count,
            errors=errors
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing Excel file: {str(e)}"
        )


@router.get("/template")
async def download_teachers_template():
    """Download Excel template for teachers import."""
    try:
        # Створюємо DataFrame з шаблоном
        template_data = {
            "Повне ім'я *": [
                "Іван Петренко",
                "Марія Коваленко", 
                "Олександр Шевченко"
            ],
            "Telegram Username": [
                "ivan_teacher",
                "maria_teacher",
                "alex_teacher"  
            ],
            "Telegram Chat ID": [
                "123456789",
                "987654321",
                "555666777"
            ],
            "Активний (так/ні)": [
                "так",
                "так", 
                "ні"
            ]
        }
        
        df = pd.DataFrame(template_data)
        
        # Створюємо Excel файл в пам'яті
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Вчителі', index=False)
        
        excel_buffer.seek(0)
        
        from fastapi.responses import StreamingResponse
        
        return StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=teachers_template.xlsx"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating template: {str(e)}"
        )


# === CRUD OPERATIONS ===

@router.get("/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(
    teacher_id: int,
    db: DbSession,
    admin: AdminUser,
) -> Teacher:
    """Get teacher by ID."""
    result = await db.execute(
        select(Teacher)
        .options(selectinload(Teacher.schedules))
        .where(Teacher.id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    return teacher


@router.put("/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: int,
    teacher_data: TeacherUpdate,
    db: DbSession,
    admin: AdminUser,
) -> Teacher:
    """Update teacher."""
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    update_data = teacher_data.model_dump(exclude_unset=True)
    for field in update_data.keys():
        old_values[field] = getattr(teacher, field, None)
    
    # Update fields
    for field, value in update_data.items():
        setattr(teacher, field, value)
    
    await db.commit()
    await db.refresh(teacher)
    
    # 📝 AUDIT LOG: Оновлення вчителя
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
        pass
    
    return teacher


@router.post("/{teacher_id}/deactivate", response_model=dict)
async def deactivate_teacher(
    teacher_id: int,
    db: DbSession,
) -> dict:
    """Deactivate teacher (soft delete) - простіший підхід."""
    
    # Перевіряємо чи існує вчитель
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    if not teacher.active:
        return {"message": f"Вчитель '{teacher.full_name}' вже деактивований", "success": True}
    
    try:
        # Просто деактивуємо вчителя
        teacher.active = False
        
        # Деактивуємо всі його розклади
        await db.execute(
            update(Schedule)
            .where(Schedule.teacher_id == teacher_id)
            .values(active=False)
        )
        
        await db.commit()
        
        # 📝 AUDIT LOG: Деактивація вчителя
        try:
            from app.services.audit_service import log_audit
            await log_audit(
                db=db,
                action_type="UPDATE",
                entity_type="teacher",
                entity_id=teacher.id,
                entity_name=teacher.full_name,
                description=f"Деактивовано вчителя: {teacher.full_name}",
                user_name="Адміністратор",
                changes={"active": {"before": True, "after": False}}
            )
        except Exception as e:
            pass
        
        return {"message": f"Вчитель '{teacher.full_name}' успішно деактивований", "success": True}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deactivating teacher: {str(e)}"
        )

@router.delete("/{teacher_id}", status_code=status.HTTP_200_OK)
async def delete_teacher(
    teacher_id: int,
    db: DbSession,
    force: bool = Query(False, description="Force delete with all dependencies"),
    # admin: AdminUser,  # Тимчасово відключено для тестування
) -> dict:
    """Delete teacher with smart cascade handling."""
    print(f"🎯 DELETE TEACHER CALLED: id={teacher_id}, force={force}")
    from app.models import LessonEvent, Payroll, ConductedLesson, PayRate
    from sqlalchemy import func
    
    # Перевіряємо чи існує вчитель
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    # Перевіряємо залежності
    schedules_count = await db.execute(
        select(func.count(Schedule.id)).where(Schedule.teacher_id == teacher_id)
    )
    schedules_count = schedules_count.scalar() or 0
    
    lesson_events_count = await db.execute(
        select(func.count(LessonEvent.id)).where(LessonEvent.teacher_id == teacher_id)
    )
    lesson_events_count = lesson_events_count.scalar() or 0
    
    payroll_count = await db.execute(
        select(func.count(Payroll.id)).where(Payroll.teacher_id == teacher_id)
    )
    payroll_count = payroll_count.scalar() or 0
    
    conducted_count = await db.execute(
        select(func.count(ConductedLesson.id)).where(ConductedLesson.teacher_id == teacher_id)
    )
    conducted_count = conducted_count.scalar() or 0
    
    # ❗️ ВАЖЛИВО: Додаємо перевірку PayRate (раніше відсутня!)
    pay_rates_count = await db.execute(
        select(func.count(PayRate.id)).where(PayRate.teacher_id == teacher_id)
    )
    pay_rates_count = pay_rates_count.scalar() or 0
    
    has_dependencies = (schedules_count > 0 or lesson_events_count > 0 or payroll_count > 0 or 
                       conducted_count > 0 or pay_rates_count > 0)
    
    # НОВА ЛОГІКА: За замовчуванням деактивуємо, з force - видаляємо
    if has_dependencies and not force:
        # Безпечна деактивація при наявності залежностей
        teacher.active = False
        
        # Деактивуємо всі його розклади
        await db.execute(
            update(Schedule)
            .where(Schedule.teacher_id == teacher_id)
            .values(active=False)
        )
        
        # 📝 AUDIT LOG: Деактивація вчителя (через DELETE з залежностями)
        try:
            from app.services.audit_service import log_audit
            await log_audit(
                db=db,
                action_type="UPDATE",
                entity_type="teacher",
                entity_id=teacher.id,
                entity_name=teacher.full_name,
                description=f"Деактивовано вчителя: {teacher.full_name} (через видалення з залежностями)",
                user_name="Адміністратор",
                changes={"active": {"before": True, "after": False}, "reason": "delete_with_dependencies"}
            )
        except Exception as e:
            pass
        
        await db.commit()
        
        return {
            "success": True,
            "action": "deactivated",
            "message": f"Вчитель '{teacher.full_name}' деактивовано через наявність залежностей",
            "teacher": teacher.full_name,
            "dependencies": {
                "schedules": schedules_count,
                "lesson_events": lesson_events_count,
                "payroll_records": payroll_count,
                "conducted_lessons": conducted_count,
                "pay_rates": pay_rates_count
            },
            "note": "Для повного видалення використайте force=true"
        }
    
    try:
        if force and has_dependencies:
            # 🔥 КАСКАДНЕ ВИДАЛЕННЯ З ПОПЕРЕДЖЕННЯМ
            print(f"🚨 FORCE DELETE teacher {teacher_id}: {teacher.full_name}")
            print(f"📊 Dependencies: schedules={schedules_count}, events={lesson_events_count}, payroll={payroll_count}, pay_rates={pay_rates_count}, conducted={conducted_count}")
            
            # 1. Видаляємо bot schedules
            await db.execute(
                delete(BotSchedule).where(BotSchedule.schedule_id.in_(
                    select(Schedule.id).where(Schedule.teacher_id == teacher_id)
                ))
            )
            
            # 2. Видаляємо payroll записи
            await db.execute(
                delete(Payroll).where(Payroll.teacher_id == teacher_id)
            )
            
            # 3. Видаляємо pay rates
            await db.execute(
                delete(PayRate).where(PayRate.teacher_id == teacher_id)
            )
            
            # 4. Видаляємо conducted lessons
            await db.execute(
                delete(ConductedLesson).where(ConductedLesson.teacher_id == teacher_id)
            )
            
            # 5. Видаляємо lesson events (це також видалить attendance через CASCADE)
            await db.execute(
                delete(LessonEvent).where(LessonEvent.teacher_id == teacher_id)
            )
            
            # 6. Видаляємо schedules
            await db.execute(
                delete(Schedule).where(Schedule.teacher_id == teacher_id)
            )
            
            # 7. Видаляємо вчителя (через SQL, не ORM щоб уникнути cascade конфліктів)
            teacher_name = teacher.full_name  # Зберігаємо перед видаленням
            await db.execute(
                delete(Teacher).where(Teacher.id == teacher_id)
            )
            
            # 📝 AUDIT LOG: FORCE DELETE вчителя
            try:
                from app.services.audit_service import log_audit
                await log_audit(
                    db=db,
                    action_type="DELETE",
                    entity_type="teacher",
                    entity_id=teacher_id,
                    entity_name=teacher_name,
                    description=f"ПОВНЕ ВИДАЛЕННЯ вчителя: {teacher_name} (force=true, каскадно видалено {schedules_count + lesson_events_count + payroll_count + conducted_count + pay_rates_count} записів)",
                    user_name="Адміністратор",
                    changes={"deleted": {
                        "teacher": teacher_name,
                        "schedules": schedules_count,
                        "lesson_events": lesson_events_count,
                        "payroll": payroll_count,
                        "conducted_lessons": conducted_count,
                        "pay_rates": pay_rates_count
                    }}
                )
            except Exception as e:
                pass
            
            await db.commit()
            
            return {
                "success": True,
                "message": f"Вчитель '{teacher_name}' та всі пов'язані дані видалено",
                "deleted": {
                    "teacher": teacher_name,
                    "schedules": schedules_count,
                    "lesson_events": lesson_events_count,
                    "payroll_records": payroll_count,
                    "conducted_lessons": conducted_count,
                    "pay_rates": pay_rates_count
                }
            }
        else:
            # Простe видалення (без залежностей, через SQL)
            await db.execute(
                delete(Teacher).where(Teacher.id == teacher_id)
            )
            await db.commit()
            
            return {
                "success": True,
                "message": f"Вчитель '{teacher.full_name}' успішно видалено",
                "deleted": {
                    "teacher": teacher.full_name
                }
            }
            
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting teacher: {str(e)}"
        )


@router.post("/{teacher_id}/toggle-active", response_model=dict)
async def toggle_teacher_active(
    teacher_id: int,
    db: DbSession,
) -> dict:
    """Toggle teacher active status."""
    
    # Перевіряємо чи існує вчитель
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    try:
        # Змінюємо статус
        new_status = not teacher.active
        teacher.active = new_status
        
        # Якщо деактивуємо - деактивуємо також розклади
        if not new_status:
            await db.execute(
                update(Schedule)
                .where(Schedule.teacher_id == teacher_id)
                .values(active=False)
            )
        
        await db.commit()
        
        action = "активовано" if new_status else "деактивовано"
        
        return {
            "success": True,
            "message": f"Вчитель '{teacher.full_name}' {action}",
            "teacher": {
                "id": teacher.id,
                "full_name": teacher.full_name,
                "active": new_status
            }
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling teacher status: {str(e)}"
        )


@router.get("/export/excel")
async def export_teachers_excel(
    db: DbSession,
    # admin: AdminUser,  # Поки що відключаємо авторизацію для тестування
) -> StreamingResponse:
    """Export all teachers data to Excel."""
    
    try:
        # Отримуємо всіх вчителів з пов'язаними даними
        result = await db.execute(
            select(Teacher)
            .options(
                selectinload(Teacher.schedules).selectinload(Schedule.club),
                selectinload(Teacher.conducted_lessons).selectinload(ConductedLesson.club)
            )
            .order_by(Teacher.full_name)
        )
        teachers = result.scalars().all()
        
        if not teachers:
            raise HTTPException(status_code=404, detail="No teachers found")
        
        # Підготуємо дані для Excel
        teachers_data = []
        for teacher in teachers:
            # Рахуємо статистику
            total_lessons = len(teacher.conducted_lessons)
            total_present = sum(lesson.present_students for lesson in teacher.conducted_lessons)
            active_clubs = len(set(schedule.club.name for schedule in teacher.schedules if schedule.active))
            
            teachers_data.append({
                # === ОСНОВНА ІНФОРМАЦІЯ ===
                "Повне ім'я": teacher.full_name,
                "Активний": "Так" if teacher.active else "Ні",
                
                # === TELEGRAM ===
                "Telegram Username": f"@{teacher.tg_username}" if teacher.tg_username else "—",
                "Telegram Chat ID": teacher.tg_chat_id or "—",
                
                # === СТАТИСТИКА РОБОТИ ===
                "Активних гуртків": active_clubs,
                "Проведено уроків": total_lessons,
                "Всього учнів навчено": total_present,
                "Середня відвідуваність": f"{total_present / total_lessons:.1f}" if total_lessons > 0 else "0",
                
                # === СИСТЕМНА ІНФОРМАЦІЯ ===
                "Дата реєстрації": teacher.created_at.strftime("%d.%m.%Y %H:%M") if teacher.created_at else "—"
            })
        
        # Створюємо DataFrame
        df = pd.DataFrame(teachers_data)
        
        # Створюємо Excel файл в пам'яті
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Вчителі', index=False)
            
            # Налаштовуємо ширину колонок
            worksheet = writer.sheets['Вчителі']
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
            
            # Додаємо лист зі статистикою
            summary_data = {
                'Статистика': [
                    'Загальна кількість вчителів',
                    'Активних вчителів',
                    'Вчителів з Telegram',
                    'Загалом проведено уроків',
                    'Загалом навчено учнів'
                ],
                'Значення': [
                    len(teachers),
                    len([t for t in teachers if t.active]),
                    len([t for t in teachers if t.tg_username]),
                    sum(len(t.conducted_lessons) for t in teachers),
                    sum(sum(lesson.present_students for lesson in t.conducted_lessons) for t in teachers)
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Статистика', index=False)
        
        output.seek(0)
        
        # Генеруємо ім'я файлу з поточною датою
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"teachers_export_{today}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting teachers: {str(e)}"
        )
