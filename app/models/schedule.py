"""Schedule model."""

from datetime import datetime, time
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Schedule(Base):
    """Schedule model for storing weekly lesson schedules."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    club_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clubs.id"), nullable=True)  # Nullable для збереження історії після видалення гуртка
    weekday: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 1=Monday, 2=Tuesday, ..., 5=Friday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    group_name: Mapped[str] = mapped_column(String(100), nullable=True, default="Група 1")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    club: Mapped["Club"] = relationship("Club", back_populates="schedules")
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="schedules")
    lesson_events: Mapped[list["LessonEvent"]] = relationship(
        "LessonEvent", back_populates="schedule"
    )
    enrolled_students: Mapped[list["ScheduleEnrollment"]] = relationship(
        "ScheduleEnrollment", back_populates="schedule"
    )
    bot_schedule: Mapped[Optional["BotSchedule"]] = relationship(
        "BotSchedule", back_populates="schedule", uselist=False
    )

    def __repr__(self) -> str:
        weekday_names = {
            1: "Понеділок",
            2: "Вівторок",
            3: "Середа",
            4: "Четвер",
            5: "П'ятниця",
        }
        return (
            f"<Schedule(id={self.id}, club='{self.club.name if self.club else 'N/A'}', "
            f"weekday='{weekday_names.get(self.weekday, self.weekday)}', "
            f"time={self.start_time}, active={self.active})>"
        )
