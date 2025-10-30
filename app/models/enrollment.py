"""Enrollment model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Enrollment(Base):
    """Enrollment model for student-club relationships."""

    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Exactly one primary per student
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="enrollments")
    club: Mapped["Club"] = relationship("Club", back_populates="enrollments")

    def __repr__(self) -> str:
        return (
            f"<Enrollment(id={self.id}, "
            f"student='{self.student.full_name if self.student else 'N/A'}', "
            f"club='{self.club.name if self.club else 'N/A'}', "
            f"is_primary={self.is_primary})>"
        )
