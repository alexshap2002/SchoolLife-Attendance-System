"""Schedules API endpoints."""

import logging
from datetime import datetime, time
from typing import List, Optional
import io
import pandas as pd

from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

from app.api.dependencies import AdminUser, DbSession
from app.models import Schedule, Club, Teacher, BotSchedule

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    """Schedule creation model."""

    club_id: int
    weekday: int  # 1=Monday, 2=Tuesday, ..., 5=Friday
    start_time: time
    teacher_id: int
    active: bool = True


class ScheduleUpdate(BaseModel):
    """Schedule update model."""

    club_id: Optional[int] = None
    weekday: Optional[int] = None
    start_time: Optional[time] = None
    teacher_id: Optional[int] = None
    active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Schedule response model."""

    id: int
    club_id: int
    weekday: int
    start_time: time
    teacher_id: int
    active: bool
    created_at: datetime
    
    # Related objects
    club_name: Optional[str] = None
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ScheduleResponse])
async def get_schedules(
    db: DbSession,
    admin: AdminUser,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = Query(False, description="Include deactivated schedules"),
) -> List[Schedule]:
    """Get all schedules."""
    query = select(Schedule).options(
        selectinload(Schedule.club),
        selectinload(Schedule.teacher),
    )
    
    # 🔍 Фільтр активних розкладів за замовчуванням
    if not include_inactive:
        query = query.where(Schedule.active == True)
    
    result = await db.execute(
        query
        .offset(skip)
        .limit(limit)
        .order_by(Schedule.weekday, Schedule.start_time)
    )
    schedules = result.scalars().all()
    
    # Add related data
    for schedule in schedules:
        schedule.club_name = schedule.club.name if schedule.club else None
        schedule.teacher_name = schedule.teacher.full_name if schedule.teacher else None
    
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: DbSession,
    admin: AdminUser,
) -> Schedule:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    return schedule


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: DbSession,
    # admin: AdminUser,  # Временно отключено для веб-интерфейса
) -> Schedule:
    """Create new schedule."""
    schedule = Schedule(**schedule_data.model_dump())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    
    # 🤖 АВТОМАТИЧНО створюємо bot_schedule з нагадуванням через 5 хвилин після початку
    from app.models import BotSchedule
    from datetime import timedelta
    
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
    await db.commit()
    
    # 📝 AUDIT LOG: Створення розкладу
    try:
        from app.services.audit_service import log_audit
        # Завантажуємо зв'язки для відображення
        await db.refresh(schedule, ['club', 'teacher'])
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="schedule",
            entity_id=schedule.id,
            entity_name=f"{schedule.club.name if schedule.club else '(гурток не вказаний)'} - {schedule.weekday}",
            description=f"Створено розклад: {schedule.club.name if schedule.club else '(гурток не вказаний)'}, викладач: {schedule.teacher.full_name if schedule.teacher else '(викладач не призначений)'}, день: {schedule.weekday}",
            user_name="Адміністратор",
            changes={"club_id": schedule.club_id, "teacher_id": schedule.teacher_id, "weekday": schedule.weekday}
        )
    except Exception as e:
        pass
    
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: DbSession,
    # admin: AdminUser,  # Тимчасово відключено для тестування
) -> Schedule:
    """Update schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Update fields
    update_data = schedule_data.model_dump(exclude_unset=True)
    
    # 🔄 КАСКАДНЕ ОНОВЛЕННЯ: Якщо змінюється вчитель - оновити майбутні lesson_events
    if 'teacher_id' in update_data and update_data['teacher_id'] != schedule.teacher_id:
        from app.models import LessonEvent, Teacher, LessonEventStatus
        from datetime import date
        
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New teacher not found"
            )
        
        logger.info(f"🔍 New teacher found: {new_teacher.full_name} (chat_id: {new_teacher.tg_chat_id})")
        
        # Спочатку перевіряємо скільки майбутніх events
        count_result = await db.execute(
            select(LessonEvent.id)
            .where(
                LessonEvent.schedule_id == schedule_id,
                LessonEvent.date >= date.today(),
                LessonEvent.status == LessonEventStatus.PLANNED
            )
        )
        events_to_update = count_result.fetchall()
        logger.info(f"📊 Found {len(events_to_update)} future events to update")
        
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
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    for field in update_data.keys():
        old_values[field] = getattr(schedule, field, None)
    
    for field, value in update_data.items():
        setattr(schedule, field, value)
    
    await db.commit()
    await db.refresh(schedule, ['club', 'teacher'])
    
    # 📝 AUDIT LOG: Оновлення розкладу
    try:
        from app.services.audit_service import log_audit
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {v}" for k, v in update_data.items() if old_values.get(k) != v])
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="schedule",
            entity_id=schedule.id,
            entity_name=f"{schedule.club.name if schedule.club else '(гурток не вказаний)'} - {schedule.weekday}",
            description=f"Оновлено розклад: {schedule.club.name if schedule.club else '(гурток не вказаний)'}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": update_data}
        )
    except Exception as e:
        pass
    
    return schedule


@router.post("/{schedule_id}/deactivate", response_model=dict)
async def deactivate_schedule(
    schedule_id: int,
    db: DbSession,
    # admin: AdminUser,  # Тимчасово відключено для тестування
) -> dict:
    """Delete schedule with proper cascade handling."""
    from app.models import BotSchedule, LessonEvent, ScheduleEnrollment
    
    # Перевіряємо чи існує розклад
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
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
        
        # 🛡️ ЗАВЖДИ ДЕАКТИВУЄМО (безпечно зберігаємо історію)
        schedule.active = False
        
        # Скасовуємо майбутні lesson_events 
        from datetime import date
        await db.execute(
            update(LessonEvent)
            .where(
                LessonEvent.schedule_id == schedule_id,
                LessonEvent.date >= date.today(),
                LessonEvent.status == 'PLANNED'
            )
            .values(status='CANCELLED')
        )
        
        # 📝 AUDIT LOG: Деактивація розкладу
        try:
            from app.services.audit_service import log_audit
            club_name = schedule.club.name if schedule.club else "(гурток не вказаний)"
            teacher_name = schedule.teacher.full_name if schedule.teacher else "(викладач не призначений)"
            schedule_time = f"{schedule.weekday} {schedule.start_time.strftime('%H:%M')}"
            
            await log_audit(
                db=db,
                action_type="DELETE",
                entity_type="schedule",
                entity_id=schedule_id,
                entity_name=f"{club_name} - {schedule_time}",
                description=f"Деактивовано розклад: {club_name}, викладач: {teacher_name}, день: {schedule_time}. Історичні дані збережено.",
                user_name="Адміністратор",
                changes={"action": "deactivated", "club": club_name, "teacher": teacher_name, "schedule": schedule_time}
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (schedule DEACTIVATE): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        
        logger.info(f"✅ Schedule {schedule_id} safely deactivated (historical data preserved)")
        
        return {
            "success": True,
            "message": f"Розклад деактивовано. Історичні дані збережено.",
            "action": "deactivated",
            "schedule_name": f"{schedule.club.name if schedule.club else 'N/A'}"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting schedule: {str(e)}"
        )


@router.post("/{schedule_id}/reactivate", response_model=dict)
async def reactivate_schedule(
    schedule_id: int,
    db: DbSession,
    # admin: AdminUser,  # Тимчасово відключено для тестування
) -> dict:
    """Reactivate deactivated schedule."""
    
    # Перевіряємо чи існує розклад
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    if schedule.active:
        return {
            "success": True,
            "message": "Розклад вже активний",
            "action": "already_active"
        }
    
    try:
        # Реактивуємо розклад
        schedule.active = True
        
        # Реактивуємо скасовані майбутні lesson_events
        from app.models import LessonEvent, LessonEventStatus  
        from datetime import date
        
        await db.execute(
            update(LessonEvent)
            .where(
                LessonEvent.schedule_id == schedule_id,
                LessonEvent.date >= date.today(),
                LessonEvent.status == LessonEventStatus.CANCELLED
            )
            .values(status=LessonEventStatus.PLANNED)
        )
        
        # 📝 AUDIT LOG: Реактивація розкладу
        try:
            from app.services.audit_service import log_audit
            club_name = schedule.club.name if schedule.club else "(гурток не вказаний)"
            teacher_name = schedule.teacher.full_name if schedule.teacher else "(викладач не призначений)"
            schedule_time = f"{schedule.weekday} {schedule.start_time.strftime('%H:%M')}"
            
            await log_audit(
                db=db,
                action_type="UPDATE",
                entity_type="schedule",
                entity_id=schedule_id,
                entity_name=f"{club_name} - {schedule_time}",
                description=f"Реактивовано розклад: {club_name}, викладач: {teacher_name}, день: {schedule_time}. Відновлено майбутні заняття.",
                user_name="Адміністратор",
                changes={"action": "reactivated", "club": club_name, "teacher": teacher_name, "schedule": schedule_time, "active": {"before": False, "after": True}}
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (schedule REACTIVATE): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        
        logger.info(f"✅ Schedule {schedule_id} reactivated with future events restored")
        
        return {
            "success": True,
            "message": f"Розклад '{schedule.club.name if schedule.club else 'N/A'}' реактивовано.",
            "action": "reactivated"
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error reactivating schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reactivating schedule: {str(e)}"
        )


@router.get("/export/excel")
async def export_schedules_excel(
    db: DbSession,
    # admin: AdminUser,  # Поки що відключаємо авторизацію для тестування
) -> StreamingResponse:
    """Export all schedules data to Excel."""
    
    try:
        # Отримуємо всі розклади з пов'язаними даними
        result = await db.execute(
            select(Schedule)
            .options(
                selectinload(Schedule.club),
                selectinload(Schedule.teacher),
                selectinload(Schedule.bot_schedule)
            )
            .order_by(Schedule.club_id, Schedule.weekday, Schedule.start_time)
        )
        schedules = result.scalars().all()
        
        if not schedules:
            raise HTTPException(status_code=404, detail="No schedules found")
        
        # Мапінг днів тижня
        WEEKDAYS = {
            0: 'Понеділок',
            1: 'Вівторок', 
            2: 'Середа',
            3: 'Четвер',
            4: 'П\'ятниця',
            5: 'Субота',
            6: 'Неділя'
        }
        
        # Підготуємо дані для Excel
        schedules_data = []
        for schedule in schedules:
            schedules_data.append({
                # === ОСНОВНА ІНФОРМАЦІЯ ===
                "Гурток": schedule.club.name if schedule.club else "—",
                "Вчитель": schedule.teacher.full_name if schedule.teacher else "—",
                "День тижня": WEEKDAYS.get(schedule.weekday, "Невідомо"),
                "Час початку": schedule.start_time.strftime("%H:%M") if schedule.start_time else "—",
                
                # === СТАТУС ===
                "Активний": "Так" if schedule.active else "Ні",
                "Автоматичні повідомлення": "Так" if schedule.bot_schedule else "Ні",
                
                # === СИСТЕМНА ІНФОРМАЦІЯ ===
                "Дата створення": schedule.created_at.strftime("%d.%m.%Y %H:%M") if schedule.created_at else "—"
            })
        
        # Створюємо DataFrame
        df = pd.DataFrame(schedules_data)
        
        # Створюємо Excel файл в пам'яті
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Розклади', index=False)
            
            # Налаштовуємо ширину колонок
            worksheet = writer.sheets['Розклади']
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
            
            # Додаємо лист зі статистикою по днях
            day_stats = {}
            for schedule in schedules:
                day_name = WEEKDAYS.get(schedule.weekday, "Невідомо")
                if day_name not in day_stats:
                    day_stats[day_name] = {'total': 0, 'active': 0}
                day_stats[day_name]['total'] += 1
                if schedule.active:
                    day_stats[day_name]['active'] += 1
            
            stats_data = {
                'День тижня': list(day_stats.keys()),
                'Загалом розкладів': [stats['total'] for stats in day_stats.values()],
                'Активних розкладів': [stats['active'] for stats in day_stats.values()]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Статистика по днях', index=False)
            
            # Загальна статистика
            summary_data = {
                'Статистика': [
                    'Загальна кількість розкладів',
                    'Активних розкладів',
                    'З автоматичними повідомленнями',
                    'Унікальних гуртків',
                    'Унікальних вчителів'
                ],
                'Значення': [
                    len(schedules),
                    len([s for s in schedules if s.active]),
                    len([s for s in schedules if s.bot_schedule]),
                    len(set(s.club_id for s in schedules if s.club_id)),
                    len(set(s.teacher_id for s in schedules if s.teacher_id))
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Загальна статистика', index=False)
        
        output.seek(0)
        
        # Генеруємо ім'я файлу з поточною датою
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"schedules_export_{today}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting schedules: {str(e)}"
        )
