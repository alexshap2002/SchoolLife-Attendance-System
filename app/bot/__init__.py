"""Telegram bot package."""

import logging
from typing import Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import router as main_router
from app.core.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """Create and configure Telegram bot."""
    # Create bot instance
    bot = Bot(
        token=settings.telegram_bot_token,
        parse_mode=ParseMode.HTML
    )
    
    # Create dispatcher with memory storage
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include routers
    dp.include_router(main_router)
    
    # Include quick attendance router
    from app.bot.quick_attendance import router as quick_attendance_router
    dp.include_router(quick_attendance_router)
    
    # Include unified attendance router
    from app.bot.unified_attendance import router as unified_attendance_router
    dp.include_router(unified_attendance_router)
    
    # Attach dispatcher to bot for easy access
    bot.dp = dp
    
    return bot


async def start_bot():
    """Start bot polling."""
    bot = create_bot()
    logger.info("Starting bot polling...")
    await bot.dp.start_polling(bot)


async def stop_bot():
    """Stop bot polling."""
    logger.info("Stopping bot...")
