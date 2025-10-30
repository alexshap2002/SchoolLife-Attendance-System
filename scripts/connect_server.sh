brCg3DMh15mXf4Z7PsRbrCg3DMh15mXf4Z7PsRbrCg3DMh15mXf4Z7PsR#!/bin/bash

# Скрипт для безпечного підключення до сервера
# Використовуйте цей скрипт для першого підключення з паролем

SERVER="root@213.199.43.90"
APP_PATH="/opt/schoola"

echo "🏫 School of Life - Підключення до сервера"
echo "=========================================="
echo ""
echo "🔐 Сервер: $SERVER"
echo "📁 Шлях: $APP_PATH"
echo ""

# Функція для безпечного виконання команд на сервері
safe_ssh() {
    local command="$1"
    echo "📡 Виконую: $command"
    ssh -o StrictHostKeyChecking=no "$SERVER" "$command"
}

echo "🔍 1. Перевіряю існуючі програми на сервері..."
safe_ssh "echo 'Підключення успішне'; echo ''; echo 'Поточна директорія:'; pwd; echo ''; echo 'Запущені Docker контейнери:'; docker ps 2>/dev/null || echo 'Docker не запущений'; echo ''; echo 'Існуючі програми в /opt:'; ls -la /opt/ 2>/dev/null || echo 'Папка /opt порожня'"

echo ""
echo "🛡️ 2. Перевіряю безпечність встановлення..."
safe_ssh "echo 'Перевіряю порти:'; netstat -tlnp | grep -E ':(80|443|8000|5432)' || echo 'Порти вільні'; echo ''; echo 'Перевіряю процеси:'; ps aux | grep -E '(nginx|apache|caddy|postgres)' | grep -v grep || echo 'Веб-сервери не запущені'"

echo ""
echo "✅ Перевірка завершена!"
echo ""
echo "🚀 Наступні кроки:"
echo "1. Переконайтеся, що немає конфліктів з портами 80, 443"
echo "2. Якщо все безпечно, запустіть: make bootstrap"
echo "3. Потім: make ship"
