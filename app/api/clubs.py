"""Clubs API endpoints."""

from datetime import datetime
from typing import List, Optional
import io
import pandas as pd
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

from app.api.dependencies import AdminUser, DbSession
from app.models import Club, Enrollment, Schedule, ConductedLesson

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clubs", tags=["clubs"])


class ClubCreate(BaseModel):
    """Club creation model."""

    name: str
    duration_min: int = 60
    location: str


class ClubUpdate(BaseModel):
    """Club update model."""

    name: Optional[str] = None
    duration_min: Optional[int] = None
    location: Optional[str] = None


class ClubResponse(BaseModel):
    """Club response model."""

    id: int
    name: str
    duration_min: int
    location: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ClubResponse])
async def get_clubs(
    db: DbSession,
    admin: AdminUser,
    skip: int = 0,
    limit: int = 100,
) -> List[Club]:
    """Get all clubs."""
    result = await db.execute(
        select(Club)
        .options(selectinload(Club.schedules))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{club_id}", response_model=ClubResponse)
async def get_club(
    club_id: int,
    db: DbSession,
    admin: AdminUser,
) -> Club:
    """Get club by ID."""
    result = await db.execute(
        select(Club)
        .options(selectinload(Club.schedules))
        .where(Club.id == club_id)
    )
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )
    return club


@router.post("/", response_model=ClubResponse, status_code=status.HTTP_201_CREATED)
async def create_club(
    club_data: ClubCreate,
    db: DbSession,
    admin: AdminUser,
) -> Club:
    """Create new club."""
    club = Club(**club_data.model_dump())
    db.add(club)
    await db.flush()  # Flush щоб отримати ID
    
    # 📝 AUDIT LOG: Створення гуртка (ПЕРЕД commit!)
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="club",
            entity_id=club.id,
            entity_name=club.name,
            description=f"Створено новий гурток: {club.name}",
            user_name="Адміністратор",
            changes={"after": {"name": club.name, "description": club.description}}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (club CREATE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(club)
    return club


@router.put("/{club_id}", response_model=ClubResponse)
async def update_club(
    club_id: int,
    club_data: ClubUpdate,
    db: DbSession,
    admin: AdminUser,
) -> Club:
    """Update club."""
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    update_data = club_data.model_dump(exclude_unset=True)
    for field in update_data.keys():
        old_values[field] = getattr(club, field, None)
    
    # Update fields
    for field, value in update_data.items():
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
            description=f"Оновлено гурток: {club.name}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": update_data}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (club UPDATE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(club)
    return club


@router.delete("/{club_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_club(
    club_id: int,
    db: DbSession,
    # admin: AdminUser,  # Тимчасово відключено для тестування
) -> None:
    """Delete club with proper cascade handling."""
    from app.models import LessonEvent, BotSchedule, Schedule
    
    # Перевіряємо чи існує гурток
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )
    
    # Зберігаємо назву для аудиту перед видаленням
    club_name = club.name
    
    try:
        # 1. Видаляємо enrollments
        await db.execute(
            delete(Enrollment).where(Enrollment.club_id == club_id)
        )
        
        # 2. Видаляємо conducted lessons
        await db.execute(
            delete(ConductedLesson).where(ConductedLesson.club_id == club_id)
        )
        
        # 3. Видаляємо lesson events
        await db.execute(
            delete(LessonEvent).where(LessonEvent.club_id == club_id)
        )
        
        # 4. Видаляємо bot schedules для цього клубу
        # Спочатку знаходимо schedules цього клубу
        schedule_result = await db.execute(select(Schedule.id).where(Schedule.club_id == club_id))
        schedule_ids = [row[0] for row in schedule_result.all()]
        
        if schedule_ids:
            await db.execute(
                delete(BotSchedule).where(BotSchedule.schedule_id.in_(schedule_ids))
            )
        
        # 5. Деактивуємо schedules замість видалення (безпечніше)
        await db.execute(
            update(Schedule)
            .where(Schedule.club_id == club_id)
            .values(active=False)
        )
        
        # 6. Тепер можемо безпечно видалити гурток
        await db.delete(club)
        
        # 📝 AUDIT LOG: Видалення гуртка (ПЕРЕД commit!)
        try:
            from app.services.audit_service import log_audit
            await log_audit(
                db=db,
                action_type="DELETE",
                entity_type="club",
                entity_id=club_id,
                entity_name=club_name,
                description=f"Видалено гурток: {club_name}",
                user_name="Адміністратор",
                changes={"deleted": {"id": club_id, "name": club_name}}
            )
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (club DELETE): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting club: {str(e)}"
        )


@router.get("/export/excel")
async def export_clubs_excel(
    db: DbSession,
    # admin: AdminUser,  # Поки що відключаємо авторизацію для тестування
) -> StreamingResponse:
    """Export all clubs data to Excel."""
    
    try:
        # Отримуємо всі гуртки з пов'язаними даними
        result = await db.execute(
            select(Club)
            .options(
                selectinload(Club.enrollments).selectinload(Enrollment.student),
                selectinload(Club.schedules),
                selectinload(Club.conducted_lessons)
            )
            .order_by(Club.name)
        )
        clubs = result.scalars().all()
        
        if not clubs:
            raise HTTPException(status_code=404, detail="No clubs found")
        
        # Підготуємо дані для Excel
        clubs_data = []
        for club in clubs:
            # Рахуємо статистику
            total_students = len(club.enrollments)
            active_schedules = len([s for s in club.schedules if s.active])
            total_lessons = len(club.conducted_lessons)
            total_attendance = sum(lesson.present_students for lesson in club.conducted_lessons)
            avg_attendance = (total_attendance / total_lessons) if total_lessons > 0 else 0
            
            clubs_data.append({
                # === ОСНОВНА ІНФОРМАЦІЯ ===
                "Назва гуртка": club.name,
                
                # === СТАТИСТИКА ===
                "Кількість учнів": total_students,
                "Активних розкладів": active_schedules,
                "Проведено занять": total_lessons,
                "Загальна відвідуваність": total_attendance,
                "Середня відвідуваність": f"{avg_attendance:.1f}",
                
                # === СИСТЕМНА ІНФОРМАЦІЯ ===
                "Дата створення": club.created_at.strftime("%d.%m.%Y %H:%M") if club.created_at else "—"
            })
        
        # Створюємо DataFrame
        df = pd.DataFrame(clubs_data)
        
        # Створюємо Excel файл в пам'яті
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Гуртки', index=False)
            
            # Налаштовуємо ширину колонок
            worksheet = writer.sheets['Гуртки']
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
                    'Загальна кількість гуртків',
                    'Гуртки з учнями',
                    'Загалом учнів записано',
                    'Загалом проведено занять',
                    'Загальна відвідуваність'
                ],
                'Значення': [
                    len(clubs),
                    len([c for c in clubs if c.enrollments]),
                    sum(len(c.enrollments) for c in clubs),
                    sum(len(c.conducted_lessons) for c in clubs),
                    sum(sum(lesson.present_students for lesson in c.conducted_lessons) for c in clubs)
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Статистика', index=False)
        
        output.seek(0)
        
        # Генеруємо ім'я файлу з поточною датою
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"clubs_export_{today}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting clubs: {str(e)}"
        )
