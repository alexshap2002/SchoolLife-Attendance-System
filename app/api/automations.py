"""
API для системи автоматизацій адміністратора.
"""

import logging
from datetime import datetime, time
from typing import List, Optional, Dict, Any
import json

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_db
from app.models import AdminAutomation, AutomationLog, Teacher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/automations", tags=["automations"])


# === PYDANTIC MODELS ===
class AutomationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    automation_type: str
    admin_chat_id: int
    is_enabled: bool = True
    trigger_time: Optional[str] = None  # "12:00:00" format
    trigger_day: Optional[int] = None   # 0-6 (Monday-Sunday) 
    config: Optional[Dict[str, Any]] = None


class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    trigger_time: Optional[str] = None
    trigger_day: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class AutomationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    automation_type: str
    admin_chat_id: int
    is_enabled: bool
    trigger_time: Optional[str]
    trigger_day: Optional[int]
    config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    last_triggered: Optional[datetime]
    
    class Config:
        from_attributes = True


class AutomationLogResponse(BaseModel):
    id: int
    automation_id: int
    triggered_at: datetime
    status: str
    message: Optional[str]
    error_details: Optional[str]
    students_count: Optional[int]
    clubs_count: Optional[int]
    execution_time_ms: Optional[int]
    
    class Config:
        from_attributes = True


# === API ENDPOINTS ===

@router.get("/admins")
async def get_telegram_admins(db: AsyncSession = Depends(get_db)):
    """Отримати список телеграм адміністраторів."""
    
    # Отримуємо унікальні chat_id з автоматизацій
    result = await db.execute(
        select(AdminAutomation.admin_chat_id)
        .distinct()
        .order_by(AdminAutomation.admin_chat_id)
    )
    chat_ids = result.scalars().all()
    
    # Отримуємо інформацію про вчителів з Telegram
    if chat_ids:
        teachers_result = await db.execute(
            select(Teacher).where(Teacher.tg_chat_id.in_(chat_ids))
        )
        teachers = {teacher.tg_chat_id: teacher for teacher in teachers_result.scalars().all()}
    else:
        teachers = {}
    
    admins = []
    for chat_id in chat_ids:
        teacher = teachers.get(chat_id)
        admin_info = {
            "chat_id": chat_id,
            "name": teacher.full_name if teacher else f"Адмін {chat_id}",
            "username": teacher.tg_username if teacher else None,
            "is_teacher": bool(teacher),
            "automations_count": 0
        }
        
        # Рахуємо кількість автоматизацій для цього адміна
        count_result = await db.execute(
            select(func.count(AdminAutomation.id))
            .where(AdminAutomation.admin_chat_id == chat_id)
        )
        admin_info["automations_count"] = count_result.scalar()
        
        admins.append(admin_info)
    
    return {"admins": admins}


@router.get("", response_model=List[AutomationResponse])
async def get_automations(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Отримати список автоматизацій."""
    
    query = select(AdminAutomation)
    
    if enabled_only:
        query = query.where(AdminAutomation.is_enabled == True)
    
    query = query.order_by(AdminAutomation.automation_type, AdminAutomation.name)
    
    result = await db.execute(query)
    automations = result.scalars().all()
    
    # Конвертуємо для response
    response_data = []
    for automation in automations:
        data = {
            "id": automation.id,
            "name": automation.name,
            "description": automation.description,
            "automation_type": automation.automation_type,
            "admin_chat_id": automation.admin_chat_id,
            "is_enabled": automation.is_enabled,
            "trigger_time": automation.trigger_time.strftime("%H:%M:%S") if automation.trigger_time else None,
            "trigger_day": automation.trigger_day,
            "config": json.loads(automation.config) if automation.config else None,
            "created_at": automation.created_at,
            "updated_at": automation.updated_at,
            "last_triggered": automation.last_triggered
        }
        response_data.append(AutomationResponse(**data))
    
    return response_data


@router.post("", response_model=AutomationResponse)
async def create_automation(
    automation_data: AutomationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Створити нову автоматизацію."""
    
    # Конвертуємо trigger_time
    trigger_time_obj = None
    if automation_data.trigger_time:
        try:
            hour, minute, second = map(int, automation_data.trigger_time.split(':'))
            trigger_time_obj = time(hour, minute, second)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid trigger_time format. Use HH:MM:SS"
            )
    
    # Створюємо автоматизацію
    automation = AdminAutomation(
        name=automation_data.name,
        description=automation_data.description,
        automation_type=automation_data.automation_type,
        admin_chat_id=automation_data.admin_chat_id,
        is_enabled=automation_data.is_enabled,
        trigger_time=trigger_time_obj,
        trigger_day=automation_data.trigger_day,
        config=json.dumps(automation_data.config) if automation_data.config else None
    )
    
    db.add(automation)
    await db.commit()
    await db.refresh(automation)
    
    logger.info(f"Created automation: {automation.name} (ID: {automation.id})")
    
    # Повертаємо response
    return AutomationResponse(
        id=automation.id,
        name=automation.name,
        description=automation.description,
        automation_type=automation.automation_type,
        admin_chat_id=automation.admin_chat_id,
        is_enabled=automation.is_enabled,
        trigger_time=automation.trigger_time.strftime("%H:%M:%S") if automation.trigger_time else None,
        trigger_day=automation.trigger_day,
        config=json.loads(automation.config) if automation.config else None,
        created_at=automation.created_at,
        updated_at=automation.updated_at,
        last_triggered=automation.last_triggered
    )


@router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Отримати автоматизацію за ID."""
    
    result = await db.execute(
        select(AdminAutomation).where(AdminAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found"
        )
    
    return AutomationResponse(
        id=automation.id,
        name=automation.name,
        description=automation.description,
        automation_type=automation.automation_type,
        admin_chat_id=automation.admin_chat_id,
        is_enabled=automation.is_enabled,
        trigger_time=automation.trigger_time.strftime("%H:%M:%S") if automation.trigger_time else None,
        trigger_day=automation.trigger_day,
        config=json.loads(automation.config) if automation.config else None,
        created_at=automation.created_at,
        updated_at=automation.updated_at,
        last_triggered=automation.last_triggered
    )


@router.put("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: int,
    automation_data: AutomationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Оновити автоматизацію."""
    
    result = await db.execute(
        select(AdminAutomation).where(AdminAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found"
        )
    
    # Оновлюємо поля
    if automation_data.name is not None:
        automation.name = automation_data.name
    if automation_data.description is not None:
        automation.description = automation_data.description
    if automation_data.is_enabled is not None:
        automation.is_enabled = automation_data.is_enabled
    if automation_data.trigger_time is not None:
        try:
            hour, minute, second = map(int, automation_data.trigger_time.split(':'))
            automation.trigger_time = time(hour, minute, second)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid trigger_time format. Use HH:MM:SS"
            )
    if automation_data.trigger_day is not None:
        automation.trigger_day = automation_data.trigger_day
    if automation_data.config is not None:
        automation.config = json.dumps(automation_data.config)
    
    automation.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(automation)
    
    logger.info(f"Updated automation: {automation.name} (ID: {automation.id})")
    
    return AutomationResponse(
        id=automation.id,
        name=automation.name,
        description=automation.description,
        automation_type=automation.automation_type,
        admin_chat_id=automation.admin_chat_id,
        is_enabled=automation.is_enabled,
        trigger_time=automation.trigger_time.strftime("%H:%M:%S") if automation.trigger_time else None,
        trigger_day=automation.trigger_day,
        config=json.loads(automation.config) if automation.config else None,
        created_at=automation.created_at,
        updated_at=automation.updated_at,
        last_triggered=automation.last_triggered
    )


@router.delete("/{automation_id}")
async def delete_automation(
    automation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Видалити автоматизацію."""
    
    result = await db.execute(
        select(AdminAutomation).where(AdminAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found"
        )
    
    # Видаляємо логи
    await db.execute(
        delete(AutomationLog).where(AutomationLog.automation_id == automation_id)
    )
    
    # Видаляємо автоматизацію
    await db.execute(
        delete(AdminAutomation).where(AdminAutomation.id == automation_id)
    )
    
    await db.commit()
    
    logger.info(f"Deleted automation: {automation.name} (ID: {automation.id})")
    
    return {"message": "Automation deleted successfully"}


@router.post("/{automation_id}/toggle")
async def toggle_automation(
    automation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Перемкнути статус автоматизації (увімкнути/вимкнути)."""
    
    result = await db.execute(
        select(AdminAutomation).where(AdminAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found"
        )
    
    # Перемикаємо статус
    automation.is_enabled = not automation.is_enabled
    automation.updated_at = datetime.utcnow()
    
    await db.commit()
    
    status_text = "enabled" if automation.is_enabled else "disabled"
    logger.info(f"Toggled automation: {automation.name} (ID: {automation.id}) - {status_text}")
    
    return {
        "message": f"Automation {status_text} successfully",
        "is_enabled": automation.is_enabled
    }


@router.get("/{automation_id}/logs", response_model=List[AutomationLogResponse])
async def get_automation_logs(
    automation_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Отримати логи виконання автоматизації."""
    
    # Перевіряємо що автоматизація існує
    result = await db.execute(
        select(AdminAutomation).where(AdminAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found"
        )
    
    # Отримуємо логи
    result = await db.execute(
        select(AutomationLog)
        .where(AutomationLog.automation_id == automation_id)
        .order_by(AutomationLog.triggered_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return [AutomationLogResponse(**log.__dict__) for log in logs]


@router.get("/types/available")
async def get_available_automation_types():
    """Отримати список доступних типів автоматизацій."""
    
    return {
        "automation_types": [
            {
                "type": "BIRTHDAYS",
                "name": "🎂 Дні народження студентів",
                "description": "Нагадує о 12:00 про дні народження студентів, які мають уроки сьогодні",
                "requires_time": True,
                "requires_day": False,
                "default_time": "12:00:00"
            },
            {
                "type": "LESSON_REMINDER_30",
                "name": "⏰ Нагадування за 30 хвилин до уроку",
                "description": "Нагадує вчителям за 30 хвилин до початку уроку",
                "requires_time": False,
                "requires_day": False
            },
            {
                "type": "LESSON_REMINDER_10",
                "name": "🔔 Нагадування за 10 хвилин до уроку",
                "description": "Нагадує вчителям за 10 хвилин до початку уроку",
                "requires_time": False,
                "requires_day": False
            },
            {
                "type": "DAILY_REPORT",
                "name": "📊 Щоденний звіт",
                "description": "Звіт про проведені уроки та відвідуваність за день",
                "requires_time": True,
                "requires_day": False,
                "default_time": "20:00:00"
            },
            {
                "type": "WEEKLY_ATTENDANCE",
                "name": "📈 Тижнева відвідуваність",
                "description": "Звіт про відвідуваність за тиждень",
                "requires_time": True,
                "requires_day": True,
                "default_time": "18:00:00",
                "default_day": 5
            },
            {
                "type": "LOW_ATTENDANCE_ALERT",
                "name": "⚠️ Попередження про низьку відвідуваність",
                "description": "Сповіщення про гуртки з відвідуваністю менше 70%",
                "requires_time": True,
                "requires_day": False,
                "default_time": "19:00:00"
            },
            {
                "type": "MISSING_ATTENDANCE",
                "name": "❌ Не заповнена відвідуваність",
                "description": "Нагадування про незаповнену відвідуваність після уроків",
                "requires_time": True,
                "requires_day": False,
                "default_time": "21:00:00"
            },
            {
                "type": "TEACHER_WORKLOAD",
                "name": "👨‍🏫 Навантаження вчителів",
                "description": "Звіт про навантаження вчителів за тиждень",
                "requires_time": True,
                "requires_day": True,
                "default_time": "17:00:00",
                "default_day": 0
            },
            {
                "type": "STUDENT_PROGRESS",
                "name": "📚 Прогрес студентів",
                "description": "Звіт про прогрес студентів з низькою відвідуваністю",
                "requires_time": True,
                "requires_day": True,
                "default_time": "16:00:00",
                "default_day": 5
            },
            {
                "type": "PAYROLL_REMINDER",
                "name": "💰 Нагадування про зарплати",
                "description": "Нагадування про необхідність нарахування зарплати",
                "requires_time": True,
                "requires_day": True,
                "default_time": "10:00:00",
                "default_day": 0
            },
            {
                "type": "EQUIPMENT_CHECK",
                "name": "🔧 Перевірка обладнання",
                "description": "Нагадування про перевірку обладнання в кабінетах",
                "requires_time": True,
                "requires_day": True,
                "default_time": "15:00:00",
                "default_day": 1
            },
            {
                "type": "PARENT_NOTIFICATIONS",
                "name": "👪 Повідомлення батькам",
                "description": "Нагадування про необхідність зв'язку з батьками",
                "requires_time": True,
                "requires_day": False,
                "default_time": "14:00:00"
            },
            {
                "type": "HOLIDAY_REMINDERS",
                "name": "🎉 Нагадування про свята",
                "description": "Нагадування про державні свята та вихідні дні",
                "requires_time": True,
                "requires_day": False,
                "default_time": "18:00:00"
            },
            {
                "type": "BACKUP_REMINDER",
                "name": "💾 Нагадування про резервні копії",
                "description": "Нагадування про створення резервних копій даних",
                "requires_time": True,
                "requires_day": True,
                "default_time": "22:00:00",
                "default_day": 5
            },
            {
                "type": "SYSTEM_HEALTH",
                "name": "🏥 Стан системи",
                "description": "Звіт про стан системи та можливі проблеми",
                "requires_time": True,
                "requires_day": False,
                "default_time": "08:00:00"
            }
        ]
    }


@router.post("/admins/{chat_id}/test")
async def test_admin_notification(
    chat_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Відправити тестове повідомлення адміністратору."""
    
    # Тут буде логіка відправки тестового повідомлення через Telegram
    # Поки що повертаємо заглушку
    
    return {
        "message": f"Тестове повідомлення відправлено адміністратору {chat_id}",
        "status": "success"
    }


@router.post("/{automation_id}/test")
async def test_automation(
    automation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Тестове виконання автоматизації."""
    
    result = await db.execute(
        select(AdminAutomation).where(AdminAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found"
        )
    
    # Виконуємо автоматизацію через automation_service
    from app.services.automation_service import automation_service
    
    try:
        result_data = await automation_service.execute_automation(automation, db)
        
        return {
            "message": f"✅ Тестове виконання '{automation.name}' завершено успішно",
            "automation_type": automation.automation_type,
            "status": "success",
            "result": result_data
        }
    except Exception as e:
        logger.error(f"Помилка тестування автоматизації {automation_id}: {e}")
        return {
            "message": f"❌ Помилка виконання '{automation.name}': {str(e)}",
            "automation_type": automation.automation_type,
            "status": "error",
            "error": str(e)
        }
