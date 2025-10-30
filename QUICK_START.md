# ⚡ Швидкий Старт - Локальний Додаток

## 🚀 **ЗАПУСК**

```bash
./start_local.sh
```

## 🛑 **ЗУПИНКА**

```bash
./stop_local.sh
```

---

## 🌐 **ДОСТУП**

- 🌐 **Адмін-панель:** http://localhost:8000/admin/
- 📚 **API Docs:** http://localhost:8000/docs  
- ❤️ **Health:** http://localhost:8000/health

**Логін:**
- Email: `admin@school.local`
- Пароль: `admin123`

---

## 📊 **ПЕРЕГЛЯД ЛОГІВ**

```bash
# Всі логи
docker compose -f docker-compose.local.yml logs -f

# Тільки webapp
docker compose -f docker-compose.local.yml logs -f webapp

# Тільки Telegram бот
docker compose -f docker-compose.local.yml logs -f dispatcher
```

---

## 🔍 **СТАТУС**

```bash
docker ps
```

Має бути **3 контейнери**:
- ✅ `school-db` (база даних)
- ✅ `new---webapp-1` (веб-додаток)
- ✅ `new---dispatcher-1` (Telegram бот)

---

## ⚠️ **ВАЖЛИВО**

- ✅ База даних `school-db` **НЕ** зупиняється коли зупиняєш додаток
- ✅ Додаток підключається до **ІСНУЮЧОЇ** бази даних
- ✅ **НІЯКИХ ЗМІН** в базі даних не робиться при запуску/зупинці

---

## 🔄 **ПЕРЕЗАПУСК**

```bash
./stop_local.sh && ./start_local.sh
```

---

## 📚 **ДЕТАЛЬНА ІНСТРУКЦІЯ**

Дивись файл `LOCAL_SETUP_README.md`


