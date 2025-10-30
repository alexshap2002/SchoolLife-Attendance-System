#!/bin/bash
# ===============================================================
# 🚀 НАЛАШТУВАННЯ ПРОДАКШН СЕРЕДОВИЩА
# ===============================================================
# 📅 Дата створення: 2025-09-15
# 🎯 Мета: Налаштування backup, monitoring та cron jobs
# ===============================================================

set -euo pipefail

echo "🚀 НАЛАШТУВАННЯ ПРОДАКШН СЕРЕДОВИЩА"
echo "="*50

# Створення необхідних директорій
echo "📁 Створення директорій..."
mkdir -p /app/backups
mkdir -p /app/logs
mkdir -p /app/scripts

# Копіювання скриптів (якщо запускається з контейнера)
if [ -f "/app/scripts/db_backup.sh" ]; then
    chmod +x /app/scripts/db_backup.sh
    echo "✅ Backup скрипт налаштовано"
fi

if [ -f "/app/scripts/db_monitoring.py" ]; then
    chmod +x /app/scripts/db_monitoring.py
    echo "✅ Monitoring скрипт налаштовано"
fi

# Встановлення cron jobs
echo "⏰ Налаштування cron jobs..."

# Backup кожного дня о 2:00
BACKUP_CRON="0 2 * * * /app/scripts/db_backup.sh >> /app/logs/backup_cron.log 2>&1"

# Моніторинг кожні 15 хвилин
MONITOR_CRON="*/15 * * * * /usr/bin/python3 /app/scripts/db_monitoring.py --save >> /app/logs/monitor_cron.log 2>&1"

# Щоденний summary о 9:00
SUMMARY_CRON="0 9 * * * /usr/bin/python3 /app/scripts/db_monitoring.py >> /app/logs/daily_summary.log 2>&1"

# Додавання cron jobs
{
    echo "# School of Life - Database Management"
    echo "# Daily backup at 2:00 AM"
    echo "$BACKUP_CRON"
    echo ""
    echo "# Monitoring every 15 minutes"
    echo "$MONITOR_CRON"
    echo ""
    echo "# Daily summary at 9:00 AM"
    echo "$SUMMARY_CRON"
} > /tmp/school_crontab

# Встановлення crontab (якщо є права)
if command -v crontab &> /dev/null; then
    crontab /tmp/school_crontab
    echo "✅ Cron jobs встановлено"
else
    echo "⚠️ crontab недоступний, cron jobs збережено в /tmp/school_crontab"
    echo "   Вручну встановіть їх командою: crontab /tmp/school_crontab"
fi

# Створення logrotate конфігурації
echo "📝 Налаштування logrotate..."
cat > /tmp/school_logrotate << 'EOF'
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    create 644 root root
}
EOF

if [ -d "/etc/logrotate.d" ]; then
    cp /tmp/school_logrotate /etc/logrotate.d/school
    echo "✅ Logrotate налаштовано"
else
    echo "⚠️ /etc/logrotate.d недоступний, конфігурація збережена в /tmp/school_logrotate"
fi

# Перевірка PostgreSQL клієнта
echo "🔍 Перевірка PostgreSQL клієнта..."
if command -v pg_dump &> /dev/null; then
    echo "✅ pg_dump доступний"
else
    echo "❌ pg_dump недоступний! Встановіть postgresql-client"
    echo "   Для Ubuntu/Debian: apt-get install postgresql-client"
    echo "   Для Alpine: apk add postgresql-client"
fi

# Перевірка Python залежностей для моніторингу
echo "🐍 Перевірка Python залежностей..."
if python3 -c "import asyncpg" 2>/dev/null; then
    echo "✅ asyncpg доступний"
else
    echo "❌ asyncpg недоступний! Встановіть: pip install asyncpg"
fi

# Створення початкового backup
echo "💾 Створення початкового backup..."
if [ -f "/app/scripts/db_backup.sh" ] && command -v pg_dump &> /dev/null; then
    /app/scripts/db_backup.sh || echo "⚠️ Backup не вдався, перевірте налаштування"
else
    echo "⚠️ Пропущено початковий backup"
fi

# Запуск першого моніторингу
echo "📊 Запуск першого моніторингу..."
if [ -f "/app/scripts/db_monitoring.py" ]; then
    python3 /app/scripts/db_monitoring.py --save || echo "⚠️ Моніторинг не вдався"
else
    echo "⚠️ Пропущено перший моніторинг"
fi

echo ""
echo "🎉 НАЛАШТУВАННЯ ЗАВЕРШЕНО!"
echo ""
echo "📋 НАСТУПНІ КРОКИ:"
echo "1. Перевірте логи в /app/logs/"
echo "2. Переконайтеся що backup працює: ls -la /app/backups/"
echo "3. Налаштуйте віддалене збереження backup (rsync, s3, etc.)"
echo "4. Додайте alerting для критичних метрик"
echo "5. Налаштуйте SMTP для email сповіщень"
echo ""
echo "📝 КОРИСНІ КОМАНДИ:"
echo "   Ручний backup: /app/scripts/db_backup.sh"
echo "   Моніторинг: python3 /app/scripts/db_monitoring.py"
echo "   Перегляд cron: crontab -l"
echo "   Логи backup: tail -f /app/logs/backup_cron.log"
echo "   Логи моніторингу: tail -f /app/logs/monitor_cron.log"

exit 0