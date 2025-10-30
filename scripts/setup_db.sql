-- Створення розширень
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Встановлення локалі
SET lc_messages TO 'uk_UA.UTF-8';
SET lc_monetary TO 'uk_UA.UTF-8';
SET lc_numeric TO 'uk_UA.UTF-8';
SET lc_time TO 'uk_UA.UTF-8';

-- Створення схеми якщо не існує
CREATE SCHEMA IF NOT EXISTS public;

-- Налаштування доступів
GRANT ALL PRIVILEGES ON DATABASE school_db TO school_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO school_user;