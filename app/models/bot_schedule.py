"""Bot schedule model for automatic notifications."""

from datetime import datetime, time
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Time, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BotSchedule(Base):
    """Model for automatic bot notifications schedule."""
    
    __tablename__ = "bot_schedules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Зв'язок з розкладом занять
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedules.id"), nullable=False)
    
    # Налаштування розсилки
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    offset_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Зсув від початку заняття (+ або -)
    custom_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)  # Точний час розсилки (якщо задано, offset_minutes ігнорується)
    
    # Додаткові налаштування
    custom_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Кастомне повідомлення
    
    # Метадані
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Зв'язки
    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="bot_schedule")
    
    def __repr__(self) -> str:
        return f"<BotSchedule(id={self.id}, schedule_id={self.schedule_id}, enabled={self.enabled}, offset={self.offset_minutes})>"
    
    @property
    def notification_time_description(self) -> str:
        """Повертає опис часу розсилки."""
        if self.custom_time:
            return f"О {self.custom_time.strftime('%H:%M')}"
        elif self.offset_minutes == 0:
            return "На початку заняття"
        elif self.offset_minutes > 0:
            return f"Через {self.offset_minutes} хв після початку"
        else:
            return f"За {abs(self.offset_minutes)} хв до початку"
    
    @property
    def status_description(self) -> str:
        """Повертає опис статусу."""
        return "Активна" if self.enabled else "Вимкнена"
