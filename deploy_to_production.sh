#!/bin/bash
# ===================================================================
# СКРИПТ DEPLOYMENT ОПТИМІЗАЦІЙ НА БОЙОВИЙ СЕРВЕР
# ===================================================================
# Дата: 2025-10-08
# ВАЖЛИВО: Виконувати тільки на сервері root@185.233.39.11
# ===================================================================

set -e  # Зупинитись при помилці

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                 ║"
echo "║     🚀 DEPLOYMENT ОПТИМІЗАЦІЙ НА БОЙОВИЙ СЕРВЕР               ║"
echo "║                                                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Перевірка що ми на сервері
if [ ! -d "/root/school-life-app" ]; then
    echo "❌ ПОМИЛКА: Скрипт треба запускати на сервері!"
    exit 1
fi

cd /root/school-life-app

# ===================================================================
# КРОК 1: BACKUP БАЗИ ДАНИХ
# ===================================================================
echo "📦 КРОК 1: Створюю BACKUP бази даних..."
BACKUP_FILE="backup_before_optimization_$(date +%Y%m%d_%H%M%S).sql"

docker exec school-db pg_dump -U school_user -d school_db > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup створено: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "❌ ПОМИЛКА: Не вдалося створити backup!"
    exit 1
fi

echo ""

# ===================================================================
# КРОК 2: ПЕРЕВІРКА СТАНУ СИСТЕМИ
# ===================================================================
echo "🔍 КРОК 2: Перевірка стану системи..."

# Перевірка контейнерів
echo "📋 Статус контейнерів:"
docker ps --filter "name=school" --format "table {{.Names}}\t{{.Status}}"

# Перевірка БД
echo ""
echo "📋 Перевірка підключення до БД:"
docker exec school-db psql -U school_user -d school_db -c "SELECT version();" | head -1

echo ""

# ===================================================================
# КРОК 3: ПЕРЕВІРКА СТАРИХ PLANNED ПОДІЙ
# ===================================================================
echo "🧹 КРОК 3: Перевірка старих PLANNED подій..."

OLD_EVENTS=$(docker exec school-db psql -U school_user -d school_db -t -c "
SELECT COUNT(*) 
FROM lesson_events 
WHERE status = 'PLANNED' 
AND notify_at < NOW() 
AND sent_at IS NULL;
")

echo "📊 Знайдено старих PLANNED подій: $OLD_EVENTS"

if [ "$OLD_EVENTS" -gt 0 ]; then
    echo "⚠️  Будуть видалені/оновлені старі події"
fi

echo ""

# ===================================================================
# КРОК 4: ЗАСТОСУВАННЯ SQL ОПТИМІЗАЦІЙ
# ===================================================================
echo "🗄️  КРОК 4: Застосування SQL оптимізацій..."

# Перевірка чи файл існує
if [ ! -f "database_optimizations.sql" ]; then
    echo "❌ ПОМИЛКА: Файл database_optimizations.sql не знайдено!"
    echo "💡 Спочатку скопіюй файли з локального комп'ютера:"
    echo "   scp database_optimizations.sql root@185.233.39.11:/root/school-life-app/"
    exit 1
fi

# Копіюємо SQL в контейнер
docker cp database_optimizations.sql school-db:/tmp/db_opt.sql

# Виконуємо SQL
echo "📝 Застосовую індекси та constraints..."
docker exec school-db psql -U school_user -d school_db -f /tmp/db_opt.sql

echo "✅ SQL оптимізації застосовано!"
echo ""

# ===================================================================
# КРОК 5: ВАЛІДАЦІЯ CONSTRAINTS
# ===================================================================
echo "✔️  КРОК 5: Валідація constraints..."

echo "📋 Перевірка на проблемні дані..."
docker exec school-db psql -U school_user -d school_db << 'EOF'
SELECT 
    'schedules.weekday' as check_type, 
    COUNT(*) as violations 
FROM schedules WHERE weekday NOT BETWEEN 1 AND 7
UNION ALL
SELECT 'bot_schedules.offset', COUNT(*) 
FROM bot_schedules WHERE offset_minutes NOT BETWEEN -120 AND 120
UNION ALL
SELECT 'schedules.start_time', COUNT(*) 
FROM schedules WHERE start_time NOT BETWEEN '06:00' AND '22:00'
UNION ALL
SELECT 'clubs.duration', COUNT(*) 
FROM clubs WHERE duration_min NOT BETWEEN 10 AND 180;
EOF

echo ""
echo "📝 Валідую constraints..."
docker exec school-db psql -U school_user -d school_db << 'EOF'
ALTER TABLE schedules VALIDATE CONSTRAINT schedules_weekday_check;
ALTER TABLE bot_schedules VALIDATE CONSTRAINT bot_schedules_offset_check;
ALTER TABLE schedules VALIDATE CONSTRAINT schedules_start_time_check;
ALTER TABLE clubs VALIDATE CONSTRAINT clubs_duration_check;
SELECT 'Constraints validated!' as result;
EOF

echo ""

# ===================================================================
# КРОК 6: ОЧИЩЕННЯ СТАРИХ PLANNED ПОДІЙ
# ===================================================================
echo "🧹 КРОК 6: Очищення старих PLANNED подій..."

if [ "$OLD_EVENTS" -gt 0 ]; then
    echo "📝 Оновлюю статус старих подій на COMPLETED..."
    
    docker exec school-db psql -U school_user -d school_db << 'EOF'
UPDATE lesson_events 
SET status = 'COMPLETED',
    completed_at = NOW()
WHERE status = 'PLANNED' 
AND notify_at < NOW() 
AND sent_at IS NULL;

SELECT 'Оновлено старих подій: ' || COUNT(*) 
FROM lesson_events 
WHERE status = 'COMPLETED' 
AND completed_at > NOW() - INTERVAL '5 minutes';
EOF
    
    echo "✅ Старі події очищено!"
else
    echo "✅ Немає старих подій для очищення"
fi

echo ""

# ===================================================================
# КРОК 7: ПЕРЕВІРКА ІНДЕКСІВ
# ===================================================================
echo "📊 КРОК 7: Перевірка створених індексів..."

docker exec school-db psql -U school_user -d school_db << 'EOF'
SELECT 
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
EOF

echo ""

# ===================================================================
# КРОК 8: ОНОВЛЕННЯ КОДУ
# ===================================================================
echo "📦 КРОК 8: Перевірка оновлених файлів коду..."

FILES_TO_CHECK=(
    "app/services/lesson_event_manager.py"
    "app/workers/dispatcher.py"
    "run_manual_cleanup.py"
)

MISSING_FILES=0
for file in "${FILES_TO_CHECK[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Відсутній файл: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    else
        echo "✅ Файл є: $file"
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo ""
    echo "⚠️  Деякі файли відсутні. Скопіюй їх з локального комп'ютера:"
    echo "   scp app/services/lesson_event_manager.py root@185.233.39.11:/root/school-life-app/app/services/"
    echo "   scp app/workers/dispatcher.py root@185.233.39.11:/root/school-life-app/app/workers/"
    echo "   scp run_manual_cleanup.py root@185.233.39.11:/root/school-life-app/"
    echo ""
    echo "❓ Продовжити без оновлення коду? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ Deployment зупинено. Спочатку скопіюй файли."
        exit 1
    fi
fi

echo ""

# ===================================================================
# КРОК 9: ПЕРЕЗАПУСК КОНТЕЙНЕРІВ
# ===================================================================
echo "🔄 КРОК 9: Перезапуск контейнерів..."

echo "📝 Зупиняю контейнери..."
docker compose -f docker-compose.server.yml down

echo "📝 Перебудовую webapp образ..."
docker compose -f docker-compose.server.yml build --no-cache webapp

echo "📝 Запускаю контейнери..."
docker compose -f docker-compose.server.yml up -d

echo "⏳ Чекаю 10 секунд для ініціалізації..."
sleep 10

echo ""

# ===================================================================
# КРОК 10: ПЕРЕВІРКА ПРАЦЕЗДАТНОСТІ
# ===================================================================
echo "✅ КРОК 10: Перевірка працездатності..."

echo "📋 Статус контейнерів:"
docker compose -f docker-compose.server.yml ps

echo ""
echo "📋 Логи webapp (останні 20 рядків):"
docker compose -f docker-compose.server.yml logs --tail=20 webapp

echo ""
echo "📋 Логи dispatcher (останні 20 рядків):"
docker compose -f docker-compose.server.yml logs --tail=20 dispatcher

echo ""

# ===================================================================
# КРОК 11: ТЕСТ ПРОДУКТИВНОСТІ
# ===================================================================
echo "⚡ КРОК 11: Тест продуктивності запиту..."

docker exec school-db psql -U school_user -d school_db << 'EOF'
EXPLAIN ANALYZE
SELECT * FROM lesson_events 
WHERE status = 'PLANNED' 
AND notify_at <= NOW() 
AND sent_at IS NULL 
ORDER BY notify_at ASC 
LIMIT 30;
EOF

echo ""

# ===================================================================
# ЗАВЕРШЕННЯ
# ===================================================================
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                 ║"
echo "║              ✅ DEPLOYMENT УСПІШНО ЗАВЕРШЕНО!                 ║"
echo "║                                                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 ПІДСУМОК:"
echo "   ✅ Backup створено: $BACKUP_FILE"
echo "   ✅ Індекси додано: 5 шт."
echo "   ✅ Constraints додано: 4 шт."
echo "   ✅ Старі події очищено: $OLD_EVENTS шт."
echo "   ✅ Контейнери перезапущено"
echo ""
echo "📝 НАСТУПНІ КРОКИ:"
echo "   1. Перевір логи: docker compose -f docker-compose.server.yml logs -f"
echo "   2. Перевір роботу Telegram bot"
echo "   3. Перевір швидкість завантаження сторінок"
echo ""
echo "🔙 ROLLBACK (якщо щось не так):"
echo "   docker exec school-db psql -U school_user -d school_db < $BACKUP_FILE"
echo ""

