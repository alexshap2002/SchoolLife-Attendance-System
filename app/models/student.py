"""Student model."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, Integer, String, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Student(Base):
    """Student model for storing student information."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # TODO: Add migration  # 'male' or 'female'
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_child: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone_mother: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_father: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    benefits_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_row_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Додаткові поля для повної анкети
    settlement_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Село/СМТ/Місто
    father_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # ПІБ батька
    mother_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # ПІБ матері
    
    # Додаткова інформація про пільги
    benefit_other: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Інші пільги
    
    # Пільги (окремі колонки для зручності фільтрування)
    benefit_low_income: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Малозабезпечені
    benefit_large_family: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Багатодітні
    benefit_military_family: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Сім'я ЗСУ
    benefit_internally_displaced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # ВПО
    benefit_orphan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Сирота/під опікою
    benefit_disability: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Дитина з інвалідністю
    benefit_social_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # СЖО
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    enrollments = relationship("Enrollment", back_populates="student")
    schedule_enrollments = relationship("ScheduleEnrollment", back_populates="student")
    attendance_records = relationship("Attendance", back_populates="student")

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name='{self.first_name} {self.last_name}')>"

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def benefits_list(self) -> list[str]:
        """Get list of benefits that this student has."""
        benefits = []
        if self.benefit_low_income:
            benefits.append("Малозабезпечені")
        if self.benefit_large_family:
            benefits.append("Багатодітні")
        if self.benefit_military_family:
            benefits.append("Сім'я ЗСУ")
        if self.benefit_internally_displaced:
            benefits.append("ВПО")
        if self.benefit_orphan:
            benefits.append("Дитина сирота, напівсирота, під опікою")
        if self.benefit_disability:
            benefits.append("Дитина з інвалідністю")
        if self.benefit_social_risk:
            benefits.append("СЖО")
        if self.benefit_other:
            benefits.append(self.benefit_other)
        return benefits
    
    @property
    def benefits_text(self) -> str:
        """Returns benefits as a formatted string."""
        benefits = self.benefits_list
        if not benefits:
            return "Немає пільг"
        return ", ".join(benefits)
    
    @property
    def has_any_benefits(self) -> bool:
        """Check if student has any benefits."""
        return (
            self.benefit_low_income or
            self.benefit_large_family or
            self.benefit_military_family or
            self.benefit_internally_displaced or
            self.benefit_orphan or
            self.benefit_disability or
            self.benefit_social_risk or
            bool(self.benefit_other)
        )