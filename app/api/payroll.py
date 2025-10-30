"""Payroll management API endpoints."""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
import io
import pandas as pd

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Payroll, PayrollBasis, Teacher, LessonEvent, ConductedLesson

router = APIRouter(prefix="/api/payroll", tags=["payroll"])
logger = logging.getLogger(__name__)


class PayrollCreateRequest(BaseModel):
    """Request model for creating a payroll."""
    teacher_id: int
    lesson_event_id: Optional[int] = None
    basis: PayrollBasis
    amount_decimal: Decimal
    note: Optional[str] = None


class PayrollUpdateRequest(BaseModel):
    """Request model for updating a payroll."""
    teacher_id: Optional[int] = None
    basis: Optional[PayrollBasis] = None
    amount_decimal: Optional[Decimal] = None
    note: Optional[str] = None


class PayrollResponse(BaseModel):
    """Response model for payroll."""
    id: int
    teacher_id: int
    teacher_name: str
    lesson_event_id: Optional[int]
    lesson_date: Optional[datetime] = None
    club_name: Optional[str] = None
    basis: PayrollBasis
    amount_decimal: Decimal
    note: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[PayrollResponse])
async def get_payroll_records(
    teacher_id: Optional[int] = None,
    basis: Optional[PayrollBasis] = None,
    date_from: Optional[date] = Query(None, description="Дата початку (фільтр за датою уроку)"),
    date_to: Optional[date] = Query(None, description="Дата кінця (фільтр за датою уроку)"),
    limit: Optional[int] = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all payroll records, optionally filtered."""
    query = select(Payroll).options(
        selectinload(Payroll.teacher),
        selectinload(Payroll.lesson_event).selectinload(LessonEvent.club)
    )
    
    if teacher_id:
        query = query.where(Payroll.teacher_id == teacher_id)
    
    if basis:
        query = query.where(Payroll.basis == basis)
    
    # Фільтр за датами УРОКУ (а не created_at)
    if date_from or date_to:
        query = query.join(LessonEvent, Payroll.lesson_event_id == LessonEvent.id)
        if date_from:
            query = query.where(LessonEvent.date >= date_from)
        if date_to:
            query = query.where(LessonEvent.date <= date_to)
    
    query = query.order_by(Payroll.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    payroll_records = result.scalars().all()
    
    response_data = []
    for payroll in payroll_records:
        # Отримуємо інформацію про lesson_event та club
        lesson_date = None
        club_name = None
        
        if payroll.lesson_event:
            lesson_date = payroll.lesson_event.date
            if payroll.lesson_event.club:
                club_name = payroll.lesson_event.club.name
        
        response_data.append(PayrollResponse(
            id=payroll.id,
            teacher_id=payroll.teacher_id,
            teacher_name=payroll.teacher.full_name if payroll.teacher else "N/A",
            lesson_event_id=payroll.lesson_event_id,
            lesson_date=lesson_date,
            club_name=club_name,
            basis=payroll.basis,
            amount_decimal=payroll.amount_decimal,
            note=payroll.note,
            created_at=payroll.created_at
        ))
    
    return response_data


@router.get("/{payroll_id}", response_model=PayrollResponse)
async def get_payroll_record(
    payroll_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific payroll record."""
    result = await db.execute(
        select(Payroll)
        .options(
            selectinload(Payroll.teacher),
            selectinload(Payroll.lesson_event)
        )
        .where(Payroll.id == payroll_id)
    )
    payroll = result.scalar_one_or_none()
    
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    return PayrollResponse(
        id=payroll.id,
        teacher_id=payroll.teacher_id,
        teacher_name=payroll.teacher.full_name if payroll.teacher else "N/A",
        lesson_event_id=payroll.lesson_event_id,
        basis=payroll.basis,
        amount_decimal=payroll.amount_decimal,
        note=payroll.note,
        created_at=payroll.created_at
    )


@router.post("", response_model=PayrollResponse)
async def create_payroll_record(
    payroll_data: PayrollCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new payroll record."""
    
    # Перевіряємо чи існує вчитель
    teacher_result = await db.execute(
        select(Teacher).where(Teacher.id == payroll_data.teacher_id)
    )
    teacher = teacher_result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    # Перевіряємо урок якщо вказано
    lesson_event = None
    if payroll_data.lesson_event_id:
        lesson_result = await db.execute(
            select(LessonEvent).where(LessonEvent.id == payroll_data.lesson_event_id)
        )
        lesson_event = lesson_result.scalar_one_or_none()
        
        if not lesson_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson event not found"
            )
    
    # Створюємо новий запис зарплати
    payroll = Payroll(
        teacher_id=payroll_data.teacher_id,
        lesson_event_id=payroll_data.lesson_event_id,
        basis=payroll_data.basis,
        amount_decimal=payroll_data.amount_decimal,
        note=payroll_data.note
    )
    
    db.add(payroll)
    await db.commit()
    await db.refresh(payroll)
    
    # Завантажуємо teacher для response
    await db.refresh(payroll, ['teacher'])
    
    logger.info(f"Created new payroll record {payroll.id} for teacher {teacher.full_name}: {payroll.amount_decimal} ₴")
    
    # 📝 AUDIT LOG: Нарахування зарплати
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="payroll",
            entity_id=payroll.id,
            entity_name=f"{teacher.full_name} - {payroll.amount_decimal} ₴",
            description=f"Нараховано зарплату: {teacher.full_name}, сума {payroll.amount_decimal} ₴ (підстава: {payroll.basis})",
            user_name="Адміністратор",
            changes={"teacher": teacher.full_name, "amount": str(payroll.amount_decimal), "basis": payroll.basis}
        )
    except Exception as e:
        pass
    
    return PayrollResponse(
        id=payroll.id,
        teacher_id=payroll.teacher_id,
        teacher_name=teacher.full_name,
        lesson_event_id=payroll.lesson_event_id,
        basis=payroll.basis,
        amount_decimal=payroll.amount_decimal,
        note=payroll.note,
        created_at=payroll.created_at
    )


@router.put("/{payroll_id}", response_model=PayrollResponse)
async def update_payroll_record(
    payroll_id: int,
    payroll_data: PayrollUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a payroll record."""
    
    # Знаходимо запис зарплати
    result = await db.execute(
        select(Payroll)
        .options(selectinload(Payroll.teacher))
        .where(Payroll.id == payroll_id)
    )
    payroll = result.scalar_one_or_none()
    
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    # Зберігаємо старі значення для аудиту
    old_values = {
        "teacher_id": payroll.teacher_id,
        "amount": str(payroll.amount_decimal),
        "basis": payroll.basis,
        "note": payroll.note
    }
    
    # Оновлюємо поля
    if payroll_data.teacher_id is not None:
        # Перевіряємо чи існує новий вчитель
        teacher_result = await db.execute(
            select(Teacher).where(Teacher.id == payroll_data.teacher_id)
        )
        teacher = teacher_result.scalar_one_or_none()
        
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher not found"
            )
        
        payroll.teacher_id = payroll_data.teacher_id
    
    if payroll_data.basis is not None:
        payroll.basis = payroll_data.basis
    if payroll_data.amount_decimal is not None:
        payroll.amount_decimal = payroll_data.amount_decimal
    if payroll_data.note is not None:
        payroll.note = payroll_data.note
    
    # 📝 AUDIT LOG: Оновлення зарплати
    try:
        from app.services.audit_service import log_audit
        teacher_name = payroll.teacher.full_name if payroll.teacher else "(викладач не вказаний)"
        new_values = {
            "teacher_id": payroll.teacher_id,
            "amount": str(payroll.amount_decimal),
            "basis": payroll.basis,
            "note": payroll.note
        }
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {new_values.get(k)}" for k in new_values.keys() if old_values.get(k) != new_values.get(k)])
        
        await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="payroll",
            entity_id=payroll.id,
            entity_name=f"{teacher_name} - {payroll.amount_decimal} ₴",
            description=f"Оновлено зарплату: {teacher_name}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": new_values}
        )
    except Exception as e:
        pass
    
    await db.commit()
    await db.refresh(payroll)
    
    logger.info(f"Updated payroll record {payroll.id}")
    
    return PayrollResponse(
        id=payroll.id,
        teacher_id=payroll.teacher_id,
        teacher_name=payroll.teacher.full_name if payroll.teacher else "N/A",
        lesson_event_id=payroll.lesson_event_id,
        basis=payroll.basis,
        amount_decimal=payroll.amount_decimal,
        note=payroll.note,
        created_at=payroll.created_at
    )


@router.delete("/{payroll_id}")
async def delete_payroll_record(
    payroll_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a payroll record."""
    
    # Перевіряємо чи існує запис
    result = await db.execute(
        select(Payroll)
        .options(selectinload(Payroll.teacher))
        .where(Payroll.id == payroll_id)
    )
    payroll = result.scalar_one_or_none()
    
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    # Зберігаємо дані для аудиту перед видаленням
    teacher_name = payroll.teacher.full_name if payroll.teacher else "(викладач не вказаний)"
    amount = str(payroll.amount_decimal)
    basis = payroll.basis
    
    # Видаляємо запис
    await db.execute(delete(Payroll).where(Payroll.id == payroll_id))
    
    # 📝 AUDIT LOG: Видалення зарплати
    try:
        from app.services.audit_service import log_audit
        await log_audit(
            db=db,
            action_type="DELETE",
            entity_type="payroll",
            entity_id=payroll_id,
            entity_name=f"{teacher_name} - {amount} ₴",
            description=f"Видалено нарахування зарплати: {teacher_name}, сума {amount} ₴ (підстава: {basis})",
            user_name="Адміністратор",
            changes={"deleted": {"teacher": teacher_name, "amount": amount, "basis": basis}}
        )
    except Exception as e:
        pass
    
    await db.commit()
    
    logger.info(f"Deleted payroll record {payroll_id}")
    
    return {"message": "Payroll record deleted successfully"}


@router.get("/export/excel")
async def export_payroll_excel(
    teacher_id: Optional[int] = Query(None, description="Filter by teacher ID"),
    start_date: Optional[date] = Query(None, description="Start date filter (дата уроку)"),
    end_date: Optional[date] = Query(None, description="End date filter (дата уроку)"),
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """Export payroll data to Excel."""
    
    try:
        # Базовий запит
        query = (
            select(Payroll)
            .options(
                selectinload(Payroll.teacher),
                selectinload(Payroll.lesson_event).selectinload(LessonEvent.club)
            )
            .order_by(Payroll.created_at.desc())
        )
        
        # Фільтри
        if teacher_id:
            query = query.where(Payroll.teacher_id == teacher_id)
        # Фільтр по даті УРОКУ (а не created_at)
        if start_date or end_date:
            query = query.join(LessonEvent, Payroll.lesson_event_id == LessonEvent.id)
            if start_date:
                query = query.where(LessonEvent.date >= start_date)
            if end_date:
                query = query.where(LessonEvent.date <= end_date)
        
        result = await db.execute(query)
        payrolls = result.scalars().all()
        
        if not payrolls:
            raise HTTPException(status_code=404, detail="No payroll records found")
        
        # Підготуємо дані для Excel
        payroll_data = []
        for payroll in payrolls:
            payroll_data.append({
                # === ОСНОВНА ІНФОРМАЦІЯ ===
                "Дата нарахування": payroll.created_at.strftime("%d.%m.%Y") if payroll.created_at else "—",
                "Вчитель": payroll.teacher.full_name if payroll.teacher else "—",
                "Гурток": payroll.lesson_event.club.name if payroll.lesson_event and payroll.lesson_event.club else "—",
                "Дата уроку": payroll.lesson_event.date.strftime("%d.%m.%Y") if payroll.lesson_event and payroll.lesson_event.date else "—",
                
                # === ФІНАНСОВА ІНФОРМАЦІЯ ===
                "Сума (грн)": float(payroll.amount_decimal) if payroll.amount_decimal else 0,
                "Основа нарахування": payroll.basis.value if payroll.basis else "—",
                "Кількість учнів": "—",  # Lesson event doesn't have direct student count
                
                # === СТАТУС ===
                "Статус": "Нараховано",
                
                # === СИСТЕМНА ІНФОРМАЦІЯ ===
                "Час створення": payroll.created_at.strftime("%d.%m.%Y %H:%M") if payroll.created_at else "—"
            })
        
        # Створюємо DataFrame
        df = pd.DataFrame(payroll_data)
        
        # Створюємо Excel файл в пам'яті
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Зарплати', index=False)
            
            # Налаштовуємо ширину колонок
            worksheet = writer.sheets['Зарплати']
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
            for payroll in payrolls:
                teacher_name = payroll.teacher.full_name if payroll.teacher else "Невідомий"
                if teacher_name not in teacher_stats:
                    teacher_stats[teacher_name] = {
                        'count': 0, 
                        'total_amount': 0, 
                        'approved_count': 0,
                        'approved_amount': 0
                    }
                teacher_stats[teacher_name]['count'] += 1
                amount = float(payroll.amount_decimal) if payroll.amount_decimal else 0
                teacher_stats[teacher_name]['total_amount'] += amount
                if payroll.is_approved:
                    teacher_stats[teacher_name]['approved_count'] += 1
                    teacher_stats[teacher_name]['approved_amount'] += amount
            
            stats_data = {
                'Вчитель': list(teacher_stats.keys()),
                'Всього нарахувань': [stats['count'] for stats in teacher_stats.values()],
                'Загальна сума': [stats['total_amount'] for stats in teacher_stats.values()],
                'Затверджених нарахувань': [stats['approved_count'] for stats in teacher_stats.values()],
                'Затверджена сума': [stats['approved_amount'] for stats in teacher_stats.values()]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Статистика по вчителях', index=False)
            
            # Загальна статистика
            total_amount = sum(float(p.amount_decimal) if p.amount_decimal else 0 for p in payrolls)
            approved_amount = sum(float(p.amount_decimal) if p.amount_decimal and p.is_approved else 0 for p in payrolls)
            
            summary_data = {
                'Показник': [
                    'Загальна кількість нарахувань',
                    'Затверджених нарахувань',
                    'Загальна сума (грн)',
                    'Затверджена сума (грн)',
                    'Очікує затвердження (грн)'
                ],
                'Значення': [
                    len(payrolls),
                    len([p for p in payrolls if p.is_approved]),
                    total_amount,
                    approved_amount,
                    total_amount - approved_amount
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Загальна статистика', index=False)
        
        output.seek(0)
        
        # Генеруємо ім'я файлу з поточною датою
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"payroll_export_{today}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting payroll: {str(e)}"
        )
