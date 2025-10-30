"""Google Sheets export service."""

import logging
from datetime import datetime
from typing import List, Dict, Any

import gspread
from google.oauth2.service_account import Credentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.settings import settings
from app.models import (
    Student,
    Teacher,
    Club,
    Schedule,
    LessonEvent,
    Attendance,
    Payroll,
)

logger = logging.getLogger(__name__)


class SheetsService:
    """Service for Google Sheets operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = None
        self.spreadsheet = None
    
    def _get_client(self):
        """Get authenticated Google Sheets client."""
        if not self.client:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            
            creds = Credentials.from_service_account_file(
                settings.google_service_account_json_path, scopes=scope
            )
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(settings.sheets_spreadsheet_id)
        
        return self.client
    
    async def sync_all_data(self):
        """Sync all data to Google Sheets."""
        try:
            self._get_client()
            
            await self.sync_students()
            await self.sync_teachers()
            await self.sync_clubs()
            await self.sync_schedules()
            await self.sync_attendance()
            await self.sync_payroll()
            
            logger.info("Successfully synced all data to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing data to Google Sheets: {e}")
    
    async def sync_students(self):
        """Sync students data to Google Sheets."""
        try:
            # Get students data
            result = await self.db.execute(
                select(Student).order_by(Student.id)
            )
            students = result.scalars().all()
            
            # Prepare data for sheets
            headers = [
                "ID",
                "Ім'я",
                "Прізвище",
                "День народження",
                "Вік",
                "Клас",
                "Телефон дитини",
                "Місце проживання",
                "Адреса",
                "ПІБ батьків",
                "Телефон матері",
                "Телефон батька",
                "Пільги",
                "Створено",
            ]
            
            rows = []
            for student in students:
                rows.append([
                    student.id,
                    student.first_name,
                    student.last_name,
                    student.birth_date.isoformat() if student.birth_date else "",
                    student.age or "",
                    student.grade or "",
                    student.phone_child or "",
                    student.location or "",
                    student.address or "",
                    student.parent_name or "",
                    student.phone_mother or "",
                    student.phone_father or "",
                    str(student.benefits_json) if student.benefits_json else "",
                    student.created_at.isoformat(),
                ])
            
            # Update sheet
            self._update_sheet("Students", headers, rows)
            logger.info(f"Synced {len(students)} students to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing students: {e}")
    
    async def sync_teachers(self):
        """Sync teachers data to Google Sheets."""
        try:
            result = await self.db.execute(
                select(Teacher).order_by(Teacher.id)
            )
            teachers = result.scalars().all()
            
            headers = [
                "ID",
                "Повне ім'я",
                "Telegram Chat ID",
                "Telegram Username",
                "Активний",
            ]
            
            rows = []
            for teacher in teachers:
                rows.append([
                    teacher.id,
                    teacher.full_name,
                    teacher.tg_chat_id or "",
                    teacher.tg_username or "",
                    "Так" if teacher.active else "Ні",
                ])
            
            self._update_sheet("Teachers", headers, rows)
            logger.info(f"Synced {len(teachers)} teachers to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing teachers: {e}")
    
    async def sync_clubs(self):
        """Sync clubs data to Google Sheets."""
        try:
            result = await self.db.execute(
                select(Club).order_by(Club.id)
            )
            clubs = result.scalars().all()
            
            headers = [
                "ID",
                "Назва",
                "Тривалість (хв)",
                "Локація",
            ]
            
            rows = []
            for club in clubs:
                rows.append([
                    club.id,
                    club.name,
                    club.duration_min,
                    club.location,
                ])
            
            self._update_sheet("Clubs", headers, rows)
            logger.info(f"Synced {len(clubs)} clubs to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing clubs: {e}")
    
    async def sync_schedules(self):
        """Sync schedules data to Google Sheets."""
        try:
            result = await self.db.execute(
                select(Schedule)
                .options(
                    selectinload(Schedule.club),
                    selectinload(Schedule.teacher),
                )
                .order_by(Schedule.id)
            )
            schedules = result.scalars().all()
            
            headers = [
                "ID",
                "Гурток",
                "День тижня",
                "Час початку",
                "Вчитель",
                "Активний",
            ]
            
            weekday_names = {
                1: "Понеділок",
                2: "Вівторок", 
                3: "Середа",
                4: "Четвер",
                5: "П'ятниця",
            }
            
            rows = []
            for schedule in schedules:
                rows.append([
                    schedule.id,
                    schedule.club.name if schedule.club else "",
                    weekday_names.get(schedule.weekday, str(schedule.weekday)),
                    schedule.start_time.strftime("%H:%M"),
                    schedule.teacher.full_name if schedule.teacher else "",
                    "Так" if schedule.active else "Ні",
                ])
            
            self._update_sheet("Schedules", headers, rows)
            logger.info(f"Synced {len(schedules)} schedules to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing schedules: {e}")
    
    async def sync_attendance(self):
        """Sync attendance data to Google Sheets."""
        try:
            result = await self.db.execute(
                select(Attendance)
                .options(
                    selectinload(Attendance.lesson_event).selectinload(LessonEvent.club),
                    selectinload(Attendance.lesson_event).selectinload(LessonEvent.teacher),
                    selectinload(Attendance.student),
                )
                .order_by(Attendance.lesson_event_id, Attendance.student_id)
            )
            attendance_records = result.scalars().all()
            
            headers = [
                "Дата",
                "День тижня",
                "Гурток",
                "Вчитель",
                "Учень",
                "Статус",
                "Відмічено",
            ]
            
            weekday_names = {
                0: "Понеділок",
                1: "Вівторок",
                2: "Середа", 
                3: "Четвер",
                4: "П'ятниця",
                5: "Субота",
                6: "Неділя",
            }
            
            rows = []
            for attendance in attendance_records:
                lesson_date = attendance.lesson_event.date
                weekday = weekday_names.get(lesson_date.weekday(), "")
                
                rows.append([
                    lesson_date.isoformat(),
                    weekday,
                    attendance.lesson_event.club.name if attendance.lesson_event.club else "",
                    attendance.lesson_event.teacher.full_name if attendance.lesson_event.teacher else "",
                    attendance.student.full_name if attendance.student else "",
                    "Присутній" if attendance.status.value == "present" else "Відсутній",
                    attendance.marked_at.isoformat() if attendance.marked_at else "",
                ])
            
            self._update_sheet("Attendance", headers, rows)
            logger.info(f"Synced {len(attendance_records)} attendance records to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing attendance: {e}")
    
    async def sync_payroll(self):
        """Sync payroll data to Google Sheets."""
        try:
            result = await self.db.execute(
                select(Payroll)
                .options(
                    selectinload(Payroll.teacher),
                    selectinload(Payroll.lesson_event).selectinload(LessonEvent.club),
                )
                .order_by(Payroll.created_at.desc())
            )
            payroll_records = result.scalars().all()
            
            headers = [
                "Місяць",
                "Вчитель",
                "Дата заняття",
                "Гурток",
                "Основа",
                "Сума",
                "Примітка",
                "Створено",
            ]
            
            rows = []
            for payroll in payroll_records:
                lesson_date = payroll.lesson_event.date if payroll.lesson_event else None
                month = lesson_date.strftime("%Y-%m") if lesson_date else ""
                
                rows.append([
                    month,
                    payroll.teacher.full_name if payroll.teacher else "",
                    lesson_date.isoformat() if lesson_date else "",
                    payroll.lesson_event.club.name if payroll.lesson_event and payroll.lesson_event.club else "",
                    "Автоматично" if payroll.basis.value == "auto" else "Вручну",
                    float(payroll.amount_decimal),
                    payroll.note or "",
                    payroll.created_at.isoformat(),
                ])
            
            self._update_sheet("Payroll", headers, rows)
            logger.info(f"Synced {len(payroll_records)} payroll records to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing payroll: {e}")
    
    def _update_sheet(self, sheet_name: str, headers: List[str], rows: List[List]):
        """Update or create sheet with data."""
        try:
            # Try to get existing sheet
            try:
                sheet = self.spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                # Create new sheet
                sheet = self.spreadsheet.add_worksheet(
                    title=sheet_name, rows=1000, cols=len(headers)
                )
            
            # Clear existing data
            sheet.clear()
            
            # Update with new data
            all_data = [headers] + rows
            if all_data:
                sheet.update(
                    range_name=f"A1:{chr(64 + len(headers))}{len(all_data)}",
                    values=all_data,
                )
            
            logger.info(f"Updated sheet '{sheet_name}' with {len(rows)} rows")
            
        except Exception as e:
            logger.error(f"Error updating sheet '{sheet_name}': {e}")
            raise
