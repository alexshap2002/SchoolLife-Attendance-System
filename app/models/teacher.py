"""Teacher model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Teacher(Base):
    """Teacher model for storing teacher information."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tg_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    tg_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule", back_populates="teacher"
    )
    lesson_events: Mapped[list["LessonEvent"]] = relationship(
        "LessonEvent", back_populates="teacher"
    )
    pay_rates: Mapped[list["PayRate"]] = relationship(
        "PayRate", back_populates="teacher"
    )
    payroll_records: Mapped[list["Payroll"]] = relationship(
        "Payroll", back_populates="teacher"
    )
    conducted_lessons: Mapped[list["ConductedLesson"]] = relationship(
        "ConductedLesson", back_populates="teacher"
    )

    def __repr__(self) -> str:
        return f"<Teacher(id={self.id}, name='{self.full_name}', active={self.active})>"
