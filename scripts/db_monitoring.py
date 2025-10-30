#!/usr/bin/env python3
"""
===============================================================
📊 МОНІТОРИНГ БАЗИ ДАНИХ ТА ПРОДУКТИВНОСТІ
===============================================================
📅 Дата створення: 2025-09-15
🎯 Мета: Моніторинг продуктивності PostgreSQL та логування метрик
===============================================================
"""

import asyncio
import asyncpg
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import argparse

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/db_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """Клас для моніторингу бази даних."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.metrics = {}
    
    async def connect(self):
        """Підключення до БД."""
        try:
            self.conn = await asyncpg.connect(self.connection_string)
            logger.info("✅ Підключено до БД для моніторингу")
        except Exception as e:
            logger.error(f"❌ Помилка підключення до БД: {e}")
            raise
    
    async def disconnect(self):
        """Відключення від БД."""
        if hasattr(self, 'conn') and self.conn:
            await self.conn.close()
            logger.info("🔌 Відключено від БД")
    
    async def get_database_size(self) -> Dict[str, Any]:
        """Отримання розміру БД та таблиць."""
        try:
            # Загальний розмір БД
            db_size_query = """
                SELECT pg_size_pretty(pg_database_size(current_database())) as database_size,
                       pg_database_size(current_database()) as database_size_bytes
            """
            db_size = await self.conn.fetchrow(db_size_query)
            
            # Розміри таблиць
            tables_size_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 20
            """
            tables = await self.conn.fetch(tables_size_query)
            
            return {
                "database_size": db_size['database_size'],
                "database_size_bytes": db_size['database_size_bytes'],
                "tables": [dict(table) for table in tables]
            }
        except Exception as e:
            logger.error(f"❌ Помилка отримання розміру БД: {e}")
            return {}
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Статистика підключень."""
        try:
            query = """
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
                    max(now() - query_start) as longest_query_duration,
                    max(now() - state_change) as longest_idle_duration
                FROM pg_stat_activity 
                WHERE pid != pg_backend_pid()
            """
            result = await self.conn.fetchrow(query)
            return dict(result)
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики підключень: {e}")
            return {}
    
    async def get_table_stats(self) -> Dict[str, Any]:
        """Статистика таблиць."""
        try:
            query = """
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables 
                ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
                LIMIT 20
            """
            result = await self.conn.fetch(query)
            return {"tables": [dict(row) for row in result]}
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики таблиць: {e}")
            return {}
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Статистика індексів."""
        try:
            query = """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                    idx_scan as scans
                FROM pg_stat_user_indexes 
                ORDER BY idx_scan DESC
                LIMIT 20
            """
            result = await self.conn.fetch(query)
            return {"indexes": [dict(row) for row in result]}
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики індексів: {e}")
            return {}
    
    async def get_slow_queries(self) -> Dict[str, Any]:
        """Повільні запити."""
        try:
            query = """
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    min_time,
                    max_time,
                    stddev_time,
                    rows
                FROM pg_stat_statements 
                WHERE query NOT LIKE '%pg_stat_statements%'
                ORDER BY mean_time DESC
                LIMIT 10
            """
            result = await self.conn.fetch(query)
            return {"slow_queries": [dict(row) for row in result]}
        except Exception as e:
            # pg_stat_statements може бути не встановлено
            logger.warning("⚠️ pg_stat_statements недоступно")
            return {"slow_queries": []}
    
    async def get_locks(self) -> Dict[str, Any]:
        """Поточні блокування."""
        try:
            query = """
                SELECT 
                    pg_stat_activity.pid,
                    pg_stat_activity.usename,
                    pg_stat_activity.query,
                    pg_locks.mode,
                    pg_locks.locktype,
                    pg_locks.granted
                FROM pg_locks 
                JOIN pg_stat_activity ON pg_locks.pid = pg_stat_activity.pid
                WHERE NOT pg_locks.granted
                ORDER BY pg_stat_activity.query_start
            """
            result = await self.conn.fetch(query)
            return {"locks": [dict(row) for row in result]}
        except Exception as e:
            logger.error(f"❌ Помилка отримання блокувань: {e}")
            return {}
    
    async def get_school_specific_metrics(self) -> Dict[str, Any]:
        """Специфічні метрики для школи."""
        try:
            metrics = {}
            
            # Загальна кількість записів
            counts_query = """
                SELECT 
                    (SELECT COUNT(*) FROM students) as total_students,
                    (SELECT COUNT(*) FROM teachers WHERE active = true) as active_teachers,
                    (SELECT COUNT(*) FROM clubs) as total_clubs,
                    (SELECT COUNT(*) FROM conducted_lessons) as total_lessons,
                    (SELECT COUNT(*) FROM attendance WHERE status = 'PRESENT') as total_attendances,
                    (SELECT COUNT(*) FROM lesson_events WHERE status = 'PLANNED' AND date >= CURRENT_DATE) as upcoming_lessons
            """
            counts = await self.conn.fetchrow(counts_query)
            metrics.update(dict(counts))
            
            # Статистика за останній тиждень
            week_stats_query = """
                SELECT 
                    COUNT(DISTINCT lesson_date) as lessons_this_week,
                    COUNT(*) as total_conducted_lessons,
                    SUM(present_students) as total_present_students,
                    AVG(present_students) as avg_students_per_lesson
                FROM conducted_lessons 
                WHERE lesson_date >= CURRENT_DATE - INTERVAL '7 days'
            """
            week_stats = await self.conn.fetchrow(week_stats_query)
            metrics.update({f"week_{k}": v for k, v in dict(week_stats).items()})
            
            # Топ-5 найактивніших гуртків
            top_clubs_query = """
                SELECT 
                    c.name,
                    COUNT(cl.id) as lessons_count,
                    SUM(cl.present_students) as total_students
                FROM clubs c
                LEFT JOIN conducted_lessons cl ON c.id = cl.club_id 
                    AND cl.lesson_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY c.id, c.name
                ORDER BY lessons_count DESC
                LIMIT 5
            """
            top_clubs = await self.conn.fetch(top_clubs_query)
            metrics["top_clubs"] = [dict(row) for row in top_clubs]
            
            return metrics
        except Exception as e:
            logger.error(f"❌ Помилка отримання шкільних метрик: {e}")
            return {}
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Збір всіх метрик."""
        logger.info("📊 Початок збору метрик...")
        
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "database_size": await self.get_database_size(),
            "connections": await self.get_connection_stats(),
            "tables": await self.get_table_stats(),
            "indexes": await self.get_index_stats(),
            "slow_queries": await self.get_slow_queries(),
            "locks": await self.get_locks(),
            "school_metrics": await self.get_school_specific_metrics()
        }
        
        logger.info("✅ Метрики зібрано")
        return self.metrics
    
    async def save_metrics(self, filepath: str):
        """Збереження метрик у файл."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2, default=str, ensure_ascii=False)
            logger.info(f"💾 Метрики збережено: {filepath}")
        except Exception as e:
            logger.error(f"❌ Помилка збереження метрик: {e}")
    
    def print_summary(self):
        """Виведення короткого резюме метрик."""
        if not self.metrics:
            logger.warning("⚠️ Немає метрик для відображення")
            return
        
        print("\n" + "="*60)
        print("📊 РЕЗЮМЕ МОНІТОРИНГУ БАЗИ ДАНИХ")
        print("="*60)
        
        # Розмір БД
        db_size = self.metrics.get("database_size", {})
        if db_size:
            print(f"💾 Розмір БД: {db_size.get('database_size', 'N/A')}")
        
        # Підключення
        conn = self.metrics.get("connections", {})
        if conn:
            print(f"🔌 Підключення: {conn.get('total_connections', 'N/A')} "
                  f"(активних: {conn.get('active_connections', 'N/A')})")
        
        # Шкільні метрики
        school = self.metrics.get("school_metrics", {})
        if school:
            print(f"👥 Студентів: {school.get('total_students', 'N/A')}")
            print(f"👨‍🏫 Активних вчителів: {school.get('active_teachers', 'N/A')}")
            print(f"🎯 Гуртків: {school.get('total_clubs', 'N/A')}")
            print(f"📚 Проведених уроків: {school.get('total_lessons', 'N/A')}")
            print(f"📅 Запланованих уроків: {school.get('upcoming_lessons', 'N/A')}")
        
        # Блокування
        locks = self.metrics.get("locks", {}).get("locks", [])
        if locks:
            print(f"🔒 Активних блокувань: {len(locks)}")
        
        print("="*60)

async def main():
    """Головна функція."""
    parser = argparse.ArgumentParser(description='Моніторинг бази даних школи')
    parser.add_argument('--save', action='store_true', help='Зберегти метрики у файл')
    parser.add_argument('--output', default='/app/logs/metrics_{timestamp}.json', 
                       help='Шлях для збереження метрик')
    parser.add_argument('--db-url', default='postgresql://postgres:postgres@db:5432/school_db',
                       help='URL бази даних')
    
    args = parser.parse_args()
    
    # Створення директорії для логів
    os.makedirs('/app/logs', exist_ok=True)
    
    monitor = DatabaseMonitor(args.db_url)
    
    try:
        await monitor.connect()
        await monitor.collect_all_metrics()
        
        monitor.print_summary()
        
        if args.save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = args.output.format(timestamp=timestamp)
            await monitor.save_metrics(output_file)
        
    except Exception as e:
        logger.error(f"❌ Помилка моніторингу: {e}")
        return 1
    finally:
        await monitor.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
