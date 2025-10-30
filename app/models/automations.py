"""
Моделі для системи автоматизацій адміністратора.
"""

from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, Time, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from app.core.database import Base
from datetime import datetime, time

class AdminAutomation(Base):
    """Налаштування автоматизацій для адміністратора."""
    
    __tablename__ = "admin_automations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основні поля
    name = Column(String(200), nullable=False)
    description = Column(Text)
    automation_type = Column(String(100), nullable=False)  # ABSENT_STUDENTS, BIRTHDAYS, WEEKLY_REPORT, etc.
    
    # Telegram налаштування
    admin_chat_id = Column(BigInteger, nullable=False)  # Telegram Chat ID адміністратора
    
    # Статус
    is_enabled = Column(Boolean, default=True)
    
    # Налаштування часу (для scheduled автоматизацій)
    trigger_time = Column(Time)  # Час відправки (наприклад, 12:00 для днів народження)
    trigger_day = Column(Integer)  # День тижня (0-6, для weekly reports)
    
    # JSON конфігурація для гнучких налаштувань
    config = Column(Text)  # JSON конфігурація автоматизації
    
    # Системні поля
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime)  # Коли остання відправка була


class AutomationLog(Base):
    """Лог виконання автоматизацій."""
    
    __tablename__ = "automation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    automation_id = Column(Integer, nullable=False)  # Зв'язок з AdminAutomation
    
    # Деталі виконання
    triggered_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="SUCCESS")  # SUCCESS, ERROR, SKIPPED
    message = Column(Text)  # Повідомлення яке було відправлено
    error_details = Column(Text)  # Деталі помилки якщо status = ERROR
    
    # Метрики
    students_count = Column(Integer)  # Кількість студентів в звіті
    clubs_count = Column(Integer)    # Кількість гуртків
    execution_time_ms = Column(Integer)  # Час виконання в мілісекундах
