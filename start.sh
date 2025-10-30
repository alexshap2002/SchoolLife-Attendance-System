#!/bin/bash

echo "🏫 Запуск School of Life з локальною PostgreSQL БД..."

# Очищаємо старі контейнери
echo "🧹 Очищення старих контейнерів..."
docker stop $(docker ps -q --filter "publish=8000") 2>/dev/null || echo "Немає контейнерів на порту 8000"
docker stop $(docker ps -q --filter "name=school-life") 2>/dev/null || echo "Немає school-life контейнерів"
docker stop $(docker ps -q --filter "name=new-app") 2>/dev/null || echo "Немає new-app контейнерів"
docker container prune -f

# Зупиняємо попередні контейнери цього проєкту
echo "🛑 Зупиняємо попередні контейнери..."
docker-compose down

# Запускаємо з новою конфігурацією
echo "🚀 Запускаємо додаток..."
docker-compose up --build

echo "✅ Додаток запущено на http://localhost:8000"
