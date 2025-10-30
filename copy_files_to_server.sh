#!/bin/bash
# ===================================================================
# СКРИПТ ДЛЯ КОПІЮВАННЯ ФАЙЛІВ НА БОЙОВИЙ СЕРВЕР
# ===================================================================
# Виконувати на ЛОКАЛЬНОМУ комп'ютері!
# ===================================================================

SERVER="root@185.233.39.11"
SERVER_PATH="/root/school-life-app"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                 ║"
echo "║        📤 КОПІЮВАННЯ ФАЙЛІВ НА БОЙОВИЙ СЕРВЕР                 ║"
echo "║                                                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Перевірка чи файли існують локально
echo "🔍 Перевірка файлів..."

FILES=(
    "database_optimizations.sql"
    "app/services/lesson_event_manager.py"
    "app/workers/dispatcher.py"
    "run_manual_cleanup.py"
    "deploy_to_production.sh"
)

MISSING=0
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - НЕ ЗНАЙДЕНО!"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "❌ Деякі файли відсутні. Перевір що ти в правильній директорії."
    exit 1
fi

echo ""
echo "📤 Копіюю файли на сервер..."
echo ""

# Копіюємо SQL файл
echo "1️⃣  Копіюю database_optimizations.sql..."
scp database_optimizations.sql "$SERVER:$SERVER_PATH/"
echo "   ✅ Скопійовано"

# Копіюємо Python файли
echo "2️⃣  Копіюю app/services/lesson_event_manager.py..."
scp app/services/lesson_event_manager.py "$SERVER:$SERVER_PATH/app/services/"
echo "   ✅ Скопійовано"

echo "3️⃣  Копіюю app/workers/dispatcher.py..."
scp app/workers/dispatcher.py "$SERVER:$SERVER_PATH/app/workers/"
echo "   ✅ Скопійовано"

echo "4️⃣  Копіюю run_manual_cleanup.py..."
scp run_manual_cleanup.py "$SERVER:$SERVER_PATH/"
echo "   ✅ Скопійовано"

# Копіюємо deployment скрипт
echo "5️⃣  Копіюю deploy_to_production.sh..."
scp deploy_to_production.sh "$SERVER:$SERVER_PATH/"
echo "   ✅ Скопійовано"

# Надаємо права на виконання
echo ""
echo "🔧 Надаю права на виконання deployment скрипту..."
ssh "$SERVER" "chmod +x $SERVER_PATH/deploy_to_production.sh"
echo "   ✅ Готово"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                 ║"
echo "║           ✅ ВСІ ФАЙЛИ СКОПІЙОВАНО НА СЕРВЕР!                 ║"
echo "║                                                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 НАСТУПНІ КРОКИ:"
echo ""
echo "1️⃣  Підключись до сервера:"
echo "   ssh $SERVER"
echo ""
echo "2️⃣  Перейди в директорію проекту:"
echo "   cd $SERVER_PATH"
echo ""
echo "3️⃣  Запусти deployment скрипт:"
echo "   ./deploy_to_production.sh"
echo ""
echo "⚠️  ВАЖЛИВО: Deployment скрипт:"
echo "   • Створить backup БД автоматично"
echo "   • Застосує всі оптимізації"
echo "   • Перезапустить контейнери"
echo "   • Покаже детальний звіт"
echo ""

