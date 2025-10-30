"""Calendar exception model."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CalendarException(Base):
    """Calendar exception model for holidays and pauses."""

    __tablename__ = "calendar_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    skip: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # True = skip lessons, False = special day
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<CalendarException(id={self.id}, date={self.date}, "
            f"reason='{self.reason}', skip={self.skip})>"
        )
