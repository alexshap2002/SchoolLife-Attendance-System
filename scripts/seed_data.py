"""Seed database with sample data."""

import asyncio
import sys
from datetime import date, time
from decimal import Decimal

sys.path.append(".")

from app.core.database import AsyncSessionLocal
from app.models import (
    Student,
    Teacher,
    Club,
    Schedule,
    Enrollment,
    PayRate,
    PayRateType,
)


async def seed_data():
    """Seed database with sample data."""
    async with AsyncSessionLocal() as db:
        # Create teachers
        teachers = [
            Teacher(
                full_name="Іван Петренко",
                tg_username="ivan_petrenko",
                active=True,
            ),
            Teacher(
                full_name="Марія Іваненко",
                tg_username="maria_ivanenko", 
                active=True,
            ),
            Teacher(
                full_name="Сергій Коваленко",
                tg_username="sergiy_kovalenko",
                active=True,
            ),
        ]
        
        for teacher in teachers:
            db.add(teacher)
        
        await db.commit()
        
        # Create clubs
        clubs = [
            Club(
                name="Інформатика (програмування)",
                duration_min=90,
                location="Кабінет 101",
            ),
            Club(
                name="Робототехніка",
                duration_min=90,
                location="Кабінет 102",
            ),
            Club(
                name="Англійська мова",
                duration_min=60,
                location="Кабінет 201",
            ),
            Club(
                name="Українська мова",
                duration_min=60,
                location="Кабінет 202",
            ),
        ]
        
        for club in clubs:
            db.add(club)
        
        await db.commit()
        
        # Create schedules
        schedules = [
            # Monday
            Schedule(
                club_id=1,  # Інформатика
                weekday=1,
                start_time=time(14, 30),
                teacher_id=1,
                active=True,
            ),
            Schedule(
                club_id=3,  # Англійська
                weekday=1,
                start_time=time(16, 30),
                teacher_id=3,
                active=True,
            ),
            # Tuesday
            Schedule(
                club_id=2,  # Робототехніка
                weekday=2,
                start_time=time(15, 0),
                teacher_id=2,
                active=True,
            ),
            # Wednesday
            Schedule(
                club_id=4,  # Українська
                weekday=3,
                start_time=time(14, 0),
                teacher_id=3,
                active=True,
            ),
            Schedule(
                club_id=1,  # Інформатика
                weekday=3,
                start_time=time(16, 0),
                teacher_id=1,
                active=True,
            ),
            # Thursday
            Schedule(
                club_id=2,  # Робототехніка
                weekday=4,
                start_time=time(15, 30),
                teacher_id=2,
                active=True,
            ),
            # Friday
            Schedule(
                club_id=3,  # Англійська
                weekday=5,
                start_time=time(14, 30),
                teacher_id=3,
                active=True,
            ),
        ]
        
        for schedule in schedules:
            db.add(schedule)
        
        await db.commit()
        
        # Create students
        students = [
            Student(
                first_name="Олександр",
                last_name="Петренко",
                birth_date=date(2010, 5, 15),
                age=13,
                grade="7",
                phone_child="+380501234567",
                location="Київ",
                address="вул. Хрещатик 1",
                parent_name="Петренко Іван Васильович",
                phone_mother="+380501234568",
                phone_father="+380501234569",
                benefits_json={"багатодітна сім'я": True},
            ),
            Student(
                first_name="Марія",
                last_name="Іваненко",
                birth_date=date(2011, 3, 22),
                age=12,
                grade="6",
                phone_child="+380509876543",
                location="Київ",
                address="вул. Лесі Українки 5",
                parent_name="Іваненко Олена Петрівна",
                phone_mother="+380509876544",
                phone_father="+380509876545",
                benefits_json={"малозабезпечена сім'я": True},
            ),
            Student(
                first_name="Дмитро",
                last_name="Коваленко",
                birth_date=date(2009, 11, 8),
                age=14,
                grade="8",
                phone_child="+380505555555",
                location="Київ",
                address="пр. Перемоги 10",
                parent_name="Коваленко Сергій Олександрович",
                phone_mother="+380505555556",
                phone_father="+380505555557",
            ),
            Student(
                first_name="Анна",
                last_name="Сидоренко",
                birth_date=date(2012, 1, 30),
                age=11,
                grade="5",
                phone_child="+380507777777",
                location="Київ",
                address="вул. Володимирська 15",
                parent_name="Сидоренко Тетяна Миколаївна",
                phone_mother="+380507777778",
                phone_father="+380507777779",
            ),
            Student(
                first_name="Максим",
                last_name="Бондаренко",
                birth_date=date(2010, 9, 12),
                age=13,
                grade="7",
                phone_child="+380503333333",
                location="Київ",
                address="вул. Саксаганського 20",
                parent_name="Бондаренко Олександр Іванович",
                phone_mother="+380503333334",
                phone_father="+380503333335",
                benefits_json={"багатодітна сім'я": True, "малозабезпечена сім'я": True},
            ),
        ]
        
        for student in students:
            db.add(student)
        
        await db.commit()
        
        # Create enrollments (primary clubs for students)
        enrollments = [
            Enrollment(student_id=1, club_id=1, is_primary=True),  # Олександр -> Інформатика
            Enrollment(student_id=1, club_id=3, is_primary=False), # Олександр -> Англійська (додатковий)
            Enrollment(student_id=2, club_id=2, is_primary=True),  # Марія -> Робототехніка
            Enrollment(student_id=2, club_id=3, is_primary=False), # Марія -> Англійська (додатковий)
            Enrollment(student_id=3, club_id=1, is_primary=True),  # Дмитро -> Інформатика
            Enrollment(student_id=3, club_id=2, is_primary=False), # Дмитро -> Робототехніка (додатковий)
            Enrollment(student_id=4, club_id=3, is_primary=True),  # Анна -> Англійська
            Enrollment(student_id=4, club_id=4, is_primary=False), # Анна -> Українська (додатковий)
            Enrollment(student_id=5, club_id=4, is_primary=True),  # Максим -> Українська
        ]
        
        for enrollment in enrollments:
            db.add(enrollment)
        
        await db.commit()
        
        # Create pay rates for teachers
        pay_rates = [
            PayRate(
                teacher_id=1,
                rate_type=PayRateType.PER_PRESENT,
                amount_decimal=Decimal("50.00"),  # 50 грн за кожного присутнього
                active_from=date(2024, 1, 1),
            ),
            PayRate(
                teacher_id=2,
                rate_type=PayRateType.PER_LESSON,
                amount_decimal=Decimal("300.00"),  # 300 грн за заняття
                active_from=date(2024, 1, 1),
            ),
            PayRate(
                teacher_id=3,
                rate_type=PayRateType.PER_PRESENT,
                amount_decimal=Decimal("40.00"),  # 40 грн за кожного присутнього
                active_from=date(2024, 1, 1),
            ),
        ]
        
        for pay_rate in pay_rates:
            db.add(pay_rate)
        
        await db.commit()
        
        print("✅ Sample data seeded successfully!")
        print(f"Created:")
        print(f"  - {len(teachers)} teachers")
        print(f"  - {len(clubs)} clubs")
        print(f"  - {len(schedules)} schedules")
        print(f"  - {len(students)} students")
        print(f"  - {len(enrollments)} enrollments")
        print(f"  - {len(pay_rates)} pay rates")


if __name__ == "__main__":
    asyncio.run(seed_data())
