"""Payroll model."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PayrollBasis(str, Enum):
    """Payroll basis enum."""

    AUTO = "AUTO"  # Automatically calculated
    MANUAL = "MANUAL"  # Manually overridden by admin


class Payroll(Base):
    """Payroll model for teacher payments."""

    __tablename__ = "payroll"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    lesson_event_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_events.id"), nullable=False
    )
    basis: Mapped[PayrollBasis] = mapped_column(
        SQLEnum(PayrollBasis), default=PayrollBasis.AUTO, nullable=False
    )
    amount_decimal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Amount in UAH
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="payroll_records")
    lesson_event: Mapped["LessonEvent"] = relationship(
        "LessonEvent", back_populates="payroll_records"
    )

    def __repr__(self) -> str:
        return (
            f"<Payroll(id={self.id}, "
            f"teacher='{self.teacher.full_name if self.teacher else 'N/A'}', "
            f"amount={self.amount_decimal}, basis={self.basis}, "
            f"created_at={self.created_at})>"
        )
