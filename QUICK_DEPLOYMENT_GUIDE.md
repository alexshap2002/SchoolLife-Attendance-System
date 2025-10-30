# ⚡ ШВИДКИЙ ГАЙД: DEPLOYMENT

## 🚀 **АВТОМАТИЧНИЙ СПОСІБ (2 команди)**

### **1. На локальному комп'ютері:**
```bash
cd /Users/oleksandrsapovalov/Робота/додаток\ ШЖ/new--
./copy_files_to_server.sh
```

### **2. На сервері:**
```bash
ssh root@185.233.39.11
cd /root/school-life-app
./deploy_to_production.sh
```

**Готово!** Скрипт зробить все автоматично.

---

## 📋 **ЩО БУДЕ ЗРОБЛЕНО:**

1. ✅ BACKUP БД автоматично
2. ✅ 5 індексів додано
3. ✅ 4 constraints додано
4. ✅ Старі події почищено
5. ✅ Код оновлено
6. ✅ Контейнери перезапущено

---

## 🔙 **ROLLBACK (1 команда)**

```bash
# На сервері
docker compose -f docker-compose.server.yml down
docker exec -i school-db psql -U school_user -d school_db < backup_before_optimization_*.sql
docker compose -f docker-compose.server.yml up -d
```

---

## 📊 **ПЕРЕВІРКА РЕЗУЛЬТАТУ**

```bash
# Статус
docker compose -f docker-compose.server.yml ps

# Логи
docker compose -f docker-compose.server.yml logs -f

# Індекси
docker exec school-db psql -U school_user -d school_db -c "
SELECT indexname FROM pg_indexes WHERE indexname LIKE 'idx_%';"
```

---

**Детальна інструкція:** `DEPLOYMENT_INSTRUCTIONS.md`

