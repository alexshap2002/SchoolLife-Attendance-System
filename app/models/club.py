"""Club model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Club(Base):
    """Club model for storing club information."""

    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule", back_populates="club"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment", back_populates="club"
    )
    lesson_events: Mapped[list["LessonEvent"]] = relationship(
        "LessonEvent", back_populates="club"
    )
    conducted_lessons: Mapped[list["ConductedLesson"]] = relationship(
        "ConductedLesson", back_populates="club"
    )

    def __repr__(self) -> str:
        return f"<Club(id={self.id}, name='{self.name}', location='{self.location}')>"
