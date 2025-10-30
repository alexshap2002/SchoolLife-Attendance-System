"""Attendance model."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, BigInteger, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AttendanceStatus(str, Enum):
    """Attendance status enum."""

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class Attendance(Base):
    """Attendance model for tracking student attendance."""

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint(
            "lesson_event_id", "student_id", 
            name="attendance_lesson_student_unique"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lesson_event_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_events.id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        SQLEnum(AttendanceStatus), nullable=False
    )
    marked_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )  # Who marked attendance (Telegram Chat ID or teacher ID)
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    lesson_event: Mapped["LessonEvent"] = relationship(
        "LessonEvent", back_populates="attendance_records"
    )
    student: Mapped["Student"] = relationship(
        "Student", back_populates="attendance_records"
    )

    def __repr__(self) -> str:
        return (
            f"<Attendance(id={self.id}, "
            f"student='{self.student.full_name if self.student else 'N/A'}', "
            f"status={self.status}, marked_at={self.marked_at})>"
        )
