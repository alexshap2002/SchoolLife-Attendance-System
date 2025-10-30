# 🎓 SchoolLife Attendance System

> Full-featured attendance tracking system for children's educational programs with Telegram bot, web admin panel, and Google Sheets integration

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [About](#-about)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Screenshots](#-screenshots)
- [Contact](#-contact)

---

## 🎯 About

**SchoolLife Attendance System** is a comprehensive web-based management system for children's educational programs, designed to automate:

- 📊 Student attendance tracking
- 👥 Student and teacher database management
- 📅 Class scheduling
- 💰 Teacher payroll calculations
- 📱 Telegram bot for quick check-ins
- 📈 Analytics and reporting
- 🔍 Complete audit trail of all actions

The system was created for **"School of Life"** — a children's educational program in Brovary, Ukraine.

---

## ✨ Key Features

### 🎨 Web Interface (Admin Panel)

- **📊 Dashboard** — real-time statistics
- **👥 Student Database** — complete information about children and parents
- **👨‍🏫 Teacher Database** — contacts, salary, statistics
- **🎭 Clubs** — activity management
- **📅 Schedule** — flexible class planning
- **✅ Attendance** — quick presence tracking
- **💵 Payroll** — automatic salary calculations
- **📈 Analytics** — KPIs, charts, trends
- **🔍 Change History** — complete audit log

### 📱 Telegram Bot

- **⚡ Quick Check-ins** — mark attendance in 10 seconds
- **🔔 Automatic Reminders** — 10 minutes before class
- **📊 Statistics** — instant reports
- **🤖 Bot Schedule** — automated schedule-based reminders

### 🔧 Technical Features

- **🐳 Docker** — full containerization
- **🔄 Automation** — scheduler for recurring tasks
- **📊 Google Sheets** — data export
- **🔐 JWT Authorization** — secure access
- **📝 Audit Log** — logging of all actions
- **⚡ AsyncIO** — asynchronous processing

---

## 🛠 Tech Stack

### Backend

- **[FastAPI](https://fastapi.tiangolo.com/)** — modern web framework
- **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** — ORM with async support
- **[Alembic](https://alembic.sqlalchemy.org/)** — database migrations
- **[Pydantic](https://pydantic.dev/)** — data validation
- **[aiogram 3.0](https://docs.aiogram.dev/)** — Telegram Bot framework
- **[APScheduler](https://apscheduler.readthedocs.io/)** — task scheduler
- **[gspread](https://gspread.readthedocs.io/)** — Google Sheets API

### Frontend

- **[React](https://react.dev/)** + **[TypeScript](https://www.typescriptlang.org/)** — Telegram WebApp
- **[Vite](https://vitejs.dev/)** — fast build tool
- **[Tailwind CSS](https://tailwindcss.com/)** — utility-first CSS
- **[Bootstrap 5](https://getbootstrap.com/)** — admin panel

### Infrastructure

- **[PostgreSQL 16](https://www.postgresql.org/)** — database
- **[Docker](https://www.docker.com/)** + **Docker Compose** — containerization
- **[Nginx](https://nginx.org/)** — web server for WebApp
- **[Uvicorn](https://www.uvicorn.org/)** — ASGI server

---

## 🚀 Installation

### Requirements

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Python** 3.11+ (for local development)
- **Node.js** 18+ (for WebApp development)

### Quick Start

1. **Clone the repository:**

```bash
git clone https://github.com/alexshap2002/SchoolLife-Attendance-System.git
cd SchoolLife-Attendance-System
```

2. **Create `.env` file:**

```bash
cp env.example .env
# Edit .env — add your tokens and passwords
```

3. **Run with Docker:**

```bash
docker-compose -f docker-compose.local.yml up -d
```

4. **Open admin panel:**

```
http://localhost:8000/admin/
```

**Login:** `admin@schoola.local`  
**Password:** `admin123` (change after first login!)

---

### Detailed Instructions

See [LOCAL_SETUP_README.md](LOCAL_SETUP_README.md) for complete setup guide.

---

## 📁 Project Structure

```
SchoolLife-Attendance-System/
├── app/                          # Main application code
│   ├── api/                      # API endpoints
│   │   ├── public.py            # Public API (students, teachers, clubs)
│   │   ├── attendance.py        # Attendance API
│   │   ├── payroll.py           # Payroll API
│   │   ├── audit.py             # Audit log API
│   │   └── ...
│   ├── bot/                      # Telegram Bot
│   │   ├── handlers.py          # Command handlers
│   │   ├── quick_attendance.py  # Quick check-ins
│   │   └── unified_attendance.py # Unified check-ins
│   ├── core/                     # System core
│   │   ├── database.py          # Database connection
│   │   ├── settings.py          # Configuration
│   │   └── security.py          # Authorization
│   ├── models/                   # SQLAlchemy models
│   ├── services/                 # Business logic
│   │   ├── attendance_service.py
│   │   ├── payroll_service.py
│   │   ├── audit_service.py
│   │   └── ...
│   ├── web/                      # Web interface
│   │   ├── templates/           # HTML templates
│   │   └── static/              # CSS, JS
│   └── workers/                  # Background workers
│       ├── dispatcher.py        # Telegram dispatcher
│       └── automation_scheduler.py
├── webapp/                       # React WebApp (Telegram)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
│   └── ...
├── alembic/                      # Database migrations
├── scripts/                      # Utility scripts
├── docs/                         # Documentation
├── docker-compose.local.yml      # Docker for local development
├── docker-compose.server.yml     # Docker for production
└── requirements.txt              # Python dependencies
```

---

## 📖 API Documentation

After running the application, API documentation is available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Main Endpoints

```
GET    /health                    # Health check
POST   /auth/login                # Authentication
GET    /api/students              # List students
POST   /api/students              # Create student
GET    /api/teachers              # List teachers
GET    /api/clubs                 # List clubs
GET    /api/schedules             # Schedule
GET    /api/attendance            # Attendance
POST   /api/payroll/calculate     # Calculate payroll
GET    /api/audit                 # Audit log
```

---

## 📊 Screenshots

### Admin Panel
*(Add screenshots after deployment)*

- Dashboard with KPIs
- Student table
- Attendance calendar
- Teacher statistics

### Telegram Bot
*(Add bot screenshots)*

- Quick check-ins
- Automatic reminders
- Real-time statistics

---

## 🔒 Security

**⚠️ IMPORTANT:** Before deployment, read [SECURITY.md](SECURITY.md)

- Never commit `.env` files
- Use strong passwords
- Regularly update tokens
- Enable HTTPS on production

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 📝 License

[MIT License](LICENSE) — free to use with attribution.

---

## 👨‍💻 Author

**Oleksandr Shapovalov**

- 📧 Email: aleks.shap2002@gmail.com
- 💼 GitHub: [@alexshap2002](https://github.com/alexshap2002)
- 🔗 LinkedIn: [in/alexandr-shapovalov](https://linkedin.com/in/alexandr-shapovalov)

---

## 🌟 Acknowledgments

- **"School of Life"** for the opportunity to create this project
- **FastAPI** and **aiogram** communities for excellent frameworks
- Everyone who uses and improves this system

---

<div align="center">
  
**Made with ❤️ in Ukraine 🇺🇦**

_If this project was helpful — give it a ⭐ on GitHub!_

</div>
