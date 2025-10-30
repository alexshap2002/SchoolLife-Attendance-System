"""
Worker для запуску автоматизацій адміністратора.
"""

import asyncio
import logging
from datetime import datetime
import schedule
import time

from app.services.automation_service import run_automations

logger = logging.getLogger(__name__)


class AutomationWorker:
    """Worker для виконання автоматизацій."""
    
    def __init__(self):
        self.running = False
    
    def setup_scheduler(self):
        """Налаштовує scheduler для автоматизацій."""
        
        # Запускаємо автоматизації кожну хвилину
        # (вони самі визначать чи потрібно виконуватись зараз)
        schedule.every().minute.do(self.run_automation_job)
        
        logger.info("🤖 Automation scheduler configured")
    
    def run_automation_job(self):
        """Запускає автоматизації в async контексті."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_automations())
            loop.close()
        except Exception as e:
            logger.error(f"❌ Error in automation job: {e}")
    
    def start(self):
        """Запускає worker."""
        logger.info("🚀 Starting Automation Worker...")
        
        self.setup_scheduler()
        self.running = True
        
        logger.info("✅ Automation Worker started. Running automations every minute.")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt received")
                self.stop()
            except Exception as e:
                logger.error(f"❌ Error in automation worker loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def stop(self):
        """Зупиняє worker."""
        logger.info("🛑 Stopping Automation Worker...")
        self.running = False
        schedule.clear()
        logger.info("✅ Automation Worker stopped")


def main():
    """Головна функція для запуску worker."""
    
    # Налаштування логування
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/app/logs/automation_worker.log')
        ]
    )
    
    # Створюємо директорію для логів
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    logger.info("🤖 Starting Automation Worker...")
    
    worker = AutomationWorker()
    
    try:
        worker.start()
    except Exception as e:
        logger.error(f"❌ Fatal error in automation worker: {e}")
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
