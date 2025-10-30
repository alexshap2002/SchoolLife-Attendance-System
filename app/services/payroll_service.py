"""Payroll service for automatic salary calculation."""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    LessonEvent, 
    PayRate, 
    PayRateType, 
    Payroll, 
    PayrollBasis, 
    Attendance, 
    AttendanceStatus,
    Teacher
)

logger = logging.getLogger(__name__)


class PayrollService:
    """Service for handling payroll calculations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_active_pay_rate(self, teacher_id: int, lesson_date: date) -> Optional[PayRate]:
        """Get active pay rate for teacher on specific date."""
        
        result = await self.db.execute(
            select(PayRate)
            .where(
                PayRate.teacher_id == teacher_id,
                PayRate.active_from <= lesson_date,
                (PayRate.active_to.is_(None) | (PayRate.active_to >= lesson_date))
            )
            .order_by(PayRate.active_from.desc())
            .limit(1)
        )
        
        return result.scalar_one_or_none()
    
    async def calculate_lesson_payment(
        self, 
        lesson_event_id: int,
        pay_rate: PayRate
    ) -> Decimal:
        """Calculate payment amount for a lesson based on pay rate type."""
        
        if pay_rate.rate_type == PayRateType.PER_LESSON:
            # За заняття - просто повертаємо фіксовану суму
            return pay_rate.amount_decimal
        
        elif pay_rate.rate_type == PayRateType.PER_PRESENT:
            # За присутнього учня - рахуємо кількість присутніх
            result = await self.db.execute(
                select(func.count(Attendance.id))
                .where(
                    Attendance.lesson_event_id == lesson_event_id,
                    Attendance.status == AttendanceStatus.PRESENT
                )
            )
            present_count = result.scalar() or 0
            
            return pay_rate.amount_decimal * Decimal(present_count)
        
        return Decimal(0)
    
    async def count_present_students(self, lesson_event_id: int) -> int:
        """Count number of present students for a lesson."""
        
        result = await self.db.execute(
            select(func.count(Attendance.id))
            .where(
                Attendance.lesson_event_id == lesson_event_id,
                Attendance.status == AttendanceStatus.PRESENT
            )
        )
        
        return result.scalar() or 0
    
    async def has_existing_payroll(self, lesson_event_id: int) -> bool:
        """Check if payroll already exists for this lesson."""
        
        result = await self.db.execute(
            select(func.count(Payroll.id))
            .where(Payroll.lesson_event_id == lesson_event_id)
        )
        
        return (result.scalar() or 0) > 0
    
    async def create_automatic_payroll(self, lesson_event_id: int) -> Optional[Payroll]:
        """
        Create automatic payroll entry for completed lesson.
        
        Rules:
        1. Must have at least 1 present student
        2. Must not already have payroll entry
        3. Must have active pay rate for teacher
        """
        
        # Перевіряємо чи вже є payroll для цього уроку
        if await self.has_existing_payroll(lesson_event_id):
            logger.info(f"Payroll already exists for lesson_event {lesson_event_id}")
            return None
        
        # Завантажуємо lesson event з teacher
        result = await self.db.execute(
            select(LessonEvent)
            .options(selectinload(LessonEvent.teacher))
            .where(LessonEvent.id == lesson_event_id)
        )
        lesson_event = result.scalar_one_or_none()
        
        if not lesson_event:
            logger.error(f"LessonEvent {lesson_event_id} not found")
            return None
        
        if not lesson_event.teacher:
            logger.error(f"LessonEvent {lesson_event_id} has no teacher")
            return None
        
        # Перевіряємо кількість присутніх студентів
        present_count = await self.count_present_students(lesson_event_id)
        
        if present_count == 0:
            logger.info(
                f"No students present for lesson_event {lesson_event_id}, "
                f"no payroll will be created"
            )
            return None
        
        # Знаходимо активний тариф для вчителя
        pay_rate = await self.get_active_pay_rate(
            lesson_event.teacher_id, 
            lesson_event.date
        )
        
        if not pay_rate:
            logger.warning(
                f"No active pay rate found for teacher {lesson_event.teacher.full_name} "
                f"on date {lesson_event.date}"
            )
            return None
        
        # Розраховуємо суму до виплати
        payment_amount = await self.calculate_lesson_payment(lesson_event_id, pay_rate)
        
        if payment_amount <= 0:
            logger.warning(f"Payment amount is 0 for lesson_event {lesson_event_id}")
            return None
        
        # Створюємо payroll запис
        payroll = Payroll(
            teacher_id=lesson_event.teacher_id,
            lesson_event_id=lesson_event_id,
            basis=PayrollBasis.AUTO,
            amount_decimal=payment_amount,
            note=f"Автоматичне нарахування. Присутніх: {present_count}. "
                 f"Тариф: {pay_rate.rate_type.value} - {pay_rate.amount_decimal} ₴"
        )
        
        self.db.add(payroll)
        await self.db.commit()
        await self.db.refresh(payroll)
        
        logger.info(
            f"✅ Created automatic payroll {payroll.id} for teacher "
            f"{lesson_event.teacher.full_name}: {payment_amount} ₴ "
            f"(lesson_event: {lesson_event_id}, present: {present_count})"
        )
        
        return payroll
    
    async def get_teacher_payroll_summary(
        self, 
        teacher_id: int, 
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> dict:
        """Get payroll summary for teacher in date range."""
        
        query = (
            select(Payroll)
            .options(selectinload(Payroll.lesson_event))
            .where(Payroll.teacher_id == teacher_id)
        )
        
        if from_date:
            query = query.join(LessonEvent).where(LessonEvent.date >= from_date)
        
        if to_date:
            query = query.join(LessonEvent).where(LessonEvent.date <= to_date)
        
        result = await self.db.execute(query.order_by(Payroll.created_at.desc()))
        payroll_records = result.scalars().all()
        
        total_amount = sum(record.amount_decimal for record in payroll_records)
        auto_count = len([r for r in payroll_records if r.basis == PayrollBasis.AUTO])
        manual_count = len([r for r in payroll_records if r.basis == PayrollBasis.MANUAL])
        
        return {
            "records": payroll_records,
            "total_amount": total_amount,
            "total_count": len(payroll_records),
            "auto_count": auto_count,
            "manual_count": manual_count,
            "from_date": from_date,
            "to_date": to_date
        }