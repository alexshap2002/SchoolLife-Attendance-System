# 🔒 БЕЗПЕКА ПРОЕКТУ

## ⚠️ ВАЖЛИВО ПЕРЕД РОЗГОРТАННЯМ!

Цей проект містить чутливі дані які **НІКОЛИ** не повинні потрапити в публічний доступ.

---

## 🚨 ЩО ТРЕБА ЗРОБИТИ:

### 1️⃣ **Створи `.env` файл (НЕ commitь його в git!)**

```bash
cp env.example .env
```

### 2️⃣ **Заміни всі placeholder значення:**

```bash
# У файлі .env заміни:
POSTGRES_PASSWORD=your_secure_password          # Придумай складний пароль
SECRET_KEY=your_very_long_random_secret_key     # Використай: openssl rand -hex 32
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather # Отримай від @BotFather в Telegram
ADMIN_PASSWORD=change_me_on_first_login         # Зміни на першому вході!
```

### 3️⃣ **Створи файл з Google credentials:**

```bash
# Помісти свій service_account.json в:
creds/service_account.json
```

---

## ❌ **НІКОЛИ НЕ РОБИ:**

1. ❌ Не commit `.env`, `.env.production`, `.env.local` файли
2. ❌ Не commit файли в `creds/` (крім `.gitkeep`)
3. ❌ Не commit файли з паролями, токенами, IP адресами
4. ❌ Не публікуй логи які можуть містити чутливі дані
5. ❌ Не зберігай паролі в коді або коментарях

---

## ✅ **ПЕРЕВІР ПЕРЕД COMMIT:**

```bash
# Перевір що ці файли НЕ в git:
git status | grep -E '\.env|creds/.*\.json|password|secret'

# Якщо знайшов щось - видали:
git rm --cached файл_з_секретом
```

---

## 🔐 **РЕКОМЕНДАЦІЇ:**

1. **Використовуй `.env.example`** як шаблон (без реальних даних)
2. **Генеруй складні паролі:** `openssl rand -base64 32`
3. **Генеруй SECRET_KEY:** `openssl rand -hex 32`
4. **Ротуй токени** після витоку
5. **Використовуй різні паролі** для dev/prod

---

## 🆘 **ЯКЩО ДАНІ ВИТЕКЛИ:**

1. 🔄 **Миттєво зміни всі паролі** та токени
2. 🤖 **Revoke Telegram Bot Token** через @BotFather
3. 🔑 **Згенеруй новий SECRET_KEY**
4. 🗄️ **Зміни паролі БД**
5. 📜 **Очисти git історію:** `git filter-branch` або `BFG Repo-Cleaner`

---

**Безпека - це не опція, це необхідність!** 🛡️

