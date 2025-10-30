#!/bin/bash
# ===============================================================
# 💾 АВТОМАТИЧНИЙ BACKUP БАЗИ ДАНИХ
# ===============================================================
# 📅 Дата створення: 2025-09-15
# 🎯 Мета: Регулярний backup PostgreSQL БД для школи
# ===============================================================

set -euo pipefail

# Конфігурація
DB_NAME="school_db"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="/app/backups"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Логування
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${BACKUP_DIR}/backup.log"
}

# Створення директорії для backup
mkdir -p "${BACKUP_DIR}"

log "🚀 Початок backup БД ${DB_NAME}"

# Перевірка з'єднання з БД
if ! pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" > /dev/null 2>&1; then
    log "❌ ПОМИЛКА: Неможливо підключитися до БД"
    exit 1
fi

# Створення backup файлів
BACKUP_FILE="${BACKUP_DIR}/school_db_${DATE}.sql"
BACKUP_CUSTOM="${BACKUP_DIR}/school_db_${DATE}.dump"
BACKUP_COMPRESSED="${BACKUP_DIR}/school_db_${DATE}.sql.gz"

log "📝 Створюю SQL dump..."
if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --verbose --clean --if-exists --no-owner --no-privileges \
    --file="${BACKUP_FILE}"; then
    log "✅ SQL dump створено: ${BACKUP_FILE}"
else
    log "❌ ПОМИЛКА створення SQL dump"
    exit 1
fi

log "📝 Створюю custom format dump..."
if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --format=custom --compress=9 --verbose \
    --file="${BACKUP_CUSTOM}"; then
    log "✅ Custom dump створено: ${BACKUP_CUSTOM}"
else
    log "❌ ПОМИЛКА створення custom dump"
    exit 1
fi

log "📝 Стискаю SQL файл..."
if gzip -c "${BACKUP_FILE}" > "${BACKUP_COMPRESSED}"; then
    log "✅ Compressed backup створено: ${BACKUP_COMPRESSED}"
    rm "${BACKUP_FILE}"  # Видаляємо нестиснений файл
else
    log "❌ ПОМИЛКА стискання"
fi

# Перевірка розміру backup
BACKUP_SIZE=$(du -h "${BACKUP_CUSTOM}" | cut -f1)
log "📊 Розмір backup: ${BACKUP_SIZE}"

# Очищення старих backup
log "🧹 Очищення backup старіших за ${RETENTION_DAYS} днів..."
OLD_BACKUPS=$(find "${BACKUP_DIR}" -name "school_db_*.dump" -mtime +${RETENTION_DAYS} 2>/dev/null || true)
OLD_COMPRESSED=$(find "${BACKUP_DIR}" -name "school_db_*.sql.gz" -mtime +${RETENTION_DAYS} 2>/dev/null || true)

if [ -n "${OLD_BACKUPS}" ]; then
    echo "${OLD_BACKUPS}" | xargs rm -f
    log "🗑️ Видалено старі .dump файли"
fi

if [ -n "${OLD_COMPRESSED}" ]; then
    echo "${OLD_COMPRESSED}" | xargs rm -f
    log "🗑️ Видалено старі .sql.gz файли"
fi

# Статистика backup
TOTAL_BACKUPS=$(find "${BACKUP_DIR}" -name "school_db_*.dump" | wc -l)
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)

log "📈 СТАТИСТИКА:"
log "   💾 Загальна кількість backup: ${TOTAL_BACKUPS}"
log "   📦 Загальний розмір: ${TOTAL_SIZE}"
log "   🕒 Останній backup: ${DATE}"

log "🎉 Backup завершено успішно!"

# Опціонально: відправка на віддалений сервер
# if command -v rsync &> /dev/null; then
#     log "📤 Синхронізація з віддаленим сервером..."
#     rsync -avz "${BACKUP_DIR}/" user@remote-server:/path/to/remote/backups/
#     log "✅ Синхронізація завершена"
# fi

exit 0
