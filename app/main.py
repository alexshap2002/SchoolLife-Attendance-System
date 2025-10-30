"""Main FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, health, public, students, teachers, clubs, schedules, bot, webapp, pay_rates, payroll, conducted_lessons, automations, audit
from app.bot import create_bot
from app.core.database import init_db
from app.core.settings import settings
# Scheduler disabled - using worker architecture
from app.web.admin import router as admin_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting School of Life application...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Scheduler disabled - using worker architecture
    logger.info("Web server mode - scheduler runs in separate worker process")
    
    # Start Telegram bot - DISABLED: polling runs in dispatcher worker
    # bot = create_bot()
    # bot_task = asyncio.create_task(bot.dp.start_polling(bot))
    # logger.info("Telegram bot started")
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")
    # bot_task.cancel()  # DISABLED: no bot task in webapp
    logger.info("Application stopped")


# Create FastAPI app
app = FastAPI(
    title="School of Life Attendance System",
    description="Система обліку відвідуваності дитячої програми 'Школа життя'",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Include API routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(public.router)  # Публічні API для веб-адмінки (з префіксом /api)
app.include_router(students.router, prefix="/api")  # Додаємо префікс для сумісності
app.include_router(teachers.router, prefix="/api")
app.include_router(clubs.router, prefix="/api")
app.include_router(schedules.router, prefix="/api")
app.include_router(bot.router, prefix="/api")
app.include_router(pay_rates.router)  # Pay rates API (має власний префікс)
app.include_router(payroll.router)    # Payroll API (має власний префікс)
app.include_router(conducted_lessons.router)  # Conducted lessons API (має власний префікс)
app.include_router(automations.router)  # Automations API (має власний префікс)
app.include_router(audit.router)  # Audit log API (має власний префікс)
app.include_router(webapp.router, prefix="/api/webapp")  # WebApp API

# Include web admin router
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.env == "dev",
        proxy_headers=True,  # Для роботи за reverse proxy
        forwarded_allow_ips="*",  # Дозволити всі IP для proxy
    )
