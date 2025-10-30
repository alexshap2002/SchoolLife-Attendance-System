"""Admin web interface routes."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import DbSession
# Temporary bypass for testing - remove AdminUser dependency
from app.models import Student, Teacher, Club, Schedule, Enrollment, ScheduleEnrollment, PayRate, Payroll, LessonEvent, ConductedLesson, Attendance

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Admin dashboard."""
    # Get basic stats
    students_count = len((await db.execute(select(Student))).scalars().all())
    teachers_count = len((await db.execute(select(Teacher))).scalars().all())
    clubs_count = len((await db.execute(select(Club))).scalars().all())
    schedules_count = len((await db.execute(select(Schedule).where(Schedule.active == True))).scalars().all())
    
    context = {
        "request": request,
        "title": "Панель адміністратора",
        "stats": {
            "students": students_count,
            "teachers": teachers_count,
            "clubs": clubs_count,
            "schedules": schedules_count,
        }
    }
    
    return templates.TemplateResponse("admin/dashboard.html", context)


@router.get("/students", response_class=HTMLResponse)
async def admin_students(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Students management page."""
    result = await db.execute(
        select(Student).order_by(Student.first_name, Student.last_name)
    )
    students = result.scalars().all()
    
    context = {
        "request": request,
        "title": "Учні",
        "students": students,
    }
    
    return templates.TemplateResponse("admin/students.html", context)


@router.get("/students_new", response_class=HTMLResponse)
async def admin_students_new(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """New students management page with extended functionality."""
    context = {
        "request": request,
        "title": "Управління учнями (розширена версія)",
    }
    
    return templates.TemplateResponse("admin/students_new.html", context)


@router.get("/students/{student_id}/full", response_class=HTMLResponse)
async def admin_student_full_info(
    request: Request,
    student_id: int,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Full student information page."""
    result = await db.execute(
        select(Student).where(Student.id == student_id)
        .options(
            selectinload(Student.enrollments).selectinload(Enrollment.club),
            selectinload(Student.schedule_enrollments).selectinload(ScheduleEnrollment.schedule).selectinload(Schedule.club),
            selectinload(Student.schedule_enrollments).selectinload(ScheduleEnrollment.schedule).selectinload(Schedule.teacher),
            selectinload(Student.attendance_records).selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
        )
    )
    student = result.scalar_one_or_none()
    
    if not student:
        # Redirect to students list if not found
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin/students", status_code=404)
    
    context = {
        "request": request,
        "title": f"Повна інформація про учня: {student.full_name}",
        "student": student,
    }
    
    return templates.TemplateResponse("admin/student_full.html", context)


@router.get("/analytics", response_class=HTMLResponse)
async def admin_analytics(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Analytics page with Google Sheets style attendance view."""
    
    # Отримуємо всі гуртки для фільтра
    result = await db.execute(
        select(Club).order_by(Club.name)
    )
    clubs = result.scalars().all()
    
    context = {
        "request": request,
        "title": "Аналітика",
        "clubs": clubs,
    }
    
    return templates.TemplateResponse("admin/analytics.html", context)


@router.get("/audit", response_class=HTMLResponse)
async def admin_audit(
    request: Request,
    # db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Audit log page."""
    context = {
        "request": request,
        "title": "Історія змін",
    }
    return templates.TemplateResponse("admin/audit.html", context)


@router.get("/statistics", response_class=HTMLResponse)
async def admin_statistics(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Advanced statistics page with comprehensive analytics and time-based filtering."""
    
    # Отримуємо базові дані для фільтрів
    clubs_result = await db.execute(select(Club).order_by(Club.name))
    clubs = clubs_result.scalars().all()
    
    teachers_result = await db.execute(select(Teacher).where(Teacher.active == True).order_by(Teacher.full_name))
    teachers = teachers_result.scalars().all()
    
    context = {
        "request": request,
        "title": "Статистика",
        "clubs": clubs,
        "teachers": teachers,
    }
    
    return templates.TemplateResponse("admin/statistics.html", context)


@router.get("/teachers", response_class=HTMLResponse)
async def admin_teachers(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Teachers management page."""
    result = await db.execute(
        select(Teacher).order_by(Teacher.full_name)
    )
    teachers = result.scalars().all()
    
    context = {
        "request": request,
        "title": "Вчителі",
        "teachers": teachers,
    }
    
    return templates.TemplateResponse("admin/teachers.html", context)


@router.get("/clubs", response_class=HTMLResponse)
async def admin_clubs(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Clubs management page."""
    # Дані завантажуються через JavaScript API, тому не передаємо clubs через template
    context = {
        "request": request,
        "title": "Гуртки",
    }
    
    return templates.TemplateResponse("admin/clubs.html", context)


@router.get("/schedules", response_class=HTMLResponse)
async def admin_schedules(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Schedules management page."""
    result = await db.execute(
        select(Schedule)
        .options(
            selectinload(Schedule.club),
            selectinload(Schedule.teacher),
        )
        .order_by(Schedule.weekday, Schedule.start_time)
    )
    schedules = result.scalars().all()
    
    context = {
        "request": request,
        "title": "Розклад",
        "schedules": schedules,
    }
    
    return templates.TemplateResponse("admin/schedules.html", context)


@router.get("/bot", response_class=HTMLResponse)
async def admin_bot(
    request: Request,
    # admin: AdminUser,  # Temporary bypass
):
    """Bot management page."""
    context = {
        "request": request,
        "title": "TG Бот",
    }
    
    return templates.TemplateResponse("admin/bot.html", context)


@router.get("/automations", response_class=HTMLResponse)
async def admin_automations(
    request: Request,
    # admin: AdminUser,  # Temporary bypass
):
    """Automations management page."""
    context = {
        "request": request,
        "title": "Додаткова автоматизація",
    }
    
    return templates.TemplateResponse("admin/automations.html", context)


@router.get("/enrollments", response_class=HTMLResponse)
async def admin_enrollments(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Enrollments management page."""
    result = await db.execute(
        select(Enrollment)
        .options(
            selectinload(Enrollment.student),
            selectinload(Enrollment.club),
        )
        .order_by(Enrollment.student_id, Enrollment.is_primary.desc())
    )
    enrollments = result.scalars().all()
    
    context = {
        "request": request,
        "title": "Записи",
        "enrollments": enrollments,
    }
    
    return templates.TemplateResponse("admin/enrollments.html", context)


@router.get("/payroll", response_class=HTMLResponse)
async def admin_payroll(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Payroll management page."""
    result = await db.execute(
        select(Payroll)
        .options(
            selectinload(Payroll.teacher),
            selectinload(Payroll.lesson_event).selectinload(LessonEvent.club),
        )
        .order_by(Payroll.created_at.desc())
    )
    payroll_records = result.scalars().all()
    
    context = {
        "request": request,
        "title": "Зарплати",
        "payroll_records": payroll_records,
    }
    
    return templates.TemplateResponse("admin/payroll.html", context)


@router.get("/conducted_lessons", response_class=HTMLResponse)
async def admin_conducted_lessons(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Conducted lessons management page."""
    context = {
        "request": request,
        "title": "Проведені уроки",
    }
    
    return templates.TemplateResponse("admin/conducted_lessons.html", context)


@router.get("/pay_rates", response_class=HTMLResponse)
async def admin_pay_rates(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Pay rates management page."""
    # Завантажуємо тарифи
    pay_rates_result = await db.execute(
        select(PayRate)
        .options(selectinload(PayRate.teacher))
        .order_by(PayRate.teacher_id, PayRate.active_from.desc())
    )
    pay_rates = pay_rates_result.scalars().all()
    
    # Завантажуємо вчителів для select
    teachers_result = await db.execute(
        select(Teacher)
        .where(Teacher.active == True)
        .order_by(Teacher.full_name)
    )
    teachers = teachers_result.scalars().all()
    
    context = {
        "request": request,
        "title": "Тарифи",
        "pay_rates": pay_rates,
        "teachers": teachers,
    }
    
    return templates.TemplateResponse("admin/pay_rates.html", context)


@router.get("/attendance", response_class=HTMLResponse)
async def admin_attendance(
    request: Request,
    db: DbSession,
    # admin: AdminUser,  # Temporary bypass
):
    """Attendance management page."""
    # Тут буде логіка завантаження записів відвідуваності
    # Поки що просто рендеримо шаблон
    context = {
        "request": request,
        "title": "Відвідуваність",
    }
    
    return templates.TemplateResponse("admin/attendance.html", context)


@router.get("/test-schedule", response_class=HTMLResponse)
async def test_schedule_page(request: Request):
    """Test schedule creation page."""
    return templates.TemplateResponse("test_schedule.html", {"request": request})
