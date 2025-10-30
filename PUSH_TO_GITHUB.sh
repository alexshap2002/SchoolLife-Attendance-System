#!/bin/bash

echo "🚀 Завантаження на GitHub..."
echo ""
echo "📝 Твій GitHub username (з git config): alexshap2002"
echo ""
echo "Введи свій GitHub username (або натисни Enter якщо alexshap2002):"
read -r github_user

if [ -z "$github_user" ]; then
    github_user="alexshap2002"
fi

echo ""
echo "✅ Використовую username: $github_user"
echo "📦 Додаю remote..."

git remote add origin "https://github.com/$github_user/SchoolLife-Attendance-System.git" 2>/dev/null || git remote set-url origin "https://github.com/$github_user/SchoolLife-Attendance-System.git"

echo "✅ Remote додано"
echo "🚀 Push в GitHub..."

git branch -M main
git push -u origin main

echo ""
echo "🎉 ГОТОВО! Репозиторій на GitHub:"
echo "   https://github.com/$github_user/SchoolLife-Attendance-System"
