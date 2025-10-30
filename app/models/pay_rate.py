"""Pay rate model."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PayRateType(str, Enum):
    """Pay rate type enum."""

    PER_LESSON = "PER_LESSON"
    PER_PRESENT = "PER_PRESENT"


class PayRate(Base):
    """Pay rate model for teacher payment rates."""

    __tablename__ = "pay_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    rate_type: Mapped[PayRateType] = mapped_column(
        SQLEnum(PayRateType), nullable=False
    )
    amount_decimal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Amount in UAH
    active_from: Mapped[date] = mapped_column(Date, nullable=False)
    active_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="pay_rates")

    def __repr__(self) -> str:
        return (
            f"<PayRate(id={self.id}, "
            f"teacher='{self.teacher.full_name if self.teacher else 'N/A'}', "
            f"rate_type={self.rate_type}, amount={self.amount_decimal}, "
            f"active_from={self.active_from}, active_to={self.active_to})>"
        )
