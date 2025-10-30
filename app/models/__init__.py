"""Database models for the School of Life attendance system."""

from app.models.attendance import Attendance, AttendanceStatus
from app.models.audit_log import AuditLog
from app.models.bot_schedule import BotSchedule
from app.models.calendar_exception import CalendarException
from app.models.club import Club
from app.models.enrollment import Enrollment
from app.models.lesson_event import LessonEvent, LessonEventStatus
from app.models.pay_rate import PayRate, PayRateType
from app.models.payroll import Payroll, PayrollBasis
from app.models.conducted_lesson import ConductedLesson
from app.models.schedule import Schedule
from app.models.schedule_enrollment import ScheduleEnrollment
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.automations import AdminAutomation, AutomationLog

__all__ = [
    "Student",
    "Teacher",
    "Club",
    "Schedule",
    "ScheduleEnrollment",
    "BotSchedule",
    "Enrollment",
    "CalendarException",
    "LessonEvent",
    "LessonEventStatus",
    "Attendance",
    "AttendanceStatus",
    "PayRate",
    "PayRateType",
    "Payroll",
    "PayrollBasis",
    "ConductedLesson",
    "AuditLog",
    "AdminAutomation",
    "AutomationLog",
]
