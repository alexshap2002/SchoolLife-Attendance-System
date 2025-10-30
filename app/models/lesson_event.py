"""Lesson event model."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class LessonEventStatus(str, Enum):
    """Lesson event status enum."""

    PLANNED = "PLANNED"
    SENT = "SENT"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class LessonEvent(Base):
    """Lesson event model for tracking individual lesson instances."""

    __tablename__ = "lesson_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    club_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clubs.id"), nullable=True)  # Nullable для збереження історії після видалення гуртка
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    status: Mapped[LessonEventStatus] = mapped_column(
        SQLEnum(LessonEventStatus), default=LessonEventStatus.PLANNED, nullable=False
    )
    
    # Timestamp fields (all UTC)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notify_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Telegram and reliability fields
    teacher_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    send_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    schedule: Mapped["Schedule"] = relationship(
        "Schedule", back_populates="lesson_events"
    )
    club: Mapped["Club"] = relationship("Club", back_populates="lesson_events")
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="lesson_events")
    attendance_records: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="lesson_event"
    )
    payroll_records: Mapped[list["Payroll"]] = relationship(
        "Payroll", back_populates="lesson_event"
    )
    conducted_lesson: Mapped[Optional["ConductedLesson"]] = relationship(
        "ConductedLesson", back_populates="lesson_event", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<LessonEvent(id={self.id}, date={self.date}, "
            f"club='{self.club.name if self.club else 'N/A'}', "
            f"teacher='{self.teacher.full_name if self.teacher else 'N/A'}', "
            f"status={self.status})>"
        )
