# 🏫 Школа життя - Система обліку відвідуваності

Система автоматизованого обліку відвідуваності для дитячої програми "Школа життя" з Telegram ботом, веб-адмінкою та інтеграцією з Google Sheets.

## 🚀 Основні можливості

- **Автоматичний облік відвідуваності** через Telegram бот
- **Веб-адмінка** для управління учнями, вчителями, гуртками
- **Розрахунок зарплати** вчителів (за заняття або за присутніх)
- **Експорт в Google Sheets** з автоматичною синхронізацією
- **Імпорт учнів** з XLSX/CSV файлів (українські назви колонок)
- **Автоматичні нагадування** вчителям про незбережену відвідуваність

## 🏗️ Архітектура

- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL
- **Bot**: aiogram v3
- **Scheduler**: APScheduler з часовою зоною Europe/Kyiv
- **Frontend**: Server-side rendering з Jinja2 + Bootstrap
- **Deploy**: Docker + docker-compose + Caddy (HTTPS)
- **Export**: Google Sheets API

## 📋 Встановлення

### 1. Підготовка

```bash
git clone <repository-url>
cd "TG bot School of life"
make setup
```

### 2. Налаштування

#### 2.1 Telegram Bot
1. Створіть бота через [@BotFather](https://t.me/botfather)
2. Отримайте токен і додайте в `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

#### 2.2 Google Sheets
1. Створіть проєкт в [Google Cloud Console](https://console.cloud.google.com/)
2. Увімкніть Google Sheets API та Google Drive API
3. Створіть Service Account і завантажте JSON ключ
4. Помістіть файл як `creds/service_account.json`
5. Створіть Google Spreadsheet і поділіться з email Service Account
6. Додайте ID таблиці в `.env`:
```bash
SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
```

#### 2.3 Налаштування .env
Відредагуйте файл `.env`:
```bash
# Environment
ENV=dev
TZ=Europe/Kyiv

# Database  
POSTGRES_DB=schoola
POSTGRES_USER=schoola
POSTGRES_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_very_secure_secret_key_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token

# Google Sheets
SHEETS_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/app/creds/service_account.json

# Admin
ADMIN_EMAIL=admin@schoola.local
ADMIN_PASSWORD=your_admin_password
```

### 3. Запуск

```bash
# Запуск всіх сервісів
make run

# Або окремо
docker compose up --build
```

### 4. Ініціалізація

```bash
# Застосувати міграції
make migrate

# Додати тестові дані (опціонально)
make seed
```

## 📖 Використання

### Адмін-панель
Відкрийте http://localhost/admin/ і увійдіть з:
- Email: `admin@schoola.local` 
- Пароль: `admin123` (або ваш з .env)

### API Документація
Доступна за адресою: http://localhost/docs

### Telegram Bot
1. Вчителі натискають `/start` для реєстрації
2. В час заняття бот автоматично надсилає чек-лист
3. Вчитель відмічає присутніх і натискає "Зберегти"
4. Через 15 хвилин приходить нагадування, якщо не збережено

## 📊 Імпорт даних

### Формат XLSX/CSV для учнів
Підтримувані колонки (українською):
- `Ім'я дитини:` → first_name
- `Прізвище дитини:` → last_name  
- `День народження дитини:` → birth_date
- `Вік:` → age
- `Клас у школі:` → grade
- `Телефон дитини:` → phone_child
- `Місце проживання:` → location
- `Адреса проживання:` → address
- `ПІБ батька/матері` → parent_name
- `Телефон матері:` → phone_mother
- `Телефон батька:` → phone_father
- `Яку пільгу ви маєте:*` → benefits_json

### Імпорт через API
```bash
curl -X POST "http://localhost/api/import/xlsx" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@students.xlsx"
```

## 🔧 Розробка

### Команди для розробки

```bash
# Перегляд логів
make logs

# Форматування коду
make format

# Лінтинг
make lint

# Тести
make test

# Оболонка в контейнері
make shell

# База даних
make db-shell

# Створення міграції
make migrate-create

# Бекап БД
make backup-db

# Відновлення БД
make restore-db FILE=backup.sql
```

### Структура проєкту

```
app/
├── core/           # Конфігурація, БД, безпека
├── models/         # SQLAlchemy моделі
├── api/           # FastAPI роутери
├── services/      # Бізнес-логіка
├── bot/           # Telegram бот
├── web/           # Веб-інтерфейс
└── main.py        # Головний файл

alembic/           # Міграції БД
scripts/           # Допоміжні скрипти
creds/            # Файли аутентифікації
```

## 📈 Моніторинг

### Health Check
```bash
curl http://localhost/health
```

### Логи
```bash
# Всі сервіси
docker compose logs -f

# Тільки додаток
docker compose logs -f app

# База даних
docker compose logs -f db
```

## 🔒 Безпека

- JWT токени для API
- HTTPS через Caddy
- Валідація власності занять в боті
- Аудит всіх змін в `audit_log`
- Захищені API ендпоінти (тільки для адмінів)

## 🐛 Усунення неполадок

### Бот не відповідає
1. Перевірте `TELEGRAM_BOT_TOKEN` в `.env`
2. Переконайтеся, що бот запущений: `docker compose logs app`
3. Перевірте, що вчитель натиснув `/start`

### Google Sheets не оновлюється  
1. Перевірте `service_account.json` в `creds/`
2. Переконайтеся, що Service Account має доступ до таблиці
3. Перевірте `SHEETS_SPREADSHEET_ID`

### База даних недоступна
```bash
# Перевірити стан
docker compose ps

# Перезапустити БД
docker compose restart db

# Перевірити логи
docker compose logs db
```

### Проблеми з міграціями
```bash
# Скинути БД і застосувати міграції заново
make clean
make run
make migrate
```

## 📝 TODO / Майбутні покращення

- [ ] Мобільний додаток для батьків
- [ ] SMS нотифікації
- [ ] Розширена аналітика відвідуваності
- [ ] Інтеграція з платіжними системами
- [ ] Багатомовність (англійська)
- [ ] Експорт звітів в PDF

## 🤝 Внесок

1. Fork репозиторій
2. Створіть feature branch (`git checkout -b feature/amazing-feature`)
3. Зробіть commit (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Створіть Pull Request

## 📄 Ліцензія

MIT License - деталі в файлі `LICENSE`

## 🤖 Тестування Telegram бота

### Швидкий тест
```bash
# Інтерактивний скрипт тестування
./test_bot.sh

# Або створити lesson_event вручну
docker exec school-db psql -U school_user -d school_db -c "
INSERT INTO lesson_events (schedule_id, date, club_id, teacher_id, teacher_chat_id, status, start_at, notify_at, send_attempts) 
SELECT s.id, CURRENT_DATE, s.club_id, s.teacher_id, t.tg_chat_id, 'PLANNED', 
       NOW() + INTERVAL '5 minutes', NOW() + INTERVAL '1 minute', 0
FROM schedules s 
JOIN teachers t ON t.id = s.teacher_id
WHERE s.active = true AND t.tg_chat_id IS NOT NULL
LIMIT 1;"
```

### Діагностика проблем
```bash
# Логи dispatcher
docker logs school-dispatcher --tail 20

# Перевірка lesson_events
docker exec school-db psql -U school_user -d school_db -c "
SELECT le.id, le.status, c.name 
FROM lesson_events le 
JOIN clubs c ON c.id = le.club_id 
WHERE le.date >= CURRENT_DATE 
ORDER BY le.notify_at DESC LIMIT 5;"

# Перевірка студентів та enrollments
docker exec school-db psql -U school_user -d school_db -c "
SELECT s.first_name, s.last_name, c.name 
FROM students s 
JOIN enrollments e ON s.id = e.student_id 
JOIN clubs c ON c.id = e.club_id;"
```

**📖 Детальний гайд**: [TELEGRAM_BOT_TESTING_GUIDE.md](./TELEGRAM_BOT_TESTING_GUIDE.md)

## 🐛 Основні проблеми та рішення

### 1. Бот не надсилає повідомлення
- Перевірити логи: `docker logs school-dispatcher --tail 20`
- Перевірити lesson_events: має бути `status='PLANNED'` та `notify_at` в минулому
- Перевірити активні розклади: `s.active = true`
- **Перевірити teacher_chat_id**: `SELECT id, teacher_chat_id FROM lesson_events WHERE teacher_chat_id IS NULL`

### 2. Кнопки не змінюють статус
- Перевірити constraint: `attendance_lesson_student_unique` має існувати
- Перевірити enrollments: студенти мають бути записані на гурток
- Перевірити імпорти в dispatcher.py: `Enrollment` має бути імпортований

### 3. Немає студентів у повідомленні
- Перевірити enrollments: `SELECT * FROM enrollments WHERE club_id = X`
- Додати студентів: `INSERT INTO enrollments (student_id, club_id) VALUES (X, Y)`

### 4. Dispatcher не запускається
```bash
# Перезапуск
docker restart school-dispatcher

# Повний перезапуск системи
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

## 💬 Підтримка

Для питань та підтримки створіть Issue в репозиторії або зв'яжіться з командою розробки.

---

**Школа життя** - допомагаємо дітям рости і розвиватися! 🌟
