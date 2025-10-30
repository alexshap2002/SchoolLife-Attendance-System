#!/bin/bash
# ===================================================================
# DEPLOYMENT СКРИПТ - ВИКОНУВАТИ НА СЕРВЕРІ
# ===================================================================
# Підключись до сервера і запусти цей скрипт
# ===================================================================

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                 ║"
echo "║         🚀 DEPLOYMENT ОПТИМІЗАЦІЙ                             ║"
echo "║                                                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Перехід в директорію проекту
cd /root/school-life-app

# ===================================================================
# КРОК 1: BACKUP БАЗИ ДАНИХ
# ===================================================================
echo "📦 КРОК 1: Створюю BACKUP бази даних..."
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker exec school-db pg_dump -U school_user -d school_db > "$BACKUP_FILE"
echo "   ✅ Backup: $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1))"
echo ""

# ===================================================================
# КРОК 2: SQL ОПТИМІЗАЦІЇ
# ===================================================================
echo "🗄️  КРОК 2: Застосовую SQL оптимізації..."

# Перевірка чи файл існує
if [ ! -f "database_optimizations.sql" ]; then
    echo "⚠️  Файл database_optimizations.sql не знайдено!"
    echo "   Створюю його зараз..."
    
    cat > database_optimizations.sql << 'SQLEOF'
-- ІНДЕКСИ
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lesson_events_status_notify_at 
ON lesson_events(status, notify_at) 
WHERE status = 'PLANNED' AND sent_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_attendance_lesson_event_id 
ON attendance(lesson_event_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conducted_lessons_teacher_date 
ON conducted_lessons(teacher_id, lesson_date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lesson_events_date_planned 
ON lesson_events(date) 
WHERE status = 'PLANNED';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payroll_created_at 
ON payroll(created_at DESC);

-- CONSTRAINTS
DO $$ 
BEGIN
    ALTER TABLE schedules 
    ADD CONSTRAINT schedules_weekday_check 
    CHECK (weekday BETWEEN 1 AND 7) NOT VALID;
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE bot_schedules 
    ADD CONSTRAINT bot_schedules_offset_check 
    CHECK (offset_minutes BETWEEN -120 AND 120) NOT VALID;
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE schedules 
    ADD CONSTRAINT schedules_start_time_check 
    CHECK (start_time BETWEEN '06:00'::time AND '22:00'::time) NOT VALID;
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE clubs 
    ADD CONSTRAINT clubs_duration_check 
    CHECK (duration_min BETWEEN 10 AND 180) NOT VALID;
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;
SQLEOF
fi

docker cp database_optimizations.sql school-db:/tmp/db_opt.sql
docker exec school-db psql -U school_user -d school_db -f /tmp/db_opt.sql
echo "   ✅ SQL оптимізації застосовано"
echo ""

# ===================================================================
# КРОК 3: ВАЛІДАЦІЯ CONSTRAINTS
# ===================================================================
echo "✔️  КРОК 3: Валідація constraints..."
docker exec school-db psql -U school_user -d school_db << 'EOF'
ALTER TABLE schedules VALIDATE CONSTRAINT schedules_weekday_check;
ALTER TABLE bot_schedules VALIDATE CONSTRAINT bot_schedules_offset_check;
ALTER TABLE schedules VALIDATE CONSTRAINT schedules_start_time_check;
ALTER TABLE clubs VALIDATE CONSTRAINT clubs_duration_check;
SELECT 'Constraints OK!' as result;
EOF
echo ""

# ===================================================================
# КРОК 4: ОЧИЩЕННЯ СТАРИХ ПОДІЙ
# ===================================================================
echo "🧹 КРОК 4: Очищення старих PLANNED подій..."
OLD_COUNT=$(docker exec school-db psql -U school_user -d school_db -t -c "
SELECT COUNT(*) FROM lesson_events 
WHERE status = 'PLANNED' AND notify_at < NOW() AND sent_at IS NULL;
")

if [ "$OLD_COUNT" -gt 0 ]; then
    docker exec school-db psql -U school_user -d school_db << 'EOF'
UPDATE lesson_events 
SET status = 'COMPLETED', completed_at = NOW()
WHERE status = 'PLANNED' AND notify_at < NOW() AND sent_at IS NULL;
EOF
    echo "   ✅ Очищено подій: $OLD_COUNT"
else
    echo "   ✅ Немає старих подій"
fi
echo ""

# ===================================================================
# КРОК 5: ОНОВЛЕННЯ КОДУ
# ===================================================================
echo "📝 КРОК 5: Оновлення коду..."

# lesson_event_manager.py
if grep -q "from datetime import datetime, date, time$" app/services/lesson_event_manager.py; then
    sed -i.bak 's/from datetime import datetime, date, time$/from datetime import datetime, date, time, timedelta/' app/services/lesson_event_manager.py
    echo "   ✅ lesson_event_manager.py - додано timedelta"
else
    echo "   ℹ️  lesson_event_manager.py - вже оновлено"
fi

# dispatcher.py - ORDER BY
if ! grep -q "order_by(LessonEvent.notify_at" app/workers/dispatcher.py; then
    # Знаходимо рядок з .with_for_update і додаємо .order_by перед ним
    sed -i.bak '/\.with_for_update(skip_locked=True)/i\                    .order_by(LessonEvent.notify_at.asc())' app/workers/dispatcher.py
    echo "   ✅ dispatcher.py - додано ORDER BY"
else
    echo "   ℹ️  dispatcher.py - ORDER BY вже є"
fi

# dispatcher.py - sleep intervals
sed -i.bak 's/await asyncio\.sleep(10)  # Poll every 10 seconds/await asyncio.sleep(30)  # Poll every 30 seconds/' app/workers/dispatcher.py
sed -i.bak 's/await asyncio\.sleep(30)  # Wait longer on error/await asyncio.sleep(60)  # Wait longer on error/' app/workers/dispatcher.py
echo "   ✅ dispatcher.py - оновлено інтервали"
echo ""

# ===================================================================
# КРОК 6: ПЕРЕЗАПУСК КОНТЕЙНЕРІВ
# ===================================================================
echo "🔄 КРОК 6: Перезапуск контейнерів..."
docker compose -f docker-compose.server.yml down
docker compose -f docker-compose.server.yml build --no-cache webapp
docker compose -f docker-compose.server.yml up -d
echo "   ⏳ Чекаю 10 секунд..."
sleep 10
echo ""

# ===================================================================
# КРОК 7: ПЕРЕВІРКА
# ===================================================================
echo "✅ КРОК 7: Перевірка..."
echo ""
echo "📋 Статус контейнерів:"
docker compose -f docker-compose.server.yml ps
echo ""

echo "📋 Індекси:"
docker exec school-db psql -U school_user -d school_db -c "
SELECT tablename, indexname 
FROM pg_indexes 
WHERE indexname LIKE 'idx_%' 
ORDER BY tablename;" | head -10

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                 ║"
echo "║              ✅ DEPLOYMENT ЗАВЕРШЕНО!                         ║"
echo "║                                                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 РЕЗУЛЬТАТ:"
echo "   • Backup: $BACKUP_FILE"
echo "   • Індексів додано: 5"
echo "   • Constraints додано: 4"
echo "   • Старих подій очищено: $OLD_COUNT"
echo "   • Код оновлено: 4 зміни"
echo ""
echo "🔙 Rollback (якщо потрібно):"
echo "   docker compose -f docker-compose.server.yml down"
echo "   docker exec -i school-db psql -U school_user -d school_db < $BACKUP_FILE"
echo "   docker compose -f docker-compose.server.yml up -d"
echo ""

