"""Conducted lesson model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, Boolean, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConductedLesson(Base):
    """Conducted lesson model for tracking completed lessons."""

    __tablename__ = "conducted_lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Зв'язки з основними сутностями
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("teachers.id"), nullable=False)
    club_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("clubs.id"), nullable=True)  # Nullable для збереження історії після видалення гуртка
    lesson_event_id: Mapped[int] = mapped_column(Integer, ForeignKey("lesson_events.id"), nullable=False)
    
    # Інформація про урок
    lesson_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lesson_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Статистика присутності
    total_students: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    present_students: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    absent_students: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Додаткова інформація
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lesson_topic: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Статус та час створення
    is_salary_calculated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    teacher = relationship("Teacher", back_populates="conducted_lessons")
    club = relationship("Club", back_populates="conducted_lessons")
    lesson_event = relationship("LessonEvent", back_populates="conducted_lesson")

    def __repr__(self) -> str:
        return f"<ConductedLesson(id={self.id}, teacher_id={self.teacher_id}, club_id={self.club_id}, date={self.lesson_date}, present={self.present_students})>"

    @property
    def attendance_rate(self) -> float:
        """Calculate attendance rate percentage."""
        if self.total_students == 0:
            return 0.0
        return (self.present_students / self.total_students) * 100

    @property
    def is_valid_for_salary(self) -> bool:
        """Check if lesson is valid for salary calculation (at least 1 present student)."""
        return self.present_students > 0

    @property
    def lesson_summary(self) -> str:
        """Get lesson summary string."""
        return f"{self.lesson_date.strftime('%d.%m.%Y')} - {self.present_students}/{self.total_students} учнів"
