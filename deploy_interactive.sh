#!/usr/bin/expect -f
# Інтерактивний deployment скрипт

set timeout 60
set server "185.233.39.11"
set user "root"
set password "brCg3DMh15mXf4Z7PsR"

# КРОК 1: Копіювання файлів
puts "📤 КРОК 1: Копіюю файли на сервер...\n"

# SQL файл
spawn scp database_optimizations.sql $user@$server:/root/school-life-app/
expect {
    "password:" { send "$password\r" }
    "yes/no" { send "yes\r"; exp_continue }
}
expect eof

# lesson_event_manager.py
spawn scp app/services/lesson_event_manager.py $user@$server:/root/school-life-app/app/services/
expect {
    "password:" { send "$password\r" }
    "yes/no" { send "yes\r"; exp_continue }
}
expect eof

# dispatcher.py
spawn scp app/workers/dispatcher.py $user@$server:/root/school-life-app/app/workers/
expect {
    "password:" { send "$password\r" }
    "yes/no" { send "yes\r"; exp_continue }
}
expect eof

# run_manual_cleanup.py
spawn scp run_manual_cleanup.py $user@$server:/root/school-life-app/
expect {
    "password:" { send "$password\r" }
    "yes/no" { send "yes\r"; exp_continue }
}
expect eof

puts "\n✅ Файли скопійовано!\n"

# КРОК 2: Виконання на сервері
puts "🚀 КРОК 2: Підключаюсь до сервера для deployment...\n"

spawn ssh $user@$server
expect {
    "password:" { send "$password\r" }
    "yes/no" { send "yes\r"; exp_continue }
}

expect "#"
send "cd /root/school-life-app\r"
expect "#"

# Backup БД
puts "\n📦 Створюю BACKUP бази даних...\n"
send "docker exec school-db pg_dump -U school_user -d school_db > backup_before_optimization_\$(date +%Y%m%d_%H%M%S).sql\r"
expect "#"
send "ls -lh backup_before_optimization_*.sql | tail -1\r"
expect "#"

# SQL оптимізації
puts "\n🗄️  Застосовую SQL оптимізації...\n"
send "docker cp database_optimizations.sql school-db:/tmp/db_opt.sql\r"
expect "#"
send "docker exec school-db psql -U school_user -d school_db -f /tmp/db_opt.sql\r"
expect "#"

# Валідація constraints
puts "\n✔️  Валідую constraints...\n"
send "docker exec school-db psql -U school_user -d school_db -c \"ALTER TABLE schedules VALIDATE CONSTRAINT schedules_weekday_check; ALTER TABLE bot_schedules VALIDATE CONSTRAINT bot_schedules_offset_check; ALTER TABLE schedules VALIDATE CONSTRAINT schedules_start_time_check; ALTER TABLE clubs VALIDATE CONSTRAINT clubs_duration_check;\"\r"
expect "#"

# Перезапуск контейнерів
puts "\n🔄 Перезапускаю контейнери...\n"
send "docker compose -f docker-compose.server.yml down\r"
expect "#"
send "docker compose -f docker-compose.server.yml build --no-cache webapp\r"
expect "#"
send "docker compose -f docker-compose.server.yml up -d\r"
expect "#"

send "sleep 10\r"
expect "#"

# Перевірка
puts "\n✅ Перевіряю статус...\n"
send "docker compose -f docker-compose.server.yml ps\r"
expect "#"

puts "\n╔═══════════════════════════════════════════════════════════════╗\n"
puts "║              ✅ DEPLOYMENT ЗАВЕРШЕНО!                         ║\n"
puts "╚═══════════════════════════════════════════════════════════════╝\n"

send "exit\r"
expect eof

