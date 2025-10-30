"""Schedule enrollment model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScheduleEnrollment(Base):
    """Schedule enrollment model for student-schedule relationships.
    
    This links students to specific schedules (groups within clubs).
    A student can be enrolled in multiple schedules across different clubs.
    """

    __tablename__ = "schedule_enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="schedule_enrollments")
    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="enrolled_students")

    def __repr__(self) -> str:
        return (
            f"<ScheduleEnrollment(id={self.id}, "
            f"student='{self.student.full_name if self.student else 'N/A'}', "
            f"schedule_id={self.schedule_id})>"
        )
