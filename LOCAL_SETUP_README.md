# 🏠 Локальний Запуск CRM "Школа Життя"

## 📋 **ІНСТРУКЦІЯ ДЛЯ ЗАПУСКУ**

---

## ✅ **ПЕРЕДУМОВИ**

### 1️⃣ Локальна База Даних Має Працювати

Перевір що контейнер `school-db` запущений:

```bash
docker ps | grep school-db
```

Повинно показати:
```
d8bbfa98a11a   postgres:15-alpine   ...   Up 2 hours   0.0.0.0:5432->5432/tcp   school-db
```

Якщо база даних НЕ запущена:
```bash
docker start school-db
```

### 2️⃣ Переконайся Що База Містить Дані

```bash
docker exec school-db psql -U school_user -d school_db -c "\dt"
```

Повинно показати список таблиць: `students`, `teachers`, `clubs`, `schedules`, тощо.

---

## 🚀 **ЗАПУСК ДОДАТКУ**

### Простий Спосіб (Скрипт):

```bash
./start_local.sh
```

### Ручний Спосіб (Docker Compose):

```bash
# 1. Збірка образів
docker-compose -f docker-compose.local.yml build

# 2. Запуск контейнерів
docker-compose -f docker-compose.local.yml up -d

# 3. Перегляд логів
docker-compose -f docker-compose.local.yml logs -f
```

---

## 🌐 **ДОСТУП ДО ДОДАТКУ**

Після запуску:

- 🌐 **Веб-інтерфейс:** http://localhost:8000/admin/
- 📚 **API Документація:** http://localhost:8000/docs
- ❤️ **Health Check:** http://localhost:8000/health
- 📱 **WebApp (Telegram):** http://localhost:3001

**Логін в адмін-панель:**
- Email: `admin@school.local`
- Пароль: `admin123`

---

## 🛑 **ЗУПИНКА ДОДАТКУ**

### Простий Спосіб (Скрипт):

```bash
./stop_local.sh
```

### Ручний Спосіб:

```bash
docker-compose -f docker-compose.local.yml down
```

**⚠️ ВАЖЛИВО:** База даних `school-db` НЕ буде зупинена (вона працює окремо і містить цінні дані).

---

## 🔍 **ПЕРЕВІРКА СТАНУ**

### Переглянути запущені контейнери:

```bash
docker ps
```

Повинно бути **3 контейнери**:
- `school-db` (PostgreSQL база даних - ТА ЩО ВЖЕ ІСНУВАЛА)
- `new--_webapp_1` (FastAPI додаток)
- `new--_dispatcher_1` (Telegram бот)

### Переглянути логи:

```bash
# Всі логи
docker-compose -f docker-compose.local.yml logs -f

# Тільки webapp
docker-compose -f docker-compose.local.yml logs -f webapp

# Тільки dispatcher (Telegram бот)
docker-compose -f docker-compose.local.yml logs -f dispatcher
```

---

## 🔗 **ЯК ЦЕ ПРАЦЮЄ**

### Підключення До Бази Даних:

```
[webapp контейнер]  ─┐
                     ├─→ host.docker.internal:5432 ─→ [school-db контейнер]
[dispatcher контейнер]─┘                               (існуюча БД)
```

**Ключові моменти:**
- ✅ Використовується **ІСНУЮЧА** база даних `school-db`
- ✅ **НІЯКИХ ЗМІН** в базі даних не робиться
- ✅ Додаток **ТІЛЬКИ ЧИТАЄ ТА ЗАПИСУЄ** дані (як і має бути)
- ✅ База даних працює **ОКРЕМО** від додатку
- ✅ Зупинка додатку **НЕ ЗУПИНЯЄ** базу даних

---

## 📊 **НАЛАШТУВАННЯ**

### Змінні Оточення (вбудовані в docker-compose.local.yml):

```yaml
POSTGRES_HOST=host.docker.internal  # Підключення до локальної БД
POSTGRES_PORT=5432
POSTGRES_DB=school_db
POSTGRES_USER=school_user
POSTGRES_PASSWORD=school_password_123

TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
WEBAPP_URL=http://localhost:3001
```

**⚠️ Якщо потрібно змінити налаштування:**
Редагуй `docker-compose.local.yml` → перезапусти додаток

---

## 🛠️ **ДІАГНОСТИКА ПРОБЛЕМ**

### Проблема 1: "База даних не запущена"

```bash
# Перевір чи існує контейнер
docker ps -a | grep school-db

# Запусти базу даних
docker start school-db

# Перевір що запустилася
docker ps | grep school-db
```

### Проблема 2: "Не можу підключитися до бази"

```bash
# Перевір підключення
docker exec school-db psql -U school_user -d school_db -c "SELECT 1;"

# Переглянути логи бази даних
docker logs school-db
```

### Проблема 3: "Webapp не запускається"

```bash
# Переглянути логи
docker-compose -f docker-compose.local.yml logs webapp

# Перезапустити
docker-compose -f docker-compose.local.yml restart webapp
```

### Проблема 4: "Telegram бот конфліктує"

```bash
# Зупини dispatcher
docker-compose -f docker-compose.local.yml stop dispatcher

# Подивись логи
docker-compose -f docker-compose.local.yml logs dispatcher
```

**Примітка:** Якщо бот вже працює на сервері, локальний dispatcher може конфліктувати.

---

## ⚠️ **ВАЖЛИВІ ПРАВИЛА БЕЗПЕКИ**

### ✅ ЩО МОЖНА РОБИТИ:

- ✅ Запускати і зупиняти додаток (`webapp`, `dispatcher`)
- ✅ Переглядати логи
- ✅ Тестувати функціонал через веб-інтерфейс
- ✅ Додавати/редагувати студентів, вчителів, розклади
- ✅ Проводити уроки через Telegram

### ❌ ЩО НЕ МОЖНА РОБИТИ:

- ❌ **НЕ** зупиняй базу даних `school-db` (там цінні дані!)
- ❌ **НЕ** видаляй контейнер `school-db`
- ❌ **НЕ** запускай `docker-compose down` без `-f docker-compose.local.yml`
- ❌ **НЕ** змінюй налаштування бази даних вручну

---

## 🔄 **ОНОВЛЕННЯ ДОДАТКУ**

Якщо змінив код:

```bash
# 1. Зупини додаток
./stop_local.sh

# 2. Перезбери образи
docker-compose -f docker-compose.local.yml build

# 3. Запусти знову
./start_local.sh
```

---

## 📚 **ДОДАТКОВІ КОМАНДИ**

### Виконати міграції бази даних:

```bash
docker-compose -f docker-compose.local.yml exec webapp alembic upgrade head
```

### Відкрити shell в webapp контейнері:

```bash
docker-compose -f docker-compose.local.yml exec webapp bash
```

### Відкрити psql (база даних):

```bash
docker exec -it school-db psql -U school_user -d school_db
```

---

## ✅ **ГОТОВО!**

Тепер у тебе є:
- ✅ Локальний додаток, підключений до існуючої БД
- ✅ Безпечний запуск (БД не зачіпається)
- ✅ Прості скрипти для керування
- ✅ Повна інструкція з діагностики

**База даних залишається в безпеці, а ти можеш тестувати додаток локально! 🎉**


