# 🚀 ІНСТРУКЦІЯ: DEPLOYMENT НА БОЙОВИЙ СЕРВЕР

**Дата:** 2025-10-08  
**Сервер:** `root@185.233.39.11`  
**Проект:** `/root/school-life-app`

---

## 📋 **ЩО БУДЕ ЗРОБЛЕНО:**

1. ✅ Автоматичний BACKUP бази даних
2. ✅ Додавання 5 індексів для прискорення
3. ✅ Додавання 4 CHECK constraints
4. ✅ Очищення старих PLANNED подій
5. ✅ Оновлення коду (dispatcher + lesson_event_manager)
6. ✅ Перезапуск контейнерів
7. ✅ Перевірка працездатності

---

## 🎯 **МЕТОД 1: АВТОМАТИЧНИЙ (РЕКОМЕНДОВАНИЙ)**

### **Крок 1: Скопіювати файли на сервер**

**На локальному комп'ютері виконай:**

```bash
# Перейди в директорію проекту
cd /Users/oleksandrsapovalov/Робота/додаток\ ШЖ/new--

# Запусти скрипт копіювання
./copy_files_to_server.sh
```

**Що скопіюється:**
- ✅ `database_optimizations.sql`
- ✅ `app/services/lesson_event_manager.py`
- ✅ `app/workers/dispatcher.py`
- ✅ `run_manual_cleanup.py`
- ✅ `deploy_to_production.sh`

---

### **Крок 2: Запустити deployment на сервері**

**Підключись до сервера:**

```bash
ssh root@185.233.39.11
```

**На сервері виконай:**

```bash
cd /root/school-life-app
./deploy_to_production.sh
```

**Скрипт автоматично:**
1. Створить backup БД з датою/часом
2. Перевірить стан системи
3. Застосує всі SQL оптимізації
4. Почистить старі події
5. Оновить код
6. Перезапустить контейнери
7. Перевірить що все працює
8. Покаже детальний звіт

---

## 🛠️ **МЕТОД 2: РУЧНИЙ (ПОКРОКОВИЙ)**

Якщо хочеш контролювати кожен крок:

### **Крок 1: Копіювання файлів**

**З локального комп'ютера:**

```bash
# SQL оптимізації
scp database_optimizations.sql root@185.233.39.11:/root/school-life-app/

# Python файли
scp app/services/lesson_event_manager.py root@185.233.39.11:/root/school-life-app/app/services/
scp app/workers/dispatcher.py root@185.233.39.11:/root/school-life-app/app/workers/
scp run_manual_cleanup.py root@185.233.39.11:/root/school-life-app/

# Deployment скрипт
scp deploy_to_production.sh root@185.233.39.11:/root/school-life-app/
```

---

### **Крок 2: Підключення до сервера**

```bash
ssh root@185.233.39.11
cd /root/school-life-app
```

---

### **Крок 3: BACKUP бази даних**

```bash
# Створити backup
BACKUP_FILE="backup_before_optimization_$(date +%Y%m%d_%H%M%S).sql"
docker exec school-db pg_dump -U school_user -d school_db > "$BACKUP_FILE"

# Перевірити розмір
ls -lh $BACKUP_FILE
```

**Очікуваний розмір:** ~5-10 MB

---

### **Крок 4: Застосування SQL оптимізацій**

```bash
# Скопіювати SQL в контейнер
docker cp database_optimizations.sql school-db:/tmp/db_opt.sql

# Виконати SQL
docker exec school-db psql -U school_user -d school_db -f /tmp/db_opt.sql
```

**Очікуваний вивід:**
```
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
DO
DO
DO
DO
```

---

### **Крок 5: Валідація constraints**

```bash
# Перевірка на проблемні дані
docker exec school-db psql -U school_user -d school_db << 'EOF'
SELECT 'schedules.weekday' as check_type, COUNT(*) as violations 
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

# Валідувати constraints (якщо все 0)
docker exec school-db psql -U school_user -d school_db << 'EOF'
ALTER TABLE schedules VALIDATE CONSTRAINT schedules_weekday_check;
ALTER TABLE bot_schedules VALIDATE CONSTRAINT bot_schedules_offset_check;
ALTER TABLE schedules VALIDATE CONSTRAINT schedules_start_time_check;
ALTER TABLE clubs VALIDATE CONSTRAINT clubs_duration_check;
SELECT 'Constraints validated!' as result;
EOF
```

---

### **Крок 6: Очищення старих PLANNED подій**

```bash
# Перевірка скільки є
docker exec school-db psql -U school_user -d school_db -c "
SELECT COUNT(*) as old_planned_events
FROM lesson_events 
WHERE status = 'PLANNED' 
AND notify_at < NOW() 
AND sent_at IS NULL;
"

# Очищення (якщо є старі події)
docker exec school-db psql -U school_user -d school_db << 'EOF'
UPDATE lesson_events 
SET status = 'COMPLETED',
    completed_at = NOW()
WHERE status = 'PLANNED' 
AND notify_at < NOW() 
AND sent_at IS NULL;

SELECT 'Оновлено подій: ' || ROW_COUNT();
EOF
```

---

### **Крок 7: Оновлення коду та перезапуск**

```bash
# Зупинити контейнери
docker compose -f docker-compose.server.yml down

# Перебудувати образ
docker compose -f docker-compose.server.yml build --no-cache webapp

# Запустити
docker compose -f docker-compose.server.yml up -d

# Перевірити статус
docker compose -f docker-compose.server.yml ps
```

---

### **Крок 8: Перевірка працездатності**

```bash
# Логи webapp
docker compose -f docker-compose.server.yml logs --tail=30 webapp

# Логи dispatcher
docker compose -f docker-compose.server.yml logs --tail=30 dispatcher

# Тест продуктивності
docker exec school-db psql -U school_user -d school_db << 'EOF'
EXPLAIN ANALYZE
SELECT * FROM lesson_events 
WHERE status = 'PLANNED' 
AND notify_at <= NOW() 
AND sent_at IS NULL 
ORDER BY notify_at ASC 
LIMIT 30;
EOF
```

**Шукай в результаті:**
```
Index Scan using idx_lesson_events_status_notify_at
```

---

## 🔙 **ROLLBACK (якщо щось не так)**

### **Відкотити БД:**

```bash
# Зупинити контейнери
docker compose -f docker-compose.server.yml down

# Відновити backup
docker exec -i school-db psql -U school_user -d school_db < backup_before_optimization_YYYYMMDD_HHMMSS.sql

# Запустити контейнери
docker compose -f docker-compose.server.yml up -d
```

### **Відкотити код:**

```bash
# Відновити з Git
git checkout HEAD -- app/services/lesson_event_manager.py
git checkout HEAD -- app/workers/dispatcher.py

# Перебудувати
docker compose -f docker-compose.server.yml build webapp
docker compose -f docker-compose.server.yml up -d
```

---

## ✅ **ПЕРЕВІРОЧНИЙ CHECKLIST**

### **Перед deployment:**
- [ ] Backup бази даних створено
- [ ] Всі файли скопійовано на сервер
- [ ] Перевірено що контейнери працюють

### **Під час deployment:**
- [ ] SQL скрипт виконався без помилок
- [ ] Constraints валідовано
- [ ] Старі події очищено
- [ ] Контейнери перезапущено успішно

### **Після deployment:**
- [ ] Контейнери працюють (docker ps)
- [ ] Немає помилок в логах
- [ ] Webapp відповідає на порту 8000
- [ ] Dispatcher працює (логи показують polling)
- [ ] Індекс використовується (EXPLAIN ANALYZE)
- [ ] Telegram bot працює

---

## 📊 **ОЧІКУВАНІ РЕЗУЛЬТАТИ**

### **Продуктивність:**
- ⚡ Dispatcher: з 50ms → 5ms
- ⚡ Attendance: з 150ms → 30ms
- ⚡ Payroll: з 80ms → 15ms

### **Навантаження:**
- 💾 БД запити: з 6/хв → 2/хв
- 🔋 CPU: -30%

---

## 🆘 **ЯКЩО ВИНИКЛИ ПРОБЛЕМИ**

### **Помилка при створенні індексу:**
```bash
# Перевірити чи вже існує
docker exec school-db psql -U school_user -d school_db -c "\d lesson_events"
```

### **Помилка при валідації constraint:**
```bash
# Знайти проблемні дані
docker exec school-db psql -U school_user -d school_db -c "
SELECT * FROM schedules WHERE weekday NOT BETWEEN 1 AND 7;
"
```

### **Контейнери не запускаються:**
```bash
# Подивитись детальні логи
docker compose -f docker-compose.server.yml logs
```

### **Telegram bot не працює:**
```bash
# Перевірити dispatcher логи
docker compose -f docker-compose.server.yml logs dispatcher | grep -i error
```

---

## 📝 **КОМАНДИ ДЛЯ МОНІТОРИНГУ**

```bash
# Статус контейнерів
docker compose -f docker-compose.server.yml ps

# Живі логи
docker compose -f docker-compose.server.yml logs -f

# Перевірка БД
docker exec school-db psql -U school_user -d school_db -c "
SELECT 
    COUNT(*) FILTER (WHERE status = 'PLANNED') as planned,
    COUNT(*) FILTER (WHERE status = 'SENT') as sent,
    COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed
FROM lesson_events;
"

# Використання індексів
docker exec school-db psql -U school_user -d school_db -c "
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE indexname LIKE 'idx_%' 
ORDER BY tablename;
"
```

---

**Готово до deployment! Обирай метод (автоматичний або ручний) та починай!** 🚀

