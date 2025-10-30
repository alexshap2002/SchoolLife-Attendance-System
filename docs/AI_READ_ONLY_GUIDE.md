# 🤖 AI Read-Only Database Guide
## Гайд для AI Агентів (Тільки Читання Даних)

> **Призначення:** Опис бази даних для AI агентів, які працюють ТІЛЬКИ з читанням даних (SELECT запити).  
> **Операції:** ✅ SELECT, ✅ JOIN, ✅ GROUP BY, ✅ Аналітика | ❌ INSERT, ❌ UPDATE, ❌ DELETE  
> **СУБД:** PostgreSQL 16+  
> **Кодування:** UTF-8  
> **Часовий пояс:** Europe/Kyiv (UTC+2/+3)

---

## 📋 ЗМІСТ

1. [Що Можна Робити](#що-можна-робити)
2. [Структура Таблиць (READ)](#структура-таблиць-read)
3. [Готові SELECT Запити](#готові-select-запити)
4. [Типові Звіти](#типові-звіти)
5. [Аналітика та Статистика](#аналітика-та-статистика)
6. [Корисні JOIN Patterns](#корисні-join-patterns)
7. [Фільтрація Даних](#фільтрація-даних)
8. [Оптимізація Читання](#оптимізація-читання)

---

## ✅ ЩО МОЖНА РОБИТИ

### Дозволені Операції:

```sql
✅ SELECT - читання даних
✅ JOIN - об'єднання таблиць
✅ WHERE - фільтрація
✅ GROUP BY - групування
✅ ORDER BY - сортування
✅ LIMIT - обмеження кількості
✅ COUNT, SUM, AVG - агрегація
✅ CASE WHEN - умовна логіка
✅ WITH (CTE) - підзапити
```

### ❌ Заборонені Операції:

```sql
❌ INSERT - додавання даних
❌ UPDATE - оновлення даних
❌ DELETE - видалення даних
❌ ALTER - зміна структури
❌ DROP - видалення таблиць
❌ CREATE - створення об'єктів
❌ TRUNCATE - очищення таблиць
```

---

## 📊 СТРУКТУРА ТАБЛИЦЬ (READ)

### 👥 `students` - Студенти

**Що читати:**
- Базова інформація про учня
- Контакти батьків
- Соціальні пільги
- На які гуртки записаний

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `first_name` | VARCHAR(100) | Ім'я |
| `last_name` | VARCHAR(100) | Прізвище |
| `age` | INTEGER | Вік (3-18) |
| `grade` | VARCHAR(20) | Клас ("5-А", "10") |
| `location` | VARCHAR(100) | Населений пункт |
| `father_name` | VARCHAR(200) | ПІБ батька |
| `mother_name` | VARCHAR(200) | ПІБ матері |
| `phone_father` | VARCHAR(20) | Телефон батька |
| `phone_mother` | VARCHAR(20) | Телефон матері |
| `phone_child` | VARCHAR(20) | Телефон дитини |
| `benefit_low_income` | BOOLEAN | Малозабезпечені |
| `benefit_large_family` | BOOLEAN | Багатодітна сім'я |
| `benefit_military_family` | BOOLEAN | Сім'я військового |
| `benefit_internally_displaced` | BOOLEAN | ВПО |
| `benefit_orphan` | BOOLEAN | Сирота |
| `benefit_disability` | BOOLEAN | Інвалідність |
| `benefit_social_risk` | BOOLEAN | Соціальний ризик |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати всіх студентів з Брусилова
SELECT 
    id,
    first_name,
    last_name,
    age,
    grade,
    phone_mother,
    phone_father
FROM students 
WHERE location = 'Брусилів'
ORDER BY last_name, first_name;
```

---

### 👨‍🏫 `teachers` - Вчителі

**Що читати:**
- Інформація про вчителя
- Telegram інтеграція
- Чи активний вчитель
- Які гуртки веде

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `full_name` | VARCHAR(200) | Повне ім'я |
| `email` | VARCHAR(100) | Email |
| `phone` | VARCHAR(20) | Телефон |
| `tg_chat_id` | BIGINT | Telegram Chat ID |
| `active` | BOOLEAN | Чи активний |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати всіх активних вчителів з Telegram
SELECT 
    id,
    full_name,
    email,
    phone,
    tg_chat_id
FROM teachers 
WHERE active = TRUE 
  AND tg_chat_id IS NOT NULL
ORDER BY full_name;
```

---

### 🎯 `clubs` - Гуртки

**Що читати:**
- Назва гуртка
- Опис
- Тривалість заняття

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `name` | VARCHAR(200) | Назва ("Танці", "Англійська") |
| `description` | TEXT | Опис гуртка |
| `duration_min` | INTEGER | Тривалість (хвилини) |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати всі гуртки з кількістю студентів
SELECT 
    c.id,
    c.name,
    c.description,
    c.duration_min,
    COUNT(DISTINCT e.student_id) as students_count
FROM clubs c
LEFT JOIN enrollments e ON c.id = e.club_id
GROUP BY c.id, c.name, c.description, c.duration_min
ORDER BY students_count DESC;
```

---

### 📅 `schedules` - Розклади

**Що читати:**
- Коли проходять заняття
- Який вчитель веде
- Який гурток
- Чи активний розклад

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `club_id` | INTEGER | ID гуртка |
| `teacher_id` | INTEGER | ID вчителя |
| `weekday` | INTEGER | День тижня (1=Пн, 7=Нд) |
| `start_time` | TIME | Час початку |
| `end_time` | TIME | Час закінчення |
| `group_name` | VARCHAR(100) | Назва групи |
| `active` | BOOLEAN | Чи активний |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати розклад на понеділок з інформацією про вчителя та гурток
SELECT 
    s.id,
    c.name as club_name,
    t.full_name as teacher_name,
    s.start_time,
    s.end_time,
    s.group_name,
    COUNT(DISTINCT se.student_id) as enrolled_students
FROM schedules s
JOIN clubs c ON s.club_id = c.id
JOIN teachers t ON s.teacher_id = t.id
LEFT JOIN schedule_enrollments se ON s.id = se.schedule_id
WHERE s.active = TRUE
  AND s.weekday = 1  -- Понеділок
GROUP BY s.id, c.name, t.full_name, s.start_time, s.end_time, s.group_name
ORDER BY s.start_time;
```

---

### 📝 `enrollments` - Записи на Гуртки

**Що читати:**
- Який студент на який гурток записаний
- Коли записався

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `student_id` | INTEGER | ID студента |
| `club_id` | INTEGER | ID гуртка |
| `enrolled_at` | TIMESTAMP | Дата запису |

**Приклад SELECT:**
```sql
-- Отримати всі гуртки конкретного студента
SELECT 
    s.first_name || ' ' || s.last_name as student_name,
    c.name as club_name,
    e.enrolled_at
FROM enrollments e
JOIN students s ON e.student_id = s.id
JOIN clubs c ON e.club_id = c.id
WHERE s.id = 123
ORDER BY e.enrolled_at DESC;
```

---

### 📅 `schedule_enrollments` - Записи на Розклади

**Що читати:**
- Який студент на який конкретний розклад записаний
- На яку групу ходить

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `student_id` | INTEGER | ID студента |
| `schedule_id` | INTEGER | ID розкладу |
| `enrolled_at` | TIMESTAMP | Дата запису |

**Приклад SELECT:**
```sql
-- Отримати список студентів конкретного розкладу
SELECT 
    s.id,
    s.first_name,
    s.last_name,
    s.phone_mother,
    se.enrolled_at
FROM schedule_enrollments se
JOIN students s ON se.student_id = s.id
WHERE se.schedule_id = 45
ORDER BY s.last_name, s.first_name;
```

---

### 📚 `lesson_events` - Події Уроків

**Що читати:**
- Заплановані та проведені уроки
- Статус уроку
- Коли відбувся/відбудеться

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `schedule_id` | INTEGER | ID розкладу (може бути NULL) |
| `teacher_id` | INTEGER | ID вчителя |
| `club_id` | INTEGER | ID гуртка |
| `date` | DATE | Дата уроку |
| `start_at` | TIMESTAMP | Час початку |
| `status` | ENUM | PLANNED, SENT, COMPLETED, SKIPPED, CANCELLED |
| `notify_at` | TIMESTAMP | Коли надіслати нотифікацію |
| `sent_at` | TIMESTAMP | Коли надіслано |
| `completed_at` | TIMESTAMP | Коли завершено |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати всі майбутні уроки вчителя
SELECT 
    le.id,
    c.name as club_name,
    le.date,
    le.start_at,
    le.status,
    COUNT(DISTINCT a.student_id) FILTER (WHERE a.status = 'PRESENT') as present_count
FROM lesson_events le
JOIN clubs c ON le.club_id = c.id
LEFT JOIN attendance a ON le.id = a.lesson_event_id
WHERE le.teacher_id = 5
  AND le.date >= CURRENT_DATE
  AND le.status IN ('PLANNED', 'SENT')
GROUP BY le.id, c.name, le.date, le.start_at, le.status
ORDER BY le.date, le.start_at;
```

---

### ✅ `attendance` - Відвідуваність

**Що читати:**
- Хто був присутній на уроці
- Хто був відсутній
- Хто відмітив присутність

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `lesson_event_id` | INTEGER | ID уроку |
| `student_id` | INTEGER | ID студента |
| `status` | ENUM | PRESENT, ABSENT |
| `marked_by` | BIGINT | Telegram Chat ID того, хто відмітив |
| `marked_at` | TIMESTAMP | Коли відмітили |

**Приклад SELECT:**
```sql
-- Отримати відвідуваність студента за місяць
SELECT 
    le.date,
    c.name as club_name,
    a.status,
    CASE 
        WHEN a.status = 'PRESENT' THEN '✅ Присутній'
        WHEN a.status = 'ABSENT' THEN '❌ Відсутній'
    END as status_text
FROM attendance a
JOIN lesson_events le ON a.lesson_event_id = le.id
JOIN clubs c ON le.club_id = c.id
WHERE a.student_id = 123
  AND le.date >= DATE_TRUNC('month', CURRENT_DATE)
ORDER BY le.date DESC;
```

---

### 📋 `conducted_lessons` - Проведені Уроки

**Що читати:**
- Підсумки проведених уроків
- Статистика відвідуваності
- Чи нараховано зарплату

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `teacher_id` | INTEGER | ID вчителя |
| `club_id` | INTEGER | ID гуртка |
| `lesson_event_id` | INTEGER | ID події уроку |
| `lesson_date` | TIMESTAMP | Дата проведення |
| `lesson_duration_minutes` | INTEGER | Тривалість |
| `total_students` | INTEGER | Загальна кількість |
| `present_students` | INTEGER | Присутні |
| `absent_students` | INTEGER | Відсутні |
| `attendance_rate` | DECIMAL | Відсоток відвідуваності (auto) |
| `notes` | TEXT | Нотатки вчителя |
| `lesson_topic` | VARCHAR(500) | Тема уроку |
| `is_salary_calculated` | BOOLEAN | Чи нараховано зарплату |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати статистику проведених уроків за тиждень
SELECT 
    c.name as club_name,
    t.full_name as teacher_name,
    cl.lesson_date::date,
    cl.total_students,
    cl.present_students,
    cl.absent_students,
    cl.attendance_rate,
    cl.notes
FROM conducted_lessons cl
JOIN clubs c ON cl.club_id = c.id
JOIN teachers t ON cl.teacher_id = t.id
WHERE cl.lesson_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY cl.lesson_date DESC;
```

---

### 💰 `pay_rates` - Тарифи

**Що читати:**
- Скільки отримує вчитель за урок
- Діючі тарифи
- Історія змін тарифів

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `teacher_id` | INTEGER | ID вчителя |
| `rate_per_lesson` | DECIMAL(10,2) | Ставка за урок |
| `effective_from` | DATE | Діє з дати |
| `effective_to` | DATE | Діє до дати (NULL = досі) |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати діючі тарифи всіх вчителів
SELECT 
    t.full_name,
    pr.rate_per_lesson,
    pr.effective_from,
    pr.effective_to
FROM pay_rates pr
JOIN teachers t ON pr.teacher_id = t.id
WHERE pr.effective_from <= CURRENT_DATE
  AND (pr.effective_to IS NULL OR pr.effective_to >= CURRENT_DATE)
ORDER BY t.full_name;
```

---

### 💵 `payroll` - Зарплати

**Що читати:**
- Нараховані зарплати
- Статус виплат
- Суми за період

**Основні поля:**

| Поле | Тип | Опис |
|------|-----|------|
| `id` | INTEGER | Унікальний ID |
| `teacher_id` | INTEGER | ID вчителя |
| `lesson_event_id` | INTEGER | ID події уроку |
| `amount_decimal` | DECIMAL(10,2) | Сума |
| `basis` | ENUM | PER_LESSON, FIXED, MANUAL |
| `status` | VARCHAR(20) | CALCULATED, APPROVED, PAID |
| `period_start` | DATE | Початок періоду |
| `period_end` | DATE | Кінець періоду |
| `notes` | TEXT | Примітки |
| `created_at` | TIMESTAMP | Дата створення |

**Приклад SELECT:**
```sql
-- Отримати зарплати вчителів за місяць
SELECT 
    t.full_name,
    COUNT(p.id) as payments_count,
    SUM(p.amount_decimal) as total_amount,
    p.status
FROM payroll p
JOIN teachers t ON p.teacher_id = t.id
WHERE DATE_TRUNC('month', p.created_at) = DATE_TRUNC('month', CURRENT_DATE)
GROUP BY t.id, t.full_name, p.status
ORDER BY total_amount DESC;
```

---

## 📊 ГОТОВІ SELECT ЗАПИТИ

### 1. Список Студентів з Їх Гуртками

```sql
SELECT 
    s.id as student_id,
    s.first_name || ' ' || s.last_name as student_name,
    s.age,
    s.grade,
    s.location,
    s.phone_mother,
    STRING_AGG(DISTINCT c.name, ', ') as clubs,
    COUNT(DISTINCT e.club_id) as clubs_count
FROM students s
LEFT JOIN enrollments e ON s.id = e.student_id
LEFT JOIN clubs c ON e.club_id = c.id
GROUP BY s.id, s.first_name, s.last_name, s.age, s.grade, s.location, s.phone_mother
ORDER BY s.last_name, s.first_name;
```

---

### 2. Розклад на Сьогодні

```sql
SELECT 
    s.start_time,
    s.end_time,
    c.name as club_name,
    t.full_name as teacher_name,
    s.group_name,
    COUNT(DISTINCT se.student_id) as students_enrolled,
    EXTRACT(DOW FROM CURRENT_DATE) as today_weekday
FROM schedules s
JOIN clubs c ON s.club_id = c.id
JOIN teachers t ON s.teacher_id = t.id
LEFT JOIN schedule_enrollments se ON s.id = se.schedule_id
WHERE s.active = TRUE
  AND s.weekday = EXTRACT(DOW FROM CURRENT_DATE)
GROUP BY s.id, s.start_time, s.end_time, c.name, t.full_name, s.group_name
ORDER BY s.start_time;
```

---

### 3. Відвідуваність Студента (Детально)

```sql
SELECT 
    le.date,
    c.name as club_name,
    t.full_name as teacher_name,
    CASE 
        WHEN a.status = 'PRESENT' THEN '✅ Присутній'
        WHEN a.status = 'ABSENT' THEN '❌ Відсутній'
        ELSE '⚠️ Не відмічено'
    END as attendance_status,
    cl.notes as teacher_notes
FROM lesson_events le
JOIN clubs c ON le.club_id = c.id
JOIN teachers t ON le.teacher_id = t.id
LEFT JOIN attendance a ON le.id = a.lesson_event_id AND a.student_id = :student_id
LEFT JOIN conducted_lessons cl ON le.id = cl.lesson_event_id
WHERE le.status = 'COMPLETED'
  AND le.date >= CURRENT_DATE - INTERVAL '30 days'
  AND EXISTS (
      SELECT 1 FROM schedule_enrollments se
      WHERE se.student_id = :student_id
        AND se.schedule_id = le.schedule_id
  )
ORDER BY le.date DESC;
```

---

### 4. Топ-10 Студентів за Відвідуваністю

```sql
SELECT 
    s.id,
    s.first_name || ' ' || s.last_name as student_name,
    s.grade,
    COUNT(a.id) as total_lessons,
    COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END) as present_count,
    COUNT(CASE WHEN a.status = 'ABSENT' THEN 1 END) as absent_count,
    ROUND(
        COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END)::decimal / 
        NULLIF(COUNT(a.id), 0) * 100,
        2
    ) as attendance_percent
FROM students s
JOIN attendance a ON s.id = a.student_id
JOIN lesson_events le ON a.lesson_event_id = le.id
WHERE le.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY s.id, s.first_name, s.last_name, s.grade
HAVING COUNT(a.id) >= 5  -- Мінімум 5 уроків
ORDER BY attendance_percent DESC
LIMIT 10;
```

---

### 5. Статистика Гуртків за Місяць

```sql
SELECT 
    c.id,
    c.name as club_name,
    COUNT(DISTINCT e.student_id) as total_enrolled,
    COUNT(DISTINCT cl.id) as lessons_conducted,
    SUM(cl.present_students) as total_present,
    SUM(cl.total_students) as total_expected,
    ROUND(
        SUM(cl.present_students)::decimal / 
        NULLIF(SUM(cl.total_students), 0) * 100,
        2
    ) as avg_attendance_rate,
    COUNT(DISTINCT cl.teacher_id) as teachers_count
FROM clubs c
LEFT JOIN enrollments e ON c.id = e.club_id
LEFT JOIN conducted_lessons cl ON c.id = cl.club_id
    AND cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY c.id, c.name
ORDER BY lessons_conducted DESC;
```

---

### 6. Студенти з Пільгами

```sql
SELECT 
    s.id,
    s.first_name || ' ' || s.last_name as student_name,
    s.age,
    s.grade,
    s.location,
    CASE 
        WHEN s.benefit_low_income THEN 'Малозабезпечені'
        WHEN s.benefit_large_family THEN 'Багатодітна сім''я'
        WHEN s.benefit_military_family THEN 'Сім''я військового'
        WHEN s.benefit_internally_displaced THEN 'ВПО'
        WHEN s.benefit_orphan THEN 'Сирота'
        WHEN s.benefit_disability THEN 'Інвалідність'
        WHEN s.benefit_social_risk THEN 'Соціальний ризик'
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
GROUP BY s.id, s.first_name, s.last_name, s.age, s.grade, s.location,
         s.benefit_low_income, s.benefit_large_family, s.benefit_military_family,
         s.benefit_internally_displaced, s.benefit_orphan, s.benefit_disability,
         s.benefit_social_risk
ORDER BY s.last_name, s.first_name;
```

---

### 7. Навантаження Вчителів

```sql
SELECT 
    t.id,
    t.full_name,
    t.email,
    t.phone,
    COUNT(DISTINCT s.id) as schedules_count,
    COUNT(DISTINCT cl.id) FILTER (
        WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
    ) as lessons_this_month,
    SUM(cl.present_students) FILTER (
        WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
    ) as students_taught_this_month,
    ROUND(AVG(cl.attendance_rate) FILTER (
        WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
    ), 2) as avg_attendance_rate,
    COUNT(DISTINCT le.id) FILTER (
        WHERE le.status IN ('PLANNED', 'SENT') AND le.date >= CURRENT_DATE
    ) as upcoming_lessons
FROM teachers t
LEFT JOIN schedules s ON t.id = s.teacher_id AND s.active = TRUE
LEFT JOIN lesson_events le ON t.id = le.teacher_id
LEFT JOIN conducted_lessons cl ON t.id = cl.teacher_id
WHERE t.active = TRUE
GROUP BY t.id, t.full_name, t.email, t.phone
ORDER BY lessons_this_month DESC NULLS LAST;
```

---

### 8. Фінансовий Звіт (Зарплати за Період)

```sql
SELECT 
    t.full_name as teacher_name,
    COUNT(DISTINCT p.id) as payments_count,
    COUNT(DISTINCT cl.id) as lessons_count,
    SUM(cl.present_students) as total_students_taught,
    SUM(p.amount_decimal) as total_earned,
    ROUND(AVG(p.amount_decimal), 2) as avg_per_payment,
    STRING_AGG(DISTINCT p.status, ', ') as payment_statuses
FROM teachers t
JOIN payroll p ON t.id = p.teacher_id
LEFT JOIN conducted_lessons cl ON p.lesson_event_id = cl.lesson_event_id
WHERE p.created_at >= :start_date
  AND p.created_at < :end_date
GROUP BY t.id, t.full_name
ORDER BY total_earned DESC NULLS LAST;
```

---

## 📈 ТИПОВІ ЗВІТИ

### Звіт 1: Щоденний Звіт Відвідуваності

```sql
WITH daily_stats AS (
    SELECT 
        cl.lesson_date::date as date,
        COUNT(DISTINCT cl.id) as lessons_conducted,
        SUM(cl.total_students) as expected_students,
        SUM(cl.present_students) as present_students,
        SUM(cl.absent_students) as absent_students,
        ROUND(
            SUM(cl.present_students)::decimal / 
            NULLIF(SUM(cl.total_students), 0) * 100,
            2
        ) as attendance_rate
    FROM conducted_lessons cl
    WHERE cl.lesson_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY cl.lesson_date::date
)
SELECT 
    date,
    lessons_conducted,
    expected_students,
    present_students,
    absent_students,
    attendance_rate || '%' as attendance_rate
FROM daily_stats
ORDER BY date DESC;
```

---

### Звіт 2: Студенти з Низькою Відвідуваністю

```sql
SELECT 
    s.id,
    s.first_name || ' ' || s.last_name as student_name,
    s.grade,
    s.phone_mother,
    s.phone_father,
    STRING_AGG(DISTINCT c.name, ', ') as clubs,
    COUNT(a.id) as total_lessons,
    COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END) as present_count,
    ROUND(
        COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END)::decimal / 
        NULLIF(COUNT(a.id), 0) * 100,
        2
    ) as attendance_percent
FROM students s
JOIN attendance a ON s.id = a.student_id
JOIN lesson_events le ON a.lesson_event_id = le.id
JOIN clubs c ON le.club_id = c.id
WHERE le.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY s.id, s.first_name, s.last_name, s.grade, s.phone_mother, s.phone_father
HAVING COUNT(a.id) >= 5  -- Мінімум 5 уроків
  AND COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END)::decimal / 
      NULLIF(COUNT(a.id), 0) * 100 < 70  -- Менше 70%
ORDER BY attendance_percent ASC;
```

---

### Звіт 3: Найпопулярніші Гуртки

```sql
SELECT 
    c.id,
    c.name as club_name,
    c.description,
    COUNT(DISTINCT e.student_id) as students_enrolled,
    COUNT(DISTINCT s.id) as schedules_count,
    COUNT(DISTINCT cl.id) FILTER (
        WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
    ) as lessons_this_month,
    ROUND(AVG(cl.attendance_rate) FILTER (
        WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
    ), 2) as avg_attendance_rate,
    ARRAY_AGG(DISTINCT t.full_name) as teachers
FROM clubs c
LEFT JOIN enrollments e ON c.id = e.club_id
LEFT JOIN schedules s ON c.id = s.club_id AND s.active = TRUE
LEFT JOIN teachers t ON s.teacher_id = t.id
LEFT JOIN conducted_lessons cl ON c.id = cl.club_id
GROUP BY c.id, c.name, c.description
ORDER BY students_enrolled DESC;
```

---

### Звіт 4: Статистика по Населених Пунктах

```sql
SELECT 
    s.location,
    COUNT(DISTINCT s.id) as students_count,
    COUNT(DISTINCT e.club_id) as unique_clubs,
    ROUND(AVG(s.age), 1) as avg_age,
    COUNT(CASE WHEN s.benefit_low_income THEN 1 END) as with_benefits,
    COUNT(DISTINCT a.lesson_event_id) as total_lessons_attended,
    ROUND(
        COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END)::decimal /
        NULLIF(COUNT(a.id), 0) * 100,
        2
    ) as avg_attendance_percent
FROM students s
LEFT JOIN enrollments e ON s.id = e.student_id
LEFT JOIN attendance a ON s.id = a.student_id
    AND a.marked_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY s.location
ORDER BY students_count DESC;
```

---

## 🎯 АНАЛІТИКА ТА СТАТИСТИКА

### Аналітика 1: Тренд Відвідуваності (по тижнях)

```sql
SELECT 
    DATE_TRUNC('week', cl.lesson_date)::date as week_start,
    COUNT(DISTINCT cl.id) as lessons_count,
    SUM(cl.present_students) as total_present,
    SUM(cl.total_students) as total_expected,
    ROUND(
        SUM(cl.present_students)::decimal / 
        NULLIF(SUM(cl.total_students), 0) * 100,
        2
    ) as attendance_rate
FROM conducted_lessons cl
WHERE cl.lesson_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE_TRUNC('week', cl.lesson_date)
ORDER BY week_start DESC;
```

---

### Аналітика 2: Розподіл Студентів за Віком

```sql
SELECT 
    CASE 
        WHEN age BETWEEN 3 AND 6 THEN '3-6 років (дошкільники)'
        WHEN age BETWEEN 7 AND 10 THEN '7-10 років (молодші класи)'
        WHEN age BETWEEN 11 AND 14 THEN '11-14 років (середні класи)'
        WHEN age BETWEEN 15 AND 18 THEN '15-18 років (старші класи)'
        ELSE 'Невказано'
    END as age_group,
    COUNT(*) as students_count,
    ROUND(COUNT(*)::decimal / (SELECT COUNT(*) FROM students) * 100, 2) as percentage,
    STRING_AGG(DISTINCT c.name, ', ') as popular_clubs
FROM students s
LEFT JOIN enrollments e ON s.id = e.student_id
LEFT JOIN clubs c ON e.club_id = c.id
GROUP BY age_group
ORDER BY 
    CASE age_group
        WHEN '3-6 років (дошкільники)' THEN 1
        WHEN '7-10 років (молодші класи)' THEN 2
        WHEN '11-14 років (середні класи)' THEN 3
        WHEN '15-18 років (старші класи)' THEN 4
        ELSE 5
    END;
```

---

### Аналітика 3: Ефективність Вчителів

```sql
SELECT 
    t.full_name as teacher_name,
    COUNT(DISTINCT c.id) as clubs_taught,
    COUNT(DISTINCT cl.id) as lessons_conducted,
    AVG(cl.attendance_rate) as avg_attendance_rate,
    AVG(cl.present_students) as avg_students_per_lesson,
    COUNT(DISTINCT cl.id) FILTER (
        WHERE cl.attendance_rate >= 80
    ) as high_attendance_lessons,
    COUNT(DISTINCT cl.id) FILTER (
        WHERE cl.attendance_rate < 60
    ) as low_attendance_lessons
FROM teachers t
LEFT JOIN conducted_lessons cl ON t.id = cl.teacher_id
    AND cl.lesson_date >= CURRENT_DATE - INTERVAL '90 days'
LEFT JOIN clubs c ON cl.club_id = c.id
WHERE t.active = TRUE
GROUP BY t.id, t.full_name
HAVING COUNT(DISTINCT cl.id) >= 5  -- Мінімум 5 уроків
ORDER BY avg_attendance_rate DESC;
```

---

## 🔗 КОРИСНІ JOIN PATTERNS

### Pattern 1: Студент → Гуртки → Розклади → Уроки

```sql
SELECT 
    s.first_name || ' ' || s.last_name as student,
    c.name as club,
    sch.weekday,
    sch.start_time,
    t.full_name as teacher,
    COUNT(le.id) as total_lessons,
    COUNT(a.id) FILTER (WHERE a.status = 'PRESENT') as attended
FROM students s
JOIN enrollments e ON s.id = e.student_id
JOIN clubs c ON e.club_id = c.id
JOIN schedules sch ON c.id = sch.club_id AND sch.active = TRUE
JOIN teachers t ON sch.teacher_id = t.id
LEFT JOIN lesson_events le ON sch.id = le.schedule_id
LEFT JOIN attendance a ON le.id = a.lesson_event_id AND a.student_id = s.id
WHERE s.id = :student_id
GROUP BY s.first_name, s.last_name, c.name, sch.weekday, sch.start_time, t.full_name
ORDER BY sch.weekday, sch.start_time;
```

---

### Pattern 2: Гурток → Всі Пов'язані Дані

```sql
SELECT 
    c.id,
    c.name,
    COUNT(DISTINCT e.student_id) as enrolled_students,
    COUNT(DISTINCT sch.id) as schedules_count,
    COUNT(DISTINCT t.id) as teachers_count,
    COUNT(DISTINCT le.id) as total_lesson_events,
    COUNT(DISTINCT cl.id) as conducted_lessons,
    ROUND(AVG(cl.attendance_rate), 2) as avg_attendance
FROM clubs c
LEFT JOIN enrollments e ON c.id = e.club_id
LEFT JOIN schedules sch ON c.id = sch.club_id
LEFT JOIN teachers t ON sch.teacher_id = t.id
LEFT JOIN lesson_events le ON c.id = le.club_id
LEFT JOIN conducted_lessons cl ON c.id = cl.club_id
WHERE c.id = :club_id
GROUP BY c.id, c.name;
```

---

## 🎨 ФІЛЬТРАЦІЯ ДАНИХ

### Фільтр 1: За Датою

```sql
-- За конкретний день
WHERE cl.lesson_date::date = '2025-10-02'

-- За останній тиждень
WHERE cl.lesson_date >= CURRENT_DATE - INTERVAL '7 days'

-- За поточний місяць
WHERE cl.lesson_date >= DATE_TRUNC('month', CURRENT_DATE)
  AND cl.lesson_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'

-- За період
WHERE cl.lesson_date BETWEEN :start_date AND :end_date
```

---

### Фільтр 2: За Відвідуваністю

```sql
-- Висока відвідуваність (>=80%)
WHERE cl.attendance_rate >= 80

-- Низька відвідуваність (<70%)
WHERE cl.attendance_rate < 70

-- Середня відвідуваність
WHERE cl.attendance_rate BETWEEN 70 AND 79.99
```

---

### Фільтр 3: За Статусом

```sql
-- Тільки завершені уроки
WHERE le.status = 'COMPLETED'

-- Майбутні уроки
WHERE le.status IN ('PLANNED', 'SENT')
  AND le.date >= CURRENT_DATE

-- Скасовані уроки
WHERE le.status IN ('SKIPPED', 'CANCELLED')
```

---

### Фільтр 4: За Пільгами

```sql
-- Студенти з будь-якою пільгою
WHERE (
    s.benefit_low_income = TRUE OR
    s.benefit_large_family = TRUE OR
    s.benefit_military_family = TRUE OR
    s.benefit_internally_displaced = TRUE OR
    s.benefit_orphan = TRUE OR
    s.benefit_disability = TRUE OR
    s.benefit_social_risk = TRUE
)

-- Тільки ВПО
WHERE s.benefit_internally_displaced = TRUE

-- Без пільг
WHERE s.benefit_low_income = FALSE
  AND s.benefit_large_family = FALSE
  AND s.benefit_military_family = FALSE
  AND s.benefit_internally_displaced = FALSE
  AND s.benefit_orphan = FALSE
  AND s.benefit_disability = FALSE
  AND s.benefit_social_risk = FALSE
```

---

## ⚡ ОПТИМІЗАЦІЯ ЧИТАННЯ

### Правило 1: Завжди Використовуйте LIMIT

```sql
-- ✅ ДОБРЕ - обмежуємо кількість
SELECT * FROM students LIMIT 100;

-- ❌ ПОГАНО - може повернути тисячі рядків
SELECT * FROM students;
```

---

### Правило 2: Фільтруйте Рано (WHERE перед JOIN)

```sql
-- ✅ ДОБРЕ - фільтруємо перед JOIN
SELECT s.*, c.name
FROM students s
JOIN enrollments e ON s.id = e.student_id
JOIN clubs c ON e.club_id = c.id
WHERE s.location = 'Брусилів';  -- Фільтр застосується рано

-- ❌ ПОГАНО - JOIN всіх, потім фільтруємо
SELECT s.*, c.name
FROM students s
JOIN enrollments e ON s.id = e.student_id
JOIN clubs c ON e.club_id = c.id
WHERE c.name = 'Танці';  -- Краще винести в підзапит
```

---

### Правило 3: Використовуйте Індекси

```sql
-- ✅ ДОБРЕ - використовуємо індекси
WHERE s.location = 'Брусилів'  -- Є індекс на location
WHERE t.active = TRUE           -- Є індекс на active
WHERE le.date >= '2025-01-01'   -- Є індекс на date

-- ❌ ПОГАНО - ламаємо індекси
WHERE LOWER(s.first_name) LIKE '%марія%'  -- Функція + LIKE
WHERE s.age + 5 > 15                       -- Функція на колонці
```

---

### Правило 4: EXISTS замість COUNT

```sql
-- ✅ ДОБРЕ - зупиняється на першому знайденому
WHERE EXISTS (
    SELECT 1 FROM enrollments 
    WHERE student_id = s.id
)

-- ❌ ПОГАНО - рахує всі рядки
WHERE (SELECT COUNT(*) FROM enrollments WHERE student_id = s.id) > 0
```

---

### Правило 5: Уникайте SELECT *

```sql
-- ✅ ДОБРЕ - вибираємо тільки потрібні поля
SELECT s.id, s.first_name, s.last_name, s.age
FROM students s;

-- ❌ ПОГАНО - вибираємо всі поля (може бути багато даних)
SELECT * FROM students;
```

---

## 🎓 КОРИСНІ ФУНКЦІЇ

### Функції Дати

```sql
-- Поточна дата
CURRENT_DATE

-- Поточний час
CURRENT_TIMESTAMP

-- Початок місяця
DATE_TRUNC('month', CURRENT_DATE)

-- Початок тижня
DATE_TRUNC('week', CURRENT_DATE)

-- День тижня (1=Пн, 7=Нд)
EXTRACT(DOW FROM date_field)

-- Різниця днів
date_field - INTERVAL '7 days'
```

---

### Функції Агрегації

```sql
-- Кількість
COUNT(*)
COUNT(DISTINCT field)

-- Сума
SUM(amount)

-- Середнє
AVG(attendance_rate)

-- Мінімум/Максимум
MIN(date), MAX(date)

-- Об'єднання в рядок
STRING_AGG(name, ', ')
```

---

### Умовна Логіка

```sql
-- CASE WHEN
CASE 
    WHEN age BETWEEN 3 AND 6 THEN 'Дошкільник'
    WHEN age BETWEEN 7 AND 10 THEN 'Молодший'
    ELSE 'Старший'
END

-- COALESCE (перше не-NULL значення)
COALESCE(phone_mother, phone_father, 'Немає телефону')

-- NULLIF (NULL якщо рівні)
attendance_rate / NULLIF(total_students, 0)
```

---

## 📝 ПРИКЛАДИ ВИКОРИСТАННЯ

### Приклад 1: Генерація Списку для Нотифікації

```sql
-- Отримати батьків студентів, які пропустили більше 3 уроків підряд
WITH recent_absences AS (
    SELECT 
        a.student_id,
        COUNT(*) as consecutive_absences
    FROM attendance a
    JOIN lesson_events le ON a.lesson_event_id = le.id
    WHERE a.status = 'ABSENT'
      AND le.date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY a.student_id
)
SELECT 
    s.first_name || ' ' || s.last_name as student_name,
    s.phone_mother,
    s.phone_father,
    ra.consecutive_absences,
    STRING_AGG(DISTINCT c.name, ', ') as missed_clubs
FROM recent_absences ra
JOIN students s ON ra.student_id = s.id
JOIN attendance a ON s.id = a.student_id AND a.status = 'ABSENT'
JOIN lesson_events le ON a.lesson_event_id = le.id AND le.date >= CURRENT_DATE - INTERVAL '7 days'
JOIN clubs c ON le.club_id = c.id
WHERE ra.consecutive_absences >= 3
GROUP BY s.id, s.first_name, s.last_name, s.phone_mother, s.phone_father, ra.consecutive_absences;
```

---

### Приклад 2: Дані для Діаграм (Dashboard)

```sql
-- Відвідуваність по днях тижня
SELECT 
    CASE EXTRACT(DOW FROM le.date)
        WHEN 1 THEN 'Понеділок'
        WHEN 2 THEN 'Вівторок'
        WHEN 3 THEN 'Середа'
        WHEN 4 THEN 'Четвер'
        WHEN 5 THEN 'П''ятниця'
        WHEN 6 THEN 'Субота'
        WHEN 0 THEN 'Неділя'
    END as weekday,
    COUNT(DISTINCT le.id) as lessons_count,
    ROUND(AVG(cl.attendance_rate), 2) as avg_attendance
FROM lesson_events le
JOIN conducted_lessons cl ON le.id = cl.lesson_event_id
WHERE le.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY EXTRACT(DOW FROM le.date)
ORDER BY EXTRACT(DOW FROM le.date);
```

---

## 🎯 ПІДСУМОК ДЛЯ AI

### ✅ Що ви МОЖЕТЕ:

1. **SELECT** - читати будь-які дані
2. **JOIN** - поєднувати таблиці
3. **Агрегація** - рахувати статистику
4. **Фільтрація** - WHERE, HAVING
5. **Групування** - GROUP BY
6. **Сортування** - ORDER BY
7. **CTE** - WITH запити для складної логіки

### ❌ Що ви НЕ МОЖЕТЕ:

1. Змінювати дані (UPDATE)
2. Додавати дані (INSERT)
3. Видаляти дані (DELETE)
4. Змінювати структуру (ALTER, DROP, CREATE)

### 🎓 Поради:

- Завжди використовуйте LIMIT для великих таблиць
- Фільтруйте по датах для продуктивності
- Використовуйте індексовані поля в WHERE
- Вибирайте тільки потрібні колонки
- Перевіряйте що таблиці не порожні (LEFT JOIN)

---

**📞 Цей документ створений спеціально для READ-ONLY AI агентів**  
**🤖 Використовуйте для аналітики, звітів та статистики**  
**📅 Останнє оновлення:** Жовтень 2025

