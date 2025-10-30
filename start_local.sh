#!/bin/bash

echo "🚀 Запуск локального додатку 'Школа Життя'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Перевірка чи існує база даних
echo "🔍 Перевірка локальної бази даних..."
if docker ps | grep -q school-db; then
    echo "✅ База даних school-db запущена"
else
    echo "❌ ПОМИЛКА: База даних school-db НЕ запущена!"
    echo "   Будь ласка, спочатку запусти базу даних:"
    echo "   docker start school-db"
    exit 1
fi

echo ""
echo "🔧 Перевірка підключення до бази даних..."
docker exec school-db psql -U school_user -d school_db -c "SELECT 'Підключення OK' as status;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Підключення до бази даних працює"
else
    echo "❌ ПОМИЛКА: Не вдалося підключитися до бази даних!"
    exit 1
fi

echo ""
echo "🛑 Зупинка старих контейнерів додатку (якщо є)..."
docker compose -f docker-compose.local.yml down

echo ""
echo "🏗️ Збірка Docker образів..."
docker compose -f docker-compose.local.yml build

echo ""
echo "🚀 Запуск додатку..."
docker compose -f docker-compose.local.yml up -d

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Додаток запущено!"
echo ""
echo "📍 Веб-інтерфейс: http://localhost:8000/admin/"
echo "📍 API: http://localhost:8000/docs"
echo "📍 Health: http://localhost:8000/health"
echo ""
echo "📊 Перегляд логів:"
echo "   docker compose -f docker-compose.local.yml logs -f"
echo ""
echo "🛑 Зупинка додатку:"
echo "   docker compose -f docker-compose.local.yml down"
echo ""
echo "⚠️  База даних НЕ буде зупинена (вона працює окремо)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

