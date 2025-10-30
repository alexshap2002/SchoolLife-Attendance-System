# 🤖 AI Agent Database Guide
## Система Управління Школою Життя (School of Life Management System)

> **Призначення:** Повний опис бази даних для AI агентів, які працюють з системою.  
> **Версія БД:** 2.0  
> **СУБД:** PostgreSQL 16+  
> **Кодування:** UTF-8  
> **Часовий пояс:** Europe/Kyiv (UTC+2/+3)

---

## 📋 ЗМІСТ

1. [Загальна Архітектура](#загальна-архітектура)
2. [Повний Опис Таблиць](#повний-опис-таблиць)
3. [Бізнес-Логіка та Правила](#бізнес-логіка-та-правила)
4. [Зв'язки та Каскадні Операції](#звязки-та-каскадні-операції)
5. [Робочі Сценарії (Workflows)](#робочі-сценарії-workflows)
6. [Оптимізація та Індекси](#оптимізація-та-індекси)
7. [Важливі Constraints](#важливі-constraints)
8. [API Patterns](#api-patterns)
9. [Поширені Помилки та Їх Вирішення](#поширені-помилки-та-їх-вирішення)

---

## 🏗️ ЗАГАЛЬНА АРХІТЕКТУРА

### Призначення Системи

Система управляє **позашкільними гуртками** для дітей:
- 👥 Реєстрація та облік **студентів** (діти 3-18 років)
- 👨‍🏫 Управління **вчителями** та їх зарплатами
- 🎯 Організація **гуртків** (танці, музика, спорт, тощо)
- 📅 Створення **розкладів** для гуртків
- ✅ Облік **відвідуваності** через Telegram бот
- 💰 Автоматичний розрахунок **зарплат** вчителям
- 📊 Аналітика та звітність

### Ключові Концепції

1. **Student (Студент)** - дитина, яка відвідує гуртки
2. **Teacher (Вчитель)** - педагог, який проводить заняття
3. **Club (Гурток)** - навчальний напрямок (наприклад, "Танці", "Англійська мова")
4. **Schedule (Розклад)** - конкретний час заняття (наприклад, "Танці, понеділок 17:00")
5. **Enrollment (Запис)** - зв'язок студента з гуртком
6. **ScheduleEnrollment (Запис на розклад)** - зв'язок студента з конкретним розкладом
7. **LessonEvent (Подія уроку)** - конкретне заплановане заняття (наприклад, "Танці, 15 жовтня 2025, 17:00")
8. **Attendance (Відвідуваність)** - фактична присутність студента на уроці
9. **ConductedLesson (Проведений урок)** - підсумок проведеного заняття
10. **Payroll (Зарплата)** - нарахування грошей вчителю за урок

### Життєвий Цикл Уроку

```
1. СТВОРЕННЯ РОЗКЛАДУ
   ↓
2. АВТОМАТИЧНА ГЕНЕРАЦІЯ LESSON_EVENTS (через scheduler)
   ↓
3. ВІДПРАВКА НОТИФІКАЦІЇ ВЧИТЕЛЮ в Telegram (за 30 хв до уроку)
   ↓
4. ВЧИТЕЛЬ ВІДМІЧАЄ ПРИСУТНІХ через Telegram bot
   ↓
5. СТВОРЕННЯ CONDUCTED_LESSON (підсумок)
   ↓
6. АВТОМАТИЧНЕ НАРАХУВАННЯ PAYROLL (зарплата)
```

---

## 📊 ПОВНИЙ ОПИС ТАБЛИЦЬ

### 1️⃣ `students` - Студенти

**Призначення:** Зберігає інформацію про дітей, які відвідують гуртки.

**Критичні поля:**
- `id` (PRIMARY KEY) - унікальний ідентифікатор
- `first_name`, `last_name` - ім'я та прізвище (обов'язкові)
- `birth_date` - дата народження
- `age` - вік (може бути NULL)
- `grade` - клас навчання (наприклад, "5-А", "10", "дошкільник")
- `location` - населений пункт (наприклад, "Брусилів", "Житомир")
- `phone_child` - телефон дитини

**Контакти батьків:**
- `father_name` - ПІБ батька
- `mother_name` - ПІБ матері
- `phone_father` - телефон батька
- `phone_mother` - телефон матері
- ⚠️ `parent_name` - **DEPRECATED**, не використовувати

**Соціальні пільги (benefit_*):**
- `benefit_low_income` - малозабезпечена сім'я
- `benefit_large_family` - багатодітна сім'я
- `benefit_military_family` - сім'я військового
- `benefit_internally_displaced` - внутрішньо переміщені особи (ВПО)
- `benefit_orphan` - сирота
- `benefit_disability` - дитина з інвалідністю
- `benefit_social_risk` - соціально незахищені

**Зв'язки:**
- `enrollments` → Записи на гуртки
- `schedule_enrollments` → Записи на конкретні розклади
- `attendance` → Відвідуваність уроків

**Бізнес-правила:**
- Вік студента: 3-18 років
- Один студент може бути записаний на декілька гуртків
- Студент може бути записаний на кілька розкладів одного гуртка
- При видаленні студента каскадно видаляються всі його записи та відвідуваність

---

### 2️⃣ `teachers` - Вчителі

**Призначення:** Педагоги, які проводять заняття.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `full_name` - повне ім'я (обов'язкове)
- `email` - електронна пошта (унікальна, може бути NULL)
- `phone` - телефон
- `tg_chat_id` - **ВАЖЛИВО!** Telegram Chat ID для bot интеграції (унікальний)
- `active` - чи активний вчитель (default: TRUE)

**Telegram Integration:**
Поле `tg_chat_id` використовується для:
- Відправки нотифікацій про майбутні уроки
- Отримання відміток відвідуваності
- Координації розкладу

**Зв'язки:**
- `schedules` → Розклади вчителя
- `lesson_events` → Події уроків
- `conducted_lessons` → Проведені уроки
- `pay_rates` → Тарифи оплати
- `payroll` → Нарахована зарплата

**Бізнес-правила:**
- Вчитель може мати кілька розкладів
- При зміні вчителя в розкладі автоматично оновлюються майбутні `lesson_events`
- Вчителя НЕ можна видалити, якщо є пов'язані проведені уроки (історичні дані)
- Замість видалення - встановити `active = FALSE`

---

### 3️⃣ `clubs` - Гуртки

**Призначення:** Навчальні напрямки та секції.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `name` - назва гуртка (обов'язкова, наприклад: "Танці", "Англійська мова", "Футбол")
- `description` - опис гуртка
- `duration_min` - тривалість заняття в хвилинах (30-300 хв)

**Зв'язки:**
- `schedules` → Розклади цього гуртка
- `enrollments` → Студенти, записані на гурток
- `lesson_events` → Події уроків гуртка
- `conducted_lessons` → Проведені уроки

**Бізнес-правила:**
- Один гурток може мати кілька розкладів (різні дні/часи)
- Тривалість уроку зазвичай 45-90 хвилин
- Гурток НЕ можна видалити, якщо є активні розклади

---

### 4️⃣ `schedules` - Розклади

**Призначення:** Регулярний розклад занять для гуртка.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `club_id` (FK → clubs) - гурток
- `teacher_id` (FK → teachers) - вчитель
- `day_of_week` - день тижня (0=Понеділок, 6=Неділя)
- `start_time` - час початку (наприклад, "17:00")
- `end_time` - час закінчення (наприклад, "18:30")
- `group_name` - назва групи (наприклад, "Група А", "Початківці")
- `active` - чи активний розклад (default: TRUE)

**Приклад:**
```
club_id = 5 (Танці)
teacher_id = 3 (Іванова Марія)
day_of_week = 0 (Понеділок)
start_time = 17:00
end_time = 18:30
group_name = "Група А"
```

**Зв'язки:**
- `schedule_enrollments` → Студенти, записані на цей розклад
- `lesson_events` → Автоматично згенеровані події уроків

**Бізнес-правила:**
- При створенні розкладу автоматично генеруються `lesson_events` на майбутнє
- При зміні `teacher_id` оновлюються всі майбутні `lesson_events`
- При деактивації (`active = FALSE`) майбутні події скасовуються (status = 'CANCELLED')
- Розклад НЕ видаляється фізично - тільки деактивується

---

### 5️⃣ `enrollments` - Записи на Гуртки (загальні)

**Призначення:** Зв'язує студента з гуртком (загальний рівень).

**Критичні поля:**
- `id` (PRIMARY KEY)
- `student_id` (FK → students)
- `club_id` (FK → clubs)
- `enrolled_at` - дата запису

**Constraint:**
- `UNIQUE(student_id, club_id)` - студент не може бути записаний на один гурток двічі

**Бізнес-логіка:**
- Це "загальний" запис: "Студент Х відвідує Гурток Y"
- Не містить інформації про конкретний розклад
- Використовується для звітності та аналітики

---

### 6️⃣ `schedule_enrollments` - Записи на Розклади (конкретні)

**Призначення:** Зв'язує студента з конкретним розкладом.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `student_id` (FK → students)
- `schedule_id` (FK → schedules)
- `enrolled_at` - дата запису

**Constraint:**
- `UNIQUE(student_id, schedule_id)` - студент не може бути записаний на один розклад двічі

**Бізнес-логіка:**
- Це "конкретний" запис: "Студент Х відвідує Танці по Понеділках о 17:00"
- Визначає, які студенти повинні бути на конкретному уроці
- При створенні `lesson_event` система бере список студентів з `schedule_enrollments`

**Важливо:**
- Студент може бути записаний на **один гурток**, але на **кілька розкладів** цього гуртка
- Наприклад: "Танці по Понеділках 17:00" та "Танці по Середах 18:00"

---

### 7️⃣ `lesson_events` - Події Уроків

**Призначення:** Конкретні заплановані уроки з можливістю відстеження статусу.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `schedule_id` (FK → schedules, **NULLABLE** для manual lessons)
- `teacher_id` (FK → teachers)
- `club_id` (FK → clubs)
- `date` - дата уроку (наприклад, "2025-10-15")
- `start_at` - точний час початку (timestamp з timezone)
- `status` - статус події (ENUM)

**Статуси (`LessonEventStatus`):**
- `PLANNED` - урок заплановано, нотифікація не відправлена
- `SENT` - нотифікацію відправлено вчителю
- `COMPLETED` - урок проведено, відвідуваність відмічена
- `SKIPPED` - урок пропущено/скасовано
- `CANCELLED` - урок скасовано (при деактивації розкладу)

**Telegram Nотифікації:**
- `teacher_chat_id` - Telegram ID вчителя
- `notify_at` - коли відправити нотифікацію (зазвичай за 30 хв до уроку)
- `sent_at` - коли фактично відправлено
- `send_attempts` - кількість спроб відправки
- `last_error` - остання помилка (якщо була)

**Метадані:**
- `idempotency_key` - для запобігання дублікатів
- `payload` - додаткові дані в JSON

**Зв'язки:**
- `attendance` → Відвідуваність на цьому уроці
- `conducted_lessons` → Підсумок проведеного уроку
- `payroll` → Зарплата за цей урок

**Бізнес-правила:**
- Автоматично генеруються scheduler'ом на основі `schedules`
- Можна створити вручну (manual lesson) без `schedule_id`
- При зміні вчителя в розкладі оновлюються тільки майбутні події з `status = PLANNED`
- Після проведення уроку створюється `conducted_lesson`

---

### 8️⃣ `attendance` - Відвідуваність

**Призначення:** Фактична присутність студентів на уроках.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `lesson_event_id` (FK → lesson_events)
- `student_id` (FK → students)
- `status` - статус відвідуваності (ENUM)
- `marked_by` - Telegram Chat ID того, хто відмітив
- `marked_at` - час відмітки

**Статуси (`AttendanceStatus`):**
- `PRESENT` - присутній
- `ABSENT` - відсутній

**Constraint:**
- `UNIQUE(lesson_event_id, student_id)` - одна відмітка на студента на урок

**Бізнес-логіка:**
- Створюється вчителем через Telegram bot
- Після збору відміток автоматично створюється `conducted_lesson`
- Використовується для:
  - Статистики відвідуваності
  - Розрахунку зарплати (платимо тільки за присутніх)
  - Звітності для батьків

---

### 9️⃣ `conducted_lessons` - Проведені Уроки

**Призначення:** Підсумки проведених занять з статистикою.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `teacher_id` (FK → teachers)
- `club_id` (FK → clubs)
- `lesson_event_id` (FK → lesson_events, може бути NULL для manual)
- `lesson_date` - дата проведення
- `lesson_duration_minutes` - тривалість
- `total_students` - загальна кількість студентів
- `present_students` - присутні студенти
- `absent_students` - відсутні студенти
- `attendance_rate` - **GENERATED колонка** (автоматично розраховується)
- `notes` - нотатки вчителя
- `lesson_topic` - тема уроку
- `is_salary_calculated` - чи нараховано зарплату
- `is_valid_for_salary` - **GENERATED** (TRUE якщо є хоч один присутній)

**Обчислювані поля:**
```sql
attendance_rate = (present_students / total_students * 100)
is_valid_for_salary = (present_students > 0)
```

**Бізнес-правила:**
- Автоматично створюється після збору відвідуваності
- Можна створити вручну (для старих уроків)
- Зарплата нараховується ТІЛЬКИ якщо є присутні студенти (`is_valid_for_salary = TRUE`)
- НЕ можна видалити, якщо є пов'язана зарплата

---

### 🔟 `pay_rates` - Тарифи Оплати

**Призначення:** Ставки оплати для вчителів.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `teacher_id` (FK → teachers)
- `rate_per_lesson` - ставка за урок (наприклад, 500.00 грн)
- `effective_from` - дата початку дії тарифу
- `effective_to` - дата закінчення дії (NULL = діє досі)

**Бізнес-логіка:**
- Вчитель може мати різні тарифи в різні періоди
- При розрахунку зарплати береться актуальний тариф на дату уроку
- Якщо тарифу немає - зарплата не нараховується

**Приклад:**
```sql
-- Вчитель Іванов з 1 вересня отримує 600 грн за урок
teacher_id = 3
rate_per_lesson = 600.00
effective_from = 2025-09-01
effective_to = NULL
```

---

### 1️⃣1️⃣ `payroll` - Зарплати

**Призначення:** Нарахування зарплат вчителям.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `teacher_id` (FK → teachers)
- `lesson_event_id` (FK → lesson_events, може бути NULL)
- `amount_decimal` - сума (DECIMAL(10,2))
- `status` - статус нарахування
- `period_start`, `period_end` - період
- `notes` - примітки
- `basis` - основа нарахування (ENUM)

**Статуси:**
- `CALCULATED` - розраховано, але не підтверджено
- `APPROVED` - підтверджено адміністратором
- `PAID` - виплачено

**Основи нарахування (`PayrollBasis`):**
- `PER_LESSON` - за урок (стандартно)
- `FIXED` - фіксована сума
- `MANUAL` - ручне нарахування

**Бізнес-правила:**
- Автоматично створюється після проведення уроку
- Розраховується на основі `pay_rates`
- Можна створити вручну для додаткових виплат
- НЕ можна видалити запис зі статусом `PAID`

**Приклад розрахунку:**
```python
# Після уроку з 5 присутніми студентами:
teacher_rate = 600 грн
payroll.amount_decimal = 600.00
payroll.basis = "PER_LESSON"
payroll.status = "CALCULATED"
```

---

### 1️⃣2️⃣ `bot_schedules` - Розклади для Bot

**Призначення:** Регулярні завдання для бота (нотифікації, нагадування).

**Критичні поля:**
- `id` (PRIMARY KEY)
- `name` - назва завдання
- `schedule_type` - тип (interval/cron/date)
- `schedule_config` - конфігурація в JSON
- `action_type` - тип дії (send_notification, remind_teacher, тощо)
- `action_params` - параметри в JSON
- `is_active` - чи активне
- `last_run` - остання дія
- `next_run` - наступна дія

**Приклад:**
```json
{
  "name": "Нагадування вчителям за 30 хв",
  "schedule_type": "interval",
  "schedule_config": {"minutes": 5},
  "action_type": "check_upcoming_lessons",
  "is_active": true
}
```

---

### 1️⃣3️⃣ `admin_automations` - Автоматизації

**Призначення:** Правила автоматичних дій у системі.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `name` - назва автоматизації
- `trigger_type` - тип тригера (time_before_lesson, after_lesson, тощо)
- `trigger_config` - JSON з налаштуваннями
- `action_type` - тип дії
- `action_config` - JSON з налаштуваннями дії
- `is_active` - чи активна

**Приклади:**
```json
// Нагадування вчителю
{
  "trigger_type": "time_before_lesson",
  "trigger_config": {"minutes": 30},
  "action_type": "send_telegram_message"
}

// Автоматичне нарахування зарплати
{
  "trigger_type": "after_lesson_completed",
  "action_type": "calculate_payroll"
}
```

---

### 1️⃣4️⃣ `admin_users` - Адміністратори

**Призначення:** Користувачі з доступом до адмін-панелі.

**Критичні поля:**
- `id` (PRIMARY KEY)
- `username` - унікальний логін
- `email` - електронна пошта
- `password_hash` - хеш пароля (bcrypt)
- `is_active` - чи активний
- `is_superuser` - чи супер-адміністратор
- `last_login` - останній вхід

**Бізнес-правила:**
- Паролі зберігаються в хешованому вигляді
- Супер-адміністратор має доступ до всіх функцій
- Можна деактивувати, але не видаляти

---

## 🔗 ЗВ'ЯЗКИ ТА КАСКАДНІ ОПЕРАЦІЇ

### Cascade Rules (Важливо!)

#### При видаленні Student:
```sql
CASCADE DELETE:
✅ enrollments (записи на гуртки)
✅ schedule_enrollments (записи на розклади)
✅ attendance (відвідуваність)
```

#### При видаленні Teacher:
```sql
❌ RESTRICT if:
  - має проведені уроки (conducted_lessons)
  - має нараховану зарплату (payroll)

✅ Рішення: встановити active = FALSE
```

#### При видаленні Club:
```sql
❌ RESTRICT if:
  - має активні розклади (schedules)
  - має проведені уроки (conducted_lessons)
```

#### При зміні Teacher в Schedule:
```sql
UPDATE CASCADE:
✅ lesson_events (майбутні події)
  - teacher_id → новий вчитель
  - teacher_chat_id → новий chat_id
  - status → PLANNED (перевідправити нотифікацію)
```

#### При деактивації Schedule (active = FALSE):
```sql
UPDATE CASCADE:
✅ lesson_events (майбутні події)
  - status → CANCELLED
```

---

## 🔄 РОБОЧІ СЦЕНАРІЇ (WORKFLOWS)

### Сценарій 1: Створення Нового Студента та Запис на Гурток

```python
# 1. Створюємо студента
student = Student(
    first_name="Марія",
    last_name="Петренко",
    age=10,
    grade="5-А",
    phone_child="+380501234567",
    mother_name="Петренко Олена Іванівна",
    phone_mother="+380501111111",
    location="Брусилів"
)
db.add(student)
db.commit()

# 2. Записуємо на гурток (загальний запис)
enrollment = Enrollment(
    student_id=student.id,
    club_id=5  # Танці
)
db.add(enrollment)

# 3. Записуємо на конкретний розклад
schedule_enrollment = ScheduleEnrollment(
    student_id=student.id,
    schedule_id=12  # Танці, Понеділок 17:00
)
db.add(schedule_enrollment)
db.commit()
```

---

### Сценарій 2: Автоматична Генерація Уроків

```python
# Scheduler worker виконує щоденно:

for schedule in db.query(Schedule).filter(Schedule.active == True):
    # Генеруємо уроки на наступні 7 днів
    today = datetime.now().date()
    
    for day_offset in range(7):
        future_date = today + timedelta(days=day_offset)
        
        # Перевіряємо чи це потрібний день тижня
        if future_date.weekday() == schedule.day_of_week:
            # Перевіряємо чи не існує вже такого уроку
            exists = db.query(LessonEvent).filter(
                LessonEvent.schedule_id == schedule.id,
                LessonEvent.date == future_date
            ).first()
            
            if not exists:
                # Створюємо новий урок
                start_at = datetime.combine(future_date, schedule.start_time)
                notify_at = start_at - timedelta(minutes=30)
                
                lesson_event = LessonEvent(
                    schedule_id=schedule.id,
                    teacher_id=schedule.teacher_id,
                    club_id=schedule.club_id,
                    date=future_date,
                    start_at=start_at,
                    teacher_chat_id=schedule.teacher.tg_chat_id,
                    notify_at=notify_at,
                    status='PLANNED'
                )
                db.add(lesson_event)
                
db.commit()
```

---

### Сценарій 3: Відправка Нотифікації Вчителю

```python
# Bot worker виконує кожні 5 хвилин:

now = datetime.now()

# Знаходимо уроки для нотифікації
lessons_to_notify = db.query(LessonEvent).filter(
    LessonEvent.notify_at <= now,
    LessonEvent.status == 'PLANNED',
    LessonEvent.teacher_chat_id.isnot(None)
).all()

for lesson in lessons_to_notify:
    # Отримуємо список студентів
    students = db.query(Student).join(ScheduleEnrollment).filter(
        ScheduleEnrollment.schedule_id == lesson.schedule_id
    ).all()
    
    # Формуємо повідомлення
    message = f"""
🔔 Нагадування про урок!

📚 Гурток: {lesson.club.name}
📅 Дата: {lesson.date.strftime('%d.%m.%Y')}
🕐 Час: {lesson.start_at.strftime('%H:%M')}
👥 Студентів очікується: {len(students)}

Список студентів:
{'\n'.join([f"• {s.first_name} {s.last_name}" for s in students])}

Після уроку відмітьте присутніх через /mark_attendance
"""
    
    # Відправляємо через Telegram Bot
    try:
        bot.send_message(lesson.teacher_chat_id, message)
        
        lesson.status = 'SENT'
        lesson.sent_at = now
        lesson.send_attempts += 1
        
    except Exception as e:
        lesson.last_error = str(e)
        lesson.send_attempts += 1
        
db.commit()
```

---

### Сценарій 4: Відмітка Відвідуваності та Створення Підсумку

```python
# Вчитель відмічає присутніх через Telegram:

# 1. Отримуємо lesson_event_id від вчителя
lesson_event = db.query(LessonEvent).get(lesson_event_id)

# 2. Отримуємо список студентів, які мають бути на уроці
enrolled_students = db.query(Student).join(ScheduleEnrollment).filter(
    ScheduleEnrollment.schedule_id == lesson_event.schedule_id
).all()

# 3. Вчитель відмічає присутніх (отримуємо список ID)
present_student_ids = [1, 3, 5, 7]  # ID присутніх

# 4. Створюємо записи відвідуваності
for student in enrolled_students:
    attendance = Attendance(
        lesson_event_id=lesson_event.id,
        student_id=student.id,
        status='PRESENT' if student.id in present_student_ids else 'ABSENT',
        marked_by=lesson_event.teacher_chat_id
    )
    db.add(attendance)

# 5. Оновлюємо статус уроку
lesson_event.status = 'COMPLETED'
lesson_event.completed_at = datetime.now()

# 6. Створюємо підсумок уроку
total = len(enrolled_students)
present = len(present_student_ids)
absent = total - present

conducted_lesson = ConductedLesson(
    teacher_id=lesson_event.teacher_id,
    club_id=lesson_event.club_id,
    lesson_event_id=lesson_event.id,
    lesson_date=lesson_event.start_at,
    lesson_duration_minutes=lesson_event.club.duration_min,
    total_students=total,
    present_students=present,
    absent_students=absent
)
db.add(conducted_lesson)
db.commit()

# 7. Автоматично нараховуємо зарплату (якщо є присутні)
if present > 0:
    # Знаходимо актуальний тариф
    pay_rate = db.query(PayRate).filter(
        PayRate.teacher_id == lesson_event.teacher_id,
        PayRate.effective_from <= lesson_event.date,
        or_(PayRate.effective_to.is_(None), PayRate.effective_to >= lesson_event.date)
    ).first()
    
    if pay_rate:
        payroll = Payroll(
            teacher_id=lesson_event.teacher_id,
            lesson_event_id=lesson_event.id,
            amount_decimal=pay_rate.rate_per_lesson,
            basis='PER_LESSON',
            status='CALCULATED'
        )
        db.add(payroll)
        
        conducted_lesson.is_salary_calculated = True

db.commit()
```

---

### Сценарій 5: Зміна Вчителя в Розкладі

```python
# Адміністратор змінює вчителя:

schedule_id = 12
new_teacher_id = 5

# 1. Отримуємо розклад
schedule = db.query(Schedule).get(schedule_id)
old_teacher_id = schedule.teacher_id

# 2. Оновлюємо розклад
schedule.teacher_id = new_teacher_id
new_teacher = db.query(Teacher).get(new_teacher_id)

# 3. КРИТИЧНО: Оновлюємо всі майбутні lesson_events
today = datetime.now().date()

future_events = db.query(LessonEvent).filter(
    LessonEvent.schedule_id == schedule_id,
    LessonEvent.date >= today,
    LessonEvent.status == 'PLANNED'
).all()

for event in future_events:
    event.teacher_id = new_teacher_id
    event.teacher_chat_id = new_teacher.tg_chat_id
    event.status = 'PLANNED'  # Перепланувати нотифікацію
    event.notify_at = event.start_at - timedelta(minutes=30)
    event.sent_at = None

db.commit()

# ✅ Результат:
# - Старі уроки (вже проведені) залишаються за старим вчителем
# - Майбутні уроки переназначаються новому вчителю
# - Зарплата нараховується правильно кожному вчителю
```

---

## ⚡ ОПТИМІЗАЦІЯ ТА ІНДЕКСИ

### Критичні Індекси

```sql
-- 1. Пошук студентів за іменем (регістронезалежний)
CREATE INDEX idx_students_name_lower ON students 
(LOWER(first_name), LOWER(last_name));

-- 2. Фільтрація за локацією
CREATE INDEX idx_students_location ON students (location);

-- 3. Активні вчителі з Telegram
CREATE INDEX idx_teachers_active ON teachers (active) 
WHERE active = TRUE;

CREATE INDEX idx_teachers_tg_chat_id ON teachers (tg_chat_id) 
WHERE tg_chat_id IS NOT NULL;

-- 4. Відвідуваність (найчастіші запити)
CREATE INDEX idx_attendance_student_status ON attendance 
(student_id, status);

CREATE INDEX idx_attendance_lesson_event ON attendance 
(lesson_event_id);

-- 5. Події уроків (критичні для bot'а)
CREATE INDEX idx_lesson_events_date_status ON lesson_events 
(date, status);

CREATE INDEX idx_lesson_events_notify_at ON lesson_events 
(notify_at) 
WHERE notify_at IS NOT NULL AND status = 'PLANNED';

CREATE INDEX idx_lesson_events_composite ON lesson_events 
(teacher_id, club_id, date, status);

-- 6. Розклади
CREATE INDEX idx_schedules_active ON schedules (active) 
WHERE active = TRUE;

CREATE INDEX idx_schedules_club_teacher ON schedules 
(club_id, teacher_id);

-- 7. Записи на розклади
CREATE INDEX idx_schedule_enrollments_schedule ON schedule_enrollments 
(schedule_id);

CREATE INDEX idx_schedule_enrollments_student ON schedule_enrollments 
(student_id);

-- 8. Проведені уроки (звітність)
CREATE INDEX idx_conducted_lessons_date ON conducted_lessons 
(lesson_date DESC);

CREATE INDEX idx_conducted_lessons_teacher_date ON conducted_lessons 
(teacher_id, lesson_date DESC);

-- 9. Зарплати
CREATE INDEX idx_payroll_teacher_created ON payroll 
(teacher_id, created_at DESC);

CREATE INDEX idx_payroll_created_month ON payroll 
(DATE_TRUNC('month', created_at));
```

### Рекомендації по Запитам

#### ✅ ПРАВИЛЬНО:
```sql
-- Використовуйте індекси
SELECT * FROM students 
WHERE LOWER(first_name) = 'марія' 
AND LOWER(last_name) = 'петренко';

-- Завжди фільтруйте за датою для великих таблиць
SELECT * FROM conducted_lessons 
WHERE lesson_date >= CURRENT_DATE - INTERVAL '30 days';

-- Використовуйте EXISTS замість COUNT
SELECT * FROM teachers t 
WHERE EXISTS (
    SELECT 1 FROM schedules s 
    WHERE s.teacher_id = t.id AND s.active = TRUE
);
```

#### ❌ НЕПРАВИЛЬНО:
```sql
-- НЕ використовуйте LIKE без індексу
SELECT * FROM students WHERE first_name LIKE '%марія%';

-- НЕ робіть COUNT(*) на великих таблицях без WHERE
SELECT COUNT(*) FROM lesson_events;

-- НЕ використовуйте OR з різними полями
SELECT * FROM lesson_events 
WHERE teacher_id = 5 OR club_id = 3;
```

---

## 🔒 ВАЖЛИВІ CONSTRAINTS

### CHECK Constraints

```sql
-- 1. Вік студентів: 3-18 років
ALTER TABLE students ADD CONSTRAINT check_student_age 
CHECK (age IS NULL OR (age >= 3 AND age <= 18));

-- 2. Тривалість уроків: 30-300 хвилин
ALTER TABLE clubs ADD CONSTRAINT check_lesson_duration 
CHECK (duration_min IS NULL OR (duration_min >= 30 AND duration_min <= 300));

-- 3. Позитивні суми
ALTER TABLE payroll ADD CONSTRAINT check_positive_amount 
CHECK (amount_decimal > 0);

ALTER TABLE pay_rates ADD CONSTRAINT check_positive_rate 
CHECK (rate_per_lesson > 0);

-- 4. День тижня: 0-6
ALTER TABLE schedules ADD CONSTRAINT check_day_of_week 
CHECK (day_of_week >= 0 AND day_of_week <= 6);

-- 5. Час: start < end
ALTER TABLE schedules ADD CONSTRAINT check_time_order 
CHECK (start_time < end_time);

-- 6. Статистика уроків
ALTER TABLE conducted_lessons ADD CONSTRAINT check_students_count 
CHECK (
    present_students >= 0 AND 
    absent_students >= 0 AND 
    total_students = present_students + absent_students
);
```

### UNIQUE Constraints

```sql
-- 1. Email вчителя
ALTER TABLE teachers ADD CONSTRAINT unique_teacher_email 
UNIQUE (email);

-- 2. Telegram Chat ID
ALTER TABLE teachers ADD CONSTRAINT unique_teacher_tg_chat_id 
UNIQUE (tg_chat_id);

-- 3. Записи студентів
ALTER TABLE enrollments ADD CONSTRAINT unique_student_club 
UNIQUE (student_id, club_id);

ALTER TABLE schedule_enrollments ADD CONSTRAINT unique_student_schedule 
UNIQUE (student_id, schedule_id);

-- 4. Відвідуваність
ALTER TABLE attendance ADD CONSTRAINT unique_attendance 
UNIQUE (lesson_event_id, student_id);

-- 5. Username адміністратора
ALTER TABLE admin_users ADD CONSTRAINT unique_admin_username 
UNIQUE (username);
```

---

## 🎯 API PATTERNS

### Pagination Pattern

```python
# Для великих таблиць завжди використовуйте pagination:

def get_students(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = None
):
    query = db.query(Student)
    
    if location:
        query = query.filter(Student.location == location)
    
    return query.offset(skip).limit(limit).all()
```

### Filtering Pattern

```python
# Використовуйте динамічні фільтри:

def get_lesson_events(
    db: Session,
    teacher_id: Optional[int] = None,
    club_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None
):
    query = db.query(LessonEvent)
    
    if teacher_id:
        query = query.filter(LessonEvent.teacher_id == teacher_id)
    if club_id:
        query = query.filter(LessonEvent.club_id == club_id)
    if date_from:
        query = query.filter(LessonEvent.date >= date_from)
    if date_to:
        query = query.filter(LessonEvent.date <= date_to)
    if status:
        query = query.filter(LessonEvent.status == status)
    
    return query.order_by(LessonEvent.date.desc()).all()
```

### Eager Loading Pattern

```python
# Використовуйте selectinload для уникнення N+1 запитів:

from sqlalchemy.orm import selectinload

# ❌ ПОГАНО (N+1 problem):
students = db.query(Student).all()
for student in students:
    print(student.enrollments)  # Окремий запит для кожного студента

# ✅ ДОБРЕ:
students = db.query(Student).options(
    selectinload(Student.enrollments).selectinload(Enrollment.club)
).all()
for student in students:
    print(student.enrollments)  # Один запит для всіх
```

---

## ⚠️ ПОШИРЕНІ ПОМИЛКИ ТА ЇХ ВИРІШЕННЯ

### Помилка 1: Duplicate Key Error при Запису Студента

```
ERROR: duplicate key value violates unique constraint "unique_student_club"
```

**Причина:** Студент вже записаний на цей гурток.

**Рішення:**
```python
# Перевіряйте перед створенням:
existing = db.query(Enrollment).filter(
    Enrollment.student_id == student_id,
    Enrollment.club_id == club_id
).first()

if not existing:
    enrollment = Enrollment(student_id=student_id, club_id=club_id)
    db.add(enrollment)
    db.commit()
```

---

### Помилка 2: CASCADE DELETE при Видаленні Вчителя

```
ERROR: update or delete on table "teachers" violates foreign key constraint
```

**Причина:** Вчитель має проведені уроки або нараховану зарплату.

**Рішення:**
```python
# НЕ видаляємо, а деактивуємо:
teacher.active = False
db.commit()
```

---

### Помилка 3: NULL Telegram Chat ID

```
ERROR: cannot send notification - teacher_chat_id is NULL
```

**Причина:** Вчитель не зареєстрований в Telegram боті.

**Рішення:**
```python
# Перевіряйте перед відправкою:
if lesson_event.teacher_chat_id:
    bot.send_message(lesson_event.teacher_chat_id, message)
else:
    logger.warning(f"Teacher {teacher.id} has no Telegram")
```

---

### Помилка 4: Зарплата Нараховується Старому Вчителю

**Причина:** Не оновили майбутні `lesson_events` після зміни вчителя в розкладі.

**Рішення:** Див. "Сценарій 5: Зміна Вчителя в Розкладі" вище.

---

### Помилка 5: Schedule_ID NULL при Manual Lesson

**Причина:** Намагаєтеся створити manual lesson, але поле schedule_id було NOT NULL.

**Рішення:**
```sql
-- Міграція виконана:
ALTER TABLE lesson_events ALTER COLUMN schedule_id DROP NOT NULL;
```

```python
# Тепер можна створювати manual lessons:
lesson = LessonEvent(
    schedule_id=None,  # ✅ Дозволено
    teacher_id=teacher_id,
    club_id=club_id,
    date=date,
    status='PLANNED'
)
```

---

## 📊 ВАЖЛИВІ ЗАПИТИ ДЛЯ АНАЛІТИКИ

### 1. Статистика Відвідуваності по Гуртках (Місяць)

```sql
SELECT 
    c.name as club_name,
    COUNT(DISTINCT cl.id) as total_lessons,
    SUM(cl.present_students) as total_present,
    SUM(cl.total_students) as total_expected,
    ROUND(
        SUM(cl.present_students)::decimal / 
        NULLIF(SUM(cl.total_students), 0) * 100, 
        2
    ) as attendance_rate_percent
FROM clubs c
LEFT JOIN conducted_lessons cl ON c.id = cl.club_id
WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY c.id, c.name
ORDER BY attendance_rate_percent DESC NULLS LAST;
```

---

### 2. Топ-10 Найактивніших Студентів

```sql
SELECT 
    s.id,
    s.first_name || ' ' || s.last_name as student_name,
    s.grade,
    COUNT(DISTINCT a.lesson_event_id) as lessons_attended,
    COUNT(DISTINCT e.club_id) as clubs_enrolled,
    ROUND(
        COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END)::decimal / 
        NULLIF(COUNT(a.id), 0) * 100,
        2
    ) as attendance_percent
FROM students s
LEFT JOIN attendance a ON s.id = a.student_id
LEFT JOIN enrollments e ON s.id = e.student_id
WHERE a.marked_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY s.id, s.first_name, s.last_name, s.grade
ORDER BY lessons_attended DESC
LIMIT 10;
```

---

### 3. Зарплати Вчителів за Період

```sql
SELECT 
    t.full_name as teacher_name,
    COUNT(DISTINCT p.id) as payments_count,
    COUNT(DISTINCT cl.id) as lessons_conducted,
    SUM(cl.present_students) as total_students_taught,
    SUM(p.amount_decimal) as total_earned,
    ROUND(AVG(p.amount_decimal), 2) as avg_per_lesson
FROM teachers t
LEFT JOIN payroll p ON t.id = p.teacher_id
LEFT JOIN conducted_lessons cl ON p.lesson_event_id = cl.lesson_event_id
WHERE p.created_at >= DATE_TRUNC('month', CURRENT_DATE)
  AND p.status IN ('APPROVED', 'PAID')
GROUP BY t.id, t.full_name
ORDER BY total_earned DESC NULLS LAST;
```

---

### 4. Найпопулярніші Гуртки (За Записами)

```sql
SELECT 
    c.name as club_name,
    COUNT(DISTINCT e.student_id) as students_enrolled,
    COUNT(DISTINCT s.id) as schedules_count,
    COUNT(DISTINCT cl.id) as lessons_conducted_month,
    ROUND(AVG(cl.attendance_rate), 2) as avg_attendance_rate
FROM clubs c
LEFT JOIN enrollments e ON c.id = e.club_id
LEFT JOIN schedules s ON c.id = s.club_id AND s.active = TRUE
LEFT JOIN conducted_lessons cl ON c.id = cl.club_id 
    AND cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY c.id, c.name
ORDER BY students_enrolled DESC;
```

---

### 5. Студенти з Пільгами (Фільтрація)

```sql
SELECT 
    s.first_name || ' ' || s.last_name as student_name,
    s.grade,
    s.location,
    CASE 
        WHEN s.benefit_low_income THEN 'Малозабезпечені'
        WHEN s.benefit_large_family THEN 'Багатодітна сім\'я'
        WHEN s.benefit_military_family THEN 'Сім\'я військового'
        WHEN s.benefit_internally_displaced THEN 'ВПО'
        WHEN s.benefit_orphan THEN 'Сирота'
        WHEN s.benefit_disability THEN 'Інвалідність'
        WHEN s.benefit_social_risk THEN 'Соціальний ризик'
        ELSE 'Інше'
    END as benefit_type,
    COUNT(DISTINCT e.club_id) as clubs_count
FROM students s
LEFT JOIN enrollments e ON s.id = e.student_id
WHERE 
    s.benefit_low_income = TRUE OR
    s.benefit_large_family = TRUE OR
    s.benefit_military_family = TRUE OR
    s.benefit_internally_displaced = TRUE OR
    s.benefit_orphan = TRUE OR
    s.benefit_disability = TRUE OR
    s.benefit_social_risk = TRUE
GROUP BY s.id, s.first_name, s.last_name, s.grade, s.location,
         s.benefit_low_income, s.benefit_large_family, 
         s.benefit_military_family, s.benefit_internally_displaced,
         s.benefit_orphan, s.benefit_disability, s.benefit_social_risk
ORDER BY s.last_name, s.first_name;
```

---

## 🔐 БЕЗПЕКА ТА BEST PRACTICES

### 1. SQL Injection Prevention

```python
# ❌ ПОГАНО - вразливо до SQL injection:
query = f"SELECT * FROM students WHERE name = '{name}'"

# ✅ ДОБРЕ - використовуйте параметризовані запити:
query = db.query(Student).filter(Student.first_name == name)
```

---

### 2. Transaction Management

```python
# Завжди використовуйте транзакції для пов'язаних операцій:

try:
    # Створюємо conducted_lesson
    conducted_lesson = ConductedLesson(...)
    db.add(conducted_lesson)
    
    # Створюємо payroll
    payroll = Payroll(...)
    db.add(payroll)
    
    # Оновлюємо статус
    lesson_event.status = 'COMPLETED'
    
    # Комітимо все разом
    db.commit()
    
except Exception as e:
    db.rollback()
    logger.error(f"Transaction failed: {e}")
    raise
```

---

### 3. Sensitive Data

```python
# НЕ логуйте чутливу інформацію:
# ❌ logger.info(f"Student phone: {student.phone_child}")

# ✅ Логуйте тільки ID:
logger.info(f"Updated student: {student.id}")
```

---

### 4. Rate Limiting

```python
# Для Telegram bot - обмежуйте частоту запитів:

from time import sleep

for lesson in lessons_to_notify:
    bot.send_message(lesson.teacher_chat_id, message)
    sleep(0.1)  # 10 повідомлень/сек (Telegram limit: 30/сек)
```

---

## 📝 КОРИСНІ VIEW ДЛЯ ЗВІТНОСТІ

### View 1: Student Analytics

```sql
CREATE VIEW v_student_analytics AS
SELECT 
    s.id,
    s.first_name,
    s.last_name,
    s.age,
    s.grade,
    s.location,
    COUNT(DISTINCT e.club_id) as clubs_count,
    COUNT(DISTINCT a.lesson_event_id) as total_lessons,
    COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END) as present_count,
    COUNT(CASE WHEN a.status = 'ABSENT' THEN 1 END) as absent_count,
    ROUND(
        COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END)::decimal /
        NULLIF(COUNT(a.id), 0) * 100,
        2
    ) as attendance_percent
FROM students s
LEFT JOIN enrollments e ON s.id = e.student_id
LEFT JOIN attendance a ON s.id = a.student_id
GROUP BY s.id, s.first_name, s.last_name, s.age, s.grade, s.location;
```

---

### View 2: Teacher Workload

```sql
CREATE VIEW v_teacher_workload AS
SELECT 
    t.id,
    t.full_name,
    COUNT(DISTINCT s.id) as schedules_count,
    COUNT(DISTINCT le.id) FILTER (
        WHERE le.status = 'PLANNED' AND le.date >= CURRENT_DATE
    ) as upcoming_lessons,
    COUNT(DISTINCT cl.id) FILTER (
        WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
    ) as lessons_this_month,
    SUM(cl.present_students) FILTER (
        WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
    ) as students_taught_this_month
FROM teachers t
LEFT JOIN schedules s ON t.id = s.teacher_id AND s.active = TRUE
LEFT JOIN lesson_events le ON t.id = le.teacher_id
LEFT JOIN conducted_lessons cl ON t.id = cl.teacher_id
GROUP BY t.id, t.full_name;
```

---

## 🎓 ПІДСУМОК ДЛЯ AI АГЕНТІВ

### Ключові Правила:

1. **Завжди перевіряйте `active = TRUE`** для schedules та teachers
2. **Використовуйте індекси** - фільтруйте за індексованими полями
3. **Pagination обов'язкова** для великих таблиць
4. **CASCADE operations** - розумійте що видаляється автоматично
5. **Транзакції** - використовуйте для пов'язаних операцій
6. **NULL checks** - особливо для `tg_chat_id` та `schedule_id`
7. **Generated columns** - не записуйте вручну `attendance_rate` та `is_valid_for_salary`
8. **Timezones** - всі дати з timezone (Europe/Kyiv)

### Що НЕ можна робити:

❌ Видаляти вчителів з історією (використовуйте `active = FALSE`)
❌ Видаляти schedules (використовуйте `active = FALSE`)
❌ Змінювати проведені уроки (conducted_lessons) - тільки нові
❌ Видаляти payroll зі статусом `PAID`
❌ Створювати duplicates (перевіряйте UNIQUE constraints)
❌ Забувати про CASCADE при зміні teacher_id в schedule

### Типові Операції:

✅ Створити студента → записати на гурток → записати на розклад
✅ Створити розклад → автоматично генеруються lesson_events
✅ Змінити вчителя → оновити майбутні lesson_events
✅ Відмітити відвідуваність → створити conducted_lesson → нарахувати payroll
✅ Деактивувати розклад → скасувати майбутні lesson_events

---

**📞 Підтримка:** Це живий документ. Оновлюйте його при змінах схеми БД.  
**🤖 AI-Friendly:** Цей документ оптимізований для швидкого розуміння AI агентами.  
**📅 Останнє оновлення:** Жовтень 2025

