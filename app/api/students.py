"""Students API endpoints."""

from datetime import date, datetime
from typing import List, Optional
import io
import pandas as pd
import logging

from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.api.dependencies import AdminUser, DbSession
from app.models import Student, Enrollment, Club, Attendance, ScheduleEnrollment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/students", tags=["students"])


class StudentCreate(BaseModel):
    """Student creation model."""

    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    age: Optional[int] = None
    grade: Optional[str] = None
    phone_child: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    parent_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    phone_mother: Optional[str] = None
    phone_father: Optional[str] = None
    settlement_type: Optional[str] = None
    
    # Пільги
    benefit_low_income: bool = False
    benefit_large_family: bool = False
    benefit_military_family: bool = False
    benefit_internally_displaced: bool = False
    benefit_orphan: bool = False
    benefit_disability: bool = False
    benefit_social_risk: bool = False
    benefit_other: Optional[str] = None
    
    benefits_json: Optional[dict] = None
    raw_row_id: Optional[str] = None


class StudentUpdate(BaseModel):
    """Student update model."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    age: Optional[int] = None
    grade: Optional[str] = None
    phone_child: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    parent_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    phone_mother: Optional[str] = None
    phone_father: Optional[str] = None
    settlement_type: Optional[str] = None
    
    # Пільги
    benefit_low_income: Optional[bool] = None
    benefit_large_family: Optional[bool] = None
    benefit_military_family: Optional[bool] = None
    benefit_internally_displaced: Optional[bool] = None
    benefit_orphan: Optional[bool] = None
    benefit_disability: Optional[bool] = None
    benefit_social_risk: Optional[bool] = None
    benefit_other: Optional[str] = None
    
    benefits_json: Optional[dict] = None


class StudentResponse(BaseModel):
    """Student response model."""

    id: int
    first_name: str
    last_name: str
    birth_date: Optional[date]
    age: Optional[int]
    grade: Optional[str]
    phone_child: Optional[str]
    location: Optional[str]
    address: Optional[str]
    parent_name: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    phone_mother: Optional[str]
    phone_father: Optional[str]
    settlement_type: Optional[str]
    
    # Пільги
    benefit_low_income: bool
    benefit_large_family: bool
    benefit_military_family: bool
    benefit_internally_displaced: bool
    benefit_orphan: bool
    benefit_disability: bool
    benefit_social_risk: bool
    benefit_other: Optional[str]
    
    benefits_json: Optional[dict]
    raw_row_id: Optional[str]
    created_at: datetime

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    class Config:
        from_attributes = True


@router.get("/", response_model=List[StudentResponse])
async def get_students(
    db: DbSession,
    admin: AdminUser,
    skip: int = 0,
    limit: int = 100,
) -> List[Student]:
    """Get all students."""
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.enrollments))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    db: DbSession,
    admin: AdminUser,
) -> Student:
    """Get student by ID."""
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.enrollments))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    return student


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    db: DbSession,
    admin: AdminUser,
) -> Student:
    """Create new student."""
    student = Student(**student_data.model_dump())
    db.add(student)
    await db.flush()  # Flush щоб отримати ID
    
    # 📝 AUDIT LOG: Створення учня (ПЕРЕД commit!)
    logger.info(f"🔍 TRYING TO LOG AUDIT for student CREATE: {student.id}")
    try:
        from app.services.audit_service import log_audit
        logger.info(f"🔍 CALLING log_audit for CREATE...")
        result = await log_audit(
            db=db,
            action_type="CREATE",
            entity_type="student",
            entity_id=student.id,
            entity_name=f"{student.first_name} {student.last_name}",
            description=f"Створено нового учня: {student.first_name} {student.last_name}, клас {student.grade or 'не вказано'}",
            user_name="Адміністратор",
            changes={"after": {"first_name": student.first_name, "last_name": student.last_name, "grade": student.grade}}
        )
        logger.info(f"🔍 log_audit CREATE RETURNED: {result}")
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (student CREATE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(student)
    return student


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    student_data: StudentUpdate,
    db: DbSession,
    admin: AdminUser,
) -> Student:
    """Update student."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Зберігаємо старі значення для аудиту
    old_values = {}
    update_data = student_data.model_dump(exclude_unset=True)
    for field in update_data.keys():
        old_values[field] = getattr(student, field, None)
    
    # Update fields
    for field, value in update_data.items():
        setattr(student, field, value)
    
    # 📝 AUDIT LOG: Оновлення учня (ПЕРЕД commit!)
    logger.info(f"🔍 TRYING TO LOG AUDIT for student UPDATE: {student.id}")
    try:
        from app.services.audit_service import log_audit
        changes_desc = ", ".join([f"{k}: {old_values.get(k)} → {v}" for k, v in update_data.items() if old_values.get(k) != v])
        logger.info(f"🔍 CALLING log_audit...")
        result = await log_audit(
            db=db,
            action_type="UPDATE",
            entity_type="student",
            entity_id=student.id,
            entity_name=f"{student.first_name} {student.last_name}",
            description=f"Оновлено дані учня: {student.first_name} {student.last_name}. Зміни: {changes_desc}",
            user_name="Адміністратор",
            changes={"before": old_values, "after": update_data}
        )
        logger.info(f"🔍 log_audit RETURNED: {result}")
    except Exception as e:
        logger.error(f"❌ AUDIT LOG ERROR (student UPDATE): {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    await db.commit()
    await db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    db: DbSession,
    # admin: AdminUser,  # Тимчасово відключено для тестування
) -> None:
    """Delete student with proper cascade handling."""
    print(f"🔥 DELETE STUDENT CALLED FOR ID: {student_id}")
    
    # Перевіряємо чи існує студент
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Зберігаємо ім'я для аудиту перед видаленням
    student_name = f"{student.first_name} {student.last_name}"
    
    try:
        # 1. Видаляємо attendance records
        await db.execute(
            delete(Attendance).where(Attendance.student_id == student_id)
        )
        
        # 2. Видаляємо enrollments  
        await db.execute(
            delete(Enrollment).where(Enrollment.student_id == student_id)
        )
        
        # 3. Видаляємо schedule enrollments
        await db.execute(
            delete(ScheduleEnrollment).where(ScheduleEnrollment.student_id == student_id)
        )
        
        # 4. Тепер можемо безпечно видалити студента
        await db.delete(student)
        
        # 📝 AUDIT LOG: Видалення учня (ПЕРЕД commit!)
        print(f"🔥🔥🔥 DELETE STUDENT {student_id} - BEFORE AUDIT LOG 🔥🔥🔥")
        logger.info(f"🔍 TRYING TO LOG AUDIT for student DELETE: {student_id}")
        try:
            from app.services.audit_service import log_audit
            logger.info(f"🔍 CALLING log_audit for DELETE...")
            result = await log_audit(
                db=db,
                action_type="DELETE",
                entity_type="student",
                entity_id=student_id,
                entity_name=student_name,
                description=f"Видалено учня: {student_name}",
                user_name="Адміністратор",
                changes={"deleted": {"id": student_id, "name": student_name}}
            )
            logger.info(f"🔍 log_audit DELETE RETURNED: {result}")
        except Exception as e:
            logger.error(f"❌ AUDIT LOG ERROR (student DELETE): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting student: {str(e)}"
        )


@router.get("/template/download")
async def download_students_template(
    # admin: AdminUser,  # Поки що відключаємо авторизацію для тестування
):
    """Download Excel template for students import."""
    # Створюємо шаблон Excel файлу
    template_data = {
        # === ОСНОВНА ІНФОРМАЦІЯ ПРО ДИТИНУ ===
        "Ім'я *": ["Іван", "Марія", "Олександр", "Катерина", "Михайло"],
        "Прізвище *": ["Петренко", "Іваненко", "Коваленко", "Морозенко", "Сидоренко"],
        "День народження (YYYY-MM-DD)": ["2010-05-15", "2011-03-22", "2009-08-10", "2012-12-03", "2008-07-25"],
        "Вік": [13, 12, 14, 11, 15],
        "Клас": ["7-А", "6-Б", "8-В", "5-Г", "9-А"],
        "Телефон дитини": ["+380501234567", "+380507654321", "+380509876543", "+380632345678", "+380445556677"],
        
        # === АДРЕСА ТА МІСЦЕ ПРОЖИВАННЯ ===
        "Тип населеного пункту": ["місто", "місто", "селище міського типу", "село", "місто"],
        "Місце проживання": ["Київ", "Львів", "Брусилів", "Макарів", "Житомир"],
        "Адреса проживання": ["вул. Хрещатик 1, кв. 15", "вул. Ринок 5", "вул. Центральна 10", "вул. Миру 3, кв. 7", "пр. Перемоги 45, кв. 102"],
        
        # === ІНФОРМАЦІЯ ПРО БАТЬКІВ ===
        "ПІБ батька (повністю)": ["Петренко Олексій Іванович", "—", "Коваленко Микола Васильович", "Морозенко Андрій Петрович", "Сидоренко Володимир Олегович"],
        "ПІБ матері (повністю)": ["Петренко Оксана Миколаївна", "Іваненко Ольга Петрівна", "Коваленко Тетяна Олександрівна", "Морозенко Світлана Іванівна", "Сидоренко Наталія Василівна"],
        "Телефон матері": ["+380509876543", "+380502345678", "+380501112233", "+380674445566", "+380637778899"],
        "Телефон батька": ["+380671234567", "—", "+380672223344", "+380505556677", "+380668889911"],
        
        # === ПІЛЬГИ ТА СОЦІАЛЬНІ СТАТУСИ ===
        "Малозабезпечені (так/ні)": ["ні", "так", "ні", "так", "ні"],
        "Багатодітні (так/ні)": ["так", "ні", "так", "ні", "так"],
        "Сім'я ЗСУ (так/ні)": ["ні", "так", "ні", "так", "ні"],
        "ВПО (так/ні)": ["ні", "ні", "так", "ні", "ні"],
        "Сирота/під опікою (так/ні)": ["ні", "ні", "ні", "ні", "ні"],
        "Дитина з інвалідністю (так/ні)": ["ні", "ні", "ні", "так", "ні"],
        "Соціальний ризик (так/ні)": ["ні", "так", "ні", "ні", "ні"],
        "Інші пільги та додаткова інформація": ["Відмінник навчання", "Дитина учасника АТО, має алергію на горіхи", "Активний учасник шкільних заходів", "Дитина з особливими освітніми потребами, потребує індивідуального підходу", "Має обмеження по фізичних навантаженнях"]
    }
    
    df = pd.DataFrame(template_data)
    
    # Створюємо Excel файл в пам'яті
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Учні', index=False)
        
        # Додаємо лист з інструкціями
        instructions = pd.DataFrame({
            'ІНСТРУКЦІЇ ДЛЯ ЗАПОВНЕННЯ АНКЕТИ УЧНІВ': [
                '1. ОБОВ\'ЯЗКОВІ ПОЛЯ (*): Ім\'я та Прізвище є обов\'язковими для заповнення',
                '2. ДАТА НАРОДЖЕННЯ: Вказуйте у форматі YYYY-MM-DD (наприклад: 2010-05-15)',
                '3. ТЕЛЕФОНИ: У форматі +380XXXXXXXXX або залиште порожнім якщо немає',
                '4. АДРЕСА: Вкажіть повну адресу включно з квартирою (якщо є)',
                '5. ТИП НАСЕЛЕНОГО ПУНКТУ: село, селище міського типу, місто',
                '6. ПІЛЬГИ: Пишіть "так" або "ні" для кожного типу пільг',
                '7. ДОДАТКОВА ІНФОРМАЦІЯ: Особливі примітки (алергії, обмеження, особливості)',
                '8. ІНШІ ПІЛЬГИ: Текстовий опис додаткових пільг або статусів',
                '9. Видаліть всі приклади перед заповненням власними даними',
                '10. Можна додавати нові рядки з учнями (скопіюйте формат)',
                '11. НЕ ЗМІНЮЙТЕ назви колонок - це зламає імпорт!',
                '12. Якщо немає інформації - залиште порожнім або напишіть "—"'
            ]
        })
        
        # Додаємо лист з поясненнями по пільгах
        benefits_info = pd.DataFrame({
            'ТИПИ ПІЛЬГ ТА ЇХ ЗНАЧЕННЯ': [
                'Малозабезпечені - сім\'ї з низьким рівнем доходу',
                'Багатодітні - сім\'ї з трьома і більше дітьми',
                'Сім\'я ЗСУ - діти військовослужбовців ЗСУ',
                'ВПО - внутрішньо переміщені особи',
                'Сирота/під опікою - діти-сироти або під опікою',
                'Дитина з інвалідністю - діти з особливими потребами',
                'Соціальний ризик - діти в складних життєвих обставинах',
                'Інші пільги - додаткові статуси або пільги (опишіть текстом)'
            ]
        })
        instructions.to_excel(writer, sheet_name='Інструкції', index=False)
        benefits_info.to_excel(writer, sheet_name='Пояснення пільг', index=False)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=shablon_uchniv.xlsx"}
    )


class ImportStudentsResponse(BaseModel):
    """Response for students import."""
    success: bool
    message: str
    created_count: int
    skipped_count: int
    errors: List[str]


@router.post("/import", response_model=ImportStudentsResponse)
async def import_students(
    db: DbSession,
    file: UploadFile = File(...),
    skip_duplicates: bool = True,
    # admin: AdminUser,  # Поки що відключаємо авторизацію для тестування
) -> ImportStudentsResponse:
    """Import students from Excel file."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be Excel format (.xlsx or .xls)"
        )
    
    try:
        # Читаємо Excel файл
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name='Учні')
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        # Мапінг колонок - ОЧИЩЕНА ІНФОРМАЦІЯ УЧНІВ (без зайвих полів батьків)
        column_mapping = {
            "Ім'я *": "first_name",
            "Прізвище *": "last_name", 
            "День народження (YYYY-MM-DD)": "birth_date",
            "Вік": "age",
            "Клас": "grade",
            "Телефон дитини": "phone_child",
            "Місце проживання": "location",
            "Адреса проживання": "address",
            "ПІБ батька (повністю)": "father_name",
            "ПІБ матері (повністю)": "mother_name",
            "Телефон матері": "phone_mother",
            "Телефон батька": "phone_father",
            # 📍 ДЕТАЛЬНА АДРЕСА
            "Тип населеного пункту": "settlement_type",
            # 🏆 ПІЛЬГИ ТА СТАТУСИ
            "Малозабезпечені (так/ні)": "benefit_low_income",
            "Багатодітні (так/ні)": "benefit_large_family", 
            "Сім'я ЗСУ (так/ні)": "benefit_military_family",
            "ВПО (так/ні)": "benefit_internally_displaced",
            "Сирота/під опікою (так/ні)": "benefit_orphan",
            "Дитина з інвалідністю (так/ні)": "benefit_disability",
            "Соціальний ризик (так/ні)": "benefit_social_risk",
            "Інші пільги та додаткова інформація": "benefit_other"  # Включає як пільги так і примітки
        }
        
        for index, row in df.iterrows():
            try:
                # Перевіряємо обов'язкові поля
                if pd.isna(row.get("Ім'я *")) or pd.isna(row.get("Прізвище *")):
                    errors.append(f"Рядок {index + 2}: Ім'я та прізвище є обов'язковими")
                    continue
                
                first_name = str(row["Ім'я *"]).strip()
                last_name = str(row["Прізвище *"]).strip()
                
                # Перевіряємо дублікати
                if skip_duplicates:
                    result = await db.execute(
                        select(Student).where(
                            Student.first_name == first_name,
                            Student.last_name == last_name
                        )
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        skipped_count += 1
                        continue
                
                # Створюємо дані для студента
                student_data = {
                    "first_name": first_name,
                    "last_name": last_name
                }
                
                # Додаємо опціональні поля
                for excel_col, db_field in column_mapping.items():
                    if excel_col in ["Ім'я *", "Прізвище *"]:
                        continue
                        
                    value = row.get(excel_col)
                    if not pd.isna(value):
                        if db_field == "birth_date":
                            # Обробляємо дату народження
                            if isinstance(value, str):
                                try:
                                    student_data[db_field] = datetime.strptime(value, "%Y-%m-%d").date()
                                except ValueError:
                                    errors.append(f"Рядок {index + 2}: Неправильний формат дати народження")
                                    continue
                            elif hasattr(value, 'date'):
                                student_data[db_field] = value.date()
                        elif db_field == "age":
                            student_data[db_field] = int(value) if not pd.isna(value) else None
                        elif db_field.startswith("benefit_") and db_field != "benefit_other":
                            # Обробляємо булеві поля пільг
                            if isinstance(value, str):
                                value_lower = value.lower().strip()
                                student_data[db_field] = value_lower in ["так", "yes", "true", "1", "+"]
                            else:
                                student_data[db_field] = bool(value)
                        else:
                            student_data[db_field] = str(value).strip() if str(value).strip() else None
                
                # Створюємо студента
                student = Student(**student_data)
                db.add(student)
                created_count += 1
                
            except Exception as e:
                errors.append(f"Рядок {index + 2}: Помилка обробки - {str(e)}")
                continue
        
        # Зберігаємо зміни
        await db.commit()
        
        return ImportStudentsResponse(
            success=True,
            message=f"Імпорт завершено успішно. Створено: {created_count}, пропущено: {skipped_count}",
            created_count=created_count,
            skipped_count=skipped_count,
            errors=errors
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Помилка при імпорті файлу: {str(e)}"
        )


@router.get("/export/excel")
async def export_students_excel(
    db: DbSession,
    # admin: AdminUser,  # Поки що відключаємо авторизацію для тестування
) -> StreamingResponse:
    """Export all students data to Excel with full information."""
    
    try:
        # Отримуємо всіх учнів з пов'язаними даними
        result = await db.execute(
            select(Student)
            .options(
                selectinload(Student.enrollments).selectinload(Enrollment.club),
                selectinload(Student.attendance_records).selectinload(Attendance.lesson_event)
            )
            .order_by(Student.last_name, Student.first_name)
        )
        students = result.scalars().all()
        
        if not students:
            raise HTTPException(status_code=404, detail="No students found")
        
        # Підготуємо дані для Excel
        students_data = []
        for student in students:
            # Рахуємо статистику відвідуваності
            total_attendance = len(student.attendance_records)
            present_count = sum(1 for att in student.attendance_records if att.status.value == 'PRESENT')
            attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
            
            # Отримуємо список гуртків
            clubs_list = ", ".join([enrollment.club.name for enrollment in student.enrollments])
            
            students_data.append({
                # === ОСНОВНА ІНФОРМАЦІЯ ===
                "Прізвище": student.last_name,
                "Ім'я": student.first_name,
                "Дата народження": student.birth_date.strftime("%d.%m.%Y") if student.birth_date else "—",
                "Вік": student.age or "—",
                "Клас": student.grade or "—",
                
                # === КОНТАКТНА ІНФОРМАЦІЯ ===
                "Телефон дитини": student.phone_child or "—",
                "Телефон матері": student.phone_mother or "—",
                "Телефон батька": student.phone_father or "—",
                
                # === ІНФОРМАЦІЯ ПРО БАТЬКІВ ===
                "ПІБ батьків": student.parent_name or "—",
                "Ім'я батька": student.father_name or "—",
                "Ім'я матері": student.mother_name or "—",
                
                # === АДРЕСА ===
                "Тип населеного пункту": student.settlement_type or "—",
                "Місце проживання": student.location or "—",
                "Повна адреса": student.address or "—",
                
                # === ПІЛЬГИ ===
                "Малозабезпечені": "Так" if student.benefit_low_income else "Ні",
                "Багатодітні": "Так" if student.benefit_large_family else "Ні",
                "Сім'я ЗСУ": "Так" if student.benefit_military_family else "Ні",
                "ВПО": "Так" if student.benefit_internally_displaced else "Ні",
                "Сирота/під опікою": "Так" if student.benefit_orphan else "Ні",
                "Дитина з інвалідністю": "Так" if student.benefit_disability else "Ні",
                "Соціальний ризик": "Так" if student.benefit_social_risk else "Ні",
                "Інші пільги": student.benefit_other or "—",
                
                # === НАВЧАННЯ ===
                "Гуртки": clubs_list or "—",
                "Всього занять": total_attendance,
                "Присутній": present_count,
                "Відсоток відвідуваності": f"{attendance_rate:.1f}%",
                
                # === СИСТЕМНА ІНФОРМАЦІЯ ===
                "Дата реєстрації": student.created_at.strftime("%d.%m.%Y %H:%M") if student.created_at else "—"
            })
        
        # Створюємо DataFrame
        df = pd.DataFrame(students_data)
        
        # Створюємо Excel файл в пам'яті
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Учні - Повна інформація', index=False)
            
            # Налаштовуємо ширину колонок
            worksheet = writer.sheets['Учні - Повна інформація']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Додаємо лист зі статистикою
            summary_data = {
                'Статистика': [
                    'Загальна кількість учнів',
                    'Учні з пільгами',
                    'Учні без пільг', 
                    'Учні з телефонами',
                    'Учні в гуртках',
                    'Середній відсоток відвідуваності'
                ],
                'Значення': [
                    len(students),
                    len([s for s in students if any([
                        s.benefit_low_income, s.benefit_large_family, s.benefit_military_family,
                        s.benefit_internally_displaced, s.benefit_orphan, s.benefit_disability,
                        s.benefit_social_risk, s.benefit_other
                    ])]),
                    len([s for s in students if not any([
                        s.benefit_low_income, s.benefit_large_family, s.benefit_military_family,
                        s.benefit_internally_displaced, s.benefit_orphan, s.benefit_disability,
                        s.benefit_social_risk, s.benefit_other
                    ])]),
                    len([s for s in students if s.phone_child]),
                    len([s for s in students if s.enrollments]),
                    f"{sum(float(data['Відсоток відвідуваності'].rstrip('%')) for data in students_data) / len(students_data):.1f}%" if students_data else "0%"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Статистика', index=False)
        
        output.seek(0)
        
        # Генеруємо ім'я файлу з поточною датою
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"students_full_export_{today}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting students: {str(e)}"
        )
