"""Pay rates management API endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import logging
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import PayRate, PayRateType, Teacher

router = APIRouter(prefix="/api/pay_rates", tags=["pay_rates"])
logger = logging.getLogger(__name__)


class PayRateCreateRequest(BaseModel):
    """Request model for creating a pay rate."""
    teacher_id: int
    rate_type: PayRateType
    amount_decimal: Decimal
    active_from: date
    active_to: Optional[date] = None


class PayRateUpdateRequest(BaseModel):
    """Request model for updating a pay rate."""
    rate_type: Optional[PayRateType] = None
    amount_decimal: Optional[Decimal] = None
    active_from: Optional[date] = None
    active_to: Optional[date] = None


class PayRateResponse(BaseModel):
    """Response model for pay rate."""
    id: int
    teacher_id: int
    teacher_name: str
    rate_type: PayRateType
    amount_decimal: Decimal
    active_from: date
    active_to: Optional[date]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[PayRateResponse])
async def get_pay_rates(
    teacher_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all pay rates, optionally filtered by teacher."""
    query = select(PayRate).options(selectinload(PayRate.teacher))
    
    if teacher_id:
        query = query.where(PayRate.teacher_id == teacher_id)
    
    query = query.order_by(PayRate.teacher_id, PayRate.active_from.desc())
    
    result = await db.execute(query)
    pay_rates = result.scalars().all()
    
    response_data = []
    for pay_rate in pay_rates:
        # Перевіряємо чи тариф активний на поточну дату
        today = date.today()
        is_active = (
            pay_rate.active_from <= today and 
            (pay_rate.active_to is None or pay_rate.active_to >= today)
        )
        
        response_data.append(PayRateResponse(
            id=pay_rate.id,
            teacher_id=pay_rate.teacher_id,
            teacher_name=pay_rate.teacher.full_name if pay_rate.teacher else "N/A",
            rate_type=pay_rate.rate_type,
            amount_decimal=pay_rate.amount_decimal,
            active_from=pay_rate.active_from,
            active_to=pay_rate.active_to,
            is_active=is_active,
            created_at=pay_rate.created_at
        ))
    
    return response_data


@router.get("/{pay_rate_id}", response_model=PayRateResponse)
async def get_pay_rate(
    pay_rate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific pay rate by ID."""
    result = await db.execute(
        select(PayRate)
        .options(selectinload(PayRate.teacher))
        .where(PayRate.id == pay_rate_id)
    )
    pay_rate = result.scalar_one_or_none()
    
    if not pay_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay rate not found"
        )
    
    # Перевіряємо чи тариф активний
    today = date.today()
    is_active = (
        pay_rate.active_from <= today and 
        (pay_rate.active_to is None or pay_rate.active_to >= today)
    )
    
    return PayRateResponse(
        id=pay_rate.id,
        teacher_id=pay_rate.teacher_id,
        teacher_name=pay_rate.teacher.full_name if pay_rate.teacher else "N/A",
        rate_type=pay_rate.rate_type,
        amount_decimal=pay_rate.amount_decimal,
        active_from=pay_rate.active_from,
        active_to=pay_rate.active_to,
        is_active=is_active,
        created_at=pay_rate.created_at
    )


@router.post("", response_model=PayRateResponse)
async def create_pay_rate(
    pay_rate_data: PayRateCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new pay rate."""
    
    # Перевіряємо чи існує вчитель
    teacher_result = await db.execute(
        select(Teacher).where(Teacher.id == pay_rate_data.teacher_id)
    )
    teacher = teacher_result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    # Перевіряємо валідність дат
    if pay_rate_data.active_to and pay_rate_data.active_to < pay_rate_data.active_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="active_to must be after active_from"
        )
    
    # Створюємо новий тариф
    pay_rate = PayRate(
        teacher_id=pay_rate_data.teacher_id,
        rate_type=pay_rate_data.rate_type,
        amount_decimal=pay_rate_data.amount_decimal,
        active_from=pay_rate_data.active_from,
        active_to=pay_rate_data.active_to
    )
    
    db.add(pay_rate)
    await db.flush()  # Flush щоб отримати ID
    
    # 📝 AUDIT LOG: Створення ставки зарплати
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="pay_rate",
            entity_id=pay_rate.id,
            entity_name=f"{teacher.full_name} - {pay_rate.amount_decimal}₴ ({pay_rate.rate_type.value})",
            description=f"Створено ставку зарплати: {teacher.full_name}, {pay_rate.amount_decimal}₴ ({pay_rate.rate_type.value}), з {pay_rate.active_from}",
            user_name="Адміністратор",
            changes={"after": {
                "teacher": teacher.full_name,
                "amount": str(pay_rate.amount_decimal),
                "rate_type": pay_rate.rate_type.value,
                "active_from": str(pay_rate.active_from),
                "active_to": str(pay_rate.active_to) if pay_rate.active_to else None
            }}
        )
    except Exception as e:
        pass
    
    await db.commit()
    await db.refresh(pay_rate)
    
    # Завантажуємо teacher для response
    await db.refresh(pay_rate, ['teacher'])
    
    # Перевіряємо чи тариф активний
    today = date.today()
    is_active = (
        pay_rate.active_from <= today and 
        (pay_rate.active_to is None or pay_rate.active_to >= today)
    )
    
    logger.info(f"Created new pay rate {pay_rate.id} for teacher {teacher.full_name}")
    
    return PayRateResponse(
        id=pay_rate.id,
        teacher_id=pay_rate.teacher_id,
        teacher_name=teacher.full_name,
        rate_type=pay_rate.rate_type,
        amount_decimal=pay_rate.amount_decimal,
        active_from=pay_rate.active_from,
        active_to=pay_rate.active_to,
        is_active=is_active,
        created_at=pay_rate.created_at
    )


@router.put("/{pay_rate_id}", response_model=PayRateResponse)
async def update_pay_rate(
    pay_rate_id: int,
    pay_rate_data: PayRateUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing pay rate."""
    
    # Знаходимо тариф
    result = await db.execute(
        select(PayRate)
        .options(selectinload(PayRate.teacher))
        .where(PayRate.id == pay_rate_id)
    )
    pay_rate = result.scalar_one_or_none()
    
    if not pay_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay rate not found"
        )
    
    # Зберігаємо старі значення для аудиту
    old_values = {
        "teacher": pay_rate.teacher.full_name if pay_rate.teacher else "(викладач не вказаний)",
        "rate_type": pay_rate.rate_type.value,
        "amount": str(pay_rate.amount_decimal),
        "active_from": str(pay_rate.active_from),
        "active_to": str(pay_rate.active_to) if pay_rate.active_to else "безстроково"
    }
    
    # Оновлюємо поля
    if pay_rate_data.rate_type is not None:
        pay_rate.rate_type = pay_rate_data.rate_type
    if pay_rate_data.amount_decimal is not None:
        pay_rate.amount_decimal = pay_rate_data.amount_decimal
    if pay_rate_data.active_from is not None:
        pay_rate.active_from = pay_rate_data.active_from
    if pay_rate_data.active_to is not None:
        pay_rate.active_to = pay_rate_data.active_to
    
    # Перевіряємо валідність дат
    if pay_rate.active_to and pay_rate.active_to < pay_rate.active_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="active_to must be after active_from"
        )
    
    # 📝 AUDIT LOG: Оновлення ставки зарплати
    try:
        from app.services.audit_service import log_audit
        teacher_name = pay_rate.teacher.full_name if pay_rate.teacher else "(викладач не вказаний)"
        new_values = {
            "teacher": teacher_name,
            "rate_type": pay_rate.rate_type.value,
            "amount": str(pay_rate.amount_decimal),
            "active_from": str(pay_rate.active_from),
            "active_to": str(pay_rate.active_to) if pay_rate.active_to else "безстроково"
        }
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {new_values.get(k)}" for k in new_values.keys() if old_values.get(k) != new_values.get(k)])
        
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="pay_rate",
            entity_id=pay_rate.id,
            entity_name=f"{teacher_name} - {pay_rate.amount_decimal}₴ ({pay_rate.rate_type.value})",
            description=f"Оновлено ставку зарплати: {teacher_name}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": new_values}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (pay_rate UPDATE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(pay_rate)
    
    # Перевіряємо чи тариф активний
    today = date.today()
    is_active = (
        pay_rate.active_from <= today and 
        (pay_rate.active_to is None or pay_rate.active_to >= today)
    )
    
    logger.info(f"Updated pay rate {pay_rate.id}")
    
    return PayRateResponse(
        id=pay_rate.id,
        teacher_id=pay_rate.teacher_id,
        teacher_name=pay_rate.teacher.full_name if pay_rate.teacher else "N/A",
        rate_type=pay_rate.rate_type,
        amount_decimal=pay_rate.amount_decimal,
        active_from=pay_rate.active_from,
        active_to=pay_rate.active_to,
        is_active=is_active,
        created_at=pay_rate.created_at
    )


@router.delete("/{pay_rate_id}")
async def delete_pay_rate(
    pay_rate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a pay rate."""
    
    # Перевіряємо чи існує тариф
    result = await db.execute(
        select(PayRate)
        .options(selectinload(PayRate.teacher))
        .where(PayRate.id == pay_rate_id)
    )
    pay_rate = result.scalar_one_or_none()
    
    if not pay_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay rate not found"
        )
    
    # Зберігаємо дані для аудиту перед видаленням
    teacher_name = pay_rate.teacher.full_name if pay_rate.teacher else "(викладач не вказаний)"
    amount = str(pay_rate.amount_decimal)
    rate_type = pay_rate.rate_type.value
    active_from = str(pay_rate.active_from)
    active_to = str(pay_rate.active_to) if pay_rate.active_to else "безстроково"
    
    # Видаляємо тариф
    await db.execute(delete(PayRate).where(PayRate.id == pay_rate_id))
    
    # 📝 AUDIT LOG: Видалення ставки зарплати
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="pay_rate",
            entity_id=pay_rate_id,
            entity_name=f"{teacher_name} - {amount}₴ ({rate_type})",
            description=f"Видалено ставку зарплати: {teacher_name}, {amount}₴ ({rate_type}), діяла з {active_from} до {active_to}",
            user_name="Адміністратор",
            changes={"deleted": {
                "teacher": teacher_name,
                "amount": amount,
                "rate_type": rate_type,
                "active_from": active_from,
                "active_to": active_to
            }}
        )
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (pay_rate DELETE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    
    logger.info(f"Deleted pay rate {pay_rate_id}")
    
    return {"message": "Pay rate deleted successfully"}


@router.get("/teacher/{teacher_id}/active", response_model=Optional[PayRateResponse])
async def get_active_teacher_pay_rate(
    teacher_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get current active pay rate for a teacher."""
    
    today = date.today()
    
    result = await db.execute(
        select(PayRate)
        .options(selectinload(PayRate.teacher))
        .where(
            PayRate.teacher_id == teacher_id,
            PayRate.active_from <= today,
            (PayRate.active_to.is_(None) | (PayRate.active_to >= today))
        )
        .order_by(PayRate.active_from.desc())
        .limit(1)
    )
    
    pay_rate = result.scalar_one_or_none()
    
    if not pay_rate:
        return None
    
    return PayRateResponse(
        id=pay_rate.id,
        teacher_id=pay_rate.teacher_id,
        teacher_name=pay_rate.teacher.full_name if pay_rate.teacher else "N/A",
        rate_type=pay_rate.rate_type,
        amount_decimal=pay_rate.amount_decimal,
        active_from=pay_rate.active_from,
        active_to=pay_rate.active_to,
        is_active=True,
        created_at=pay_rate.created_at
    )
