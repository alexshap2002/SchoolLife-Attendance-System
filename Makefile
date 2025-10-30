.PHONY: help run build lint format test migrate seed clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

run: ## Run the application in development mode
	docker compose up --build

build: ## Build the Docker images
	docker compose build

lint: ## Run linting with ruff
	docker compose exec app ruff check app/

format: ## Format code with black and ruff
	docker compose exec app black app/
	docker compose exec app ruff format app/

test: ## Run tests with pytest
	docker compose exec app pytest

migrate: ## Run database migrations
	docker compose exec app alembic upgrade head

migrate-create: ## Create a new migration
	@read -p "Enter migration message: " message; \
	docker compose exec app alembic revision --autogenerate -m "$$message"

seed: ## Seed database with sample data
	docker compose exec app python scripts/seed_data.py

clean: ## Clean up Docker containers and volumes
	docker compose down -v
	docker system prune -f

logs: ## Show application logs
	docker compose logs -f app

shell: ## Open shell in app container
	docker compose exec app bash

db-shell: ## Open PostgreSQL shell (external DB)
	@echo "Connect to external PostgreSQL:"
	@echo "psql -h 213.199.43.90 -U schoola -d schoola"

backup-db: ## Backup database (external DB)
	pg_dump -h 213.199.43.90 -U schoola schoola > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore database (usage: make restore-db FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore-db FILE=backup.sql"; exit 1; fi
	psql -h 213.199.43.90 -U schoola schoola < $(FILE)

setup: ## Initial setup - copy env file and create directories
	cp env.example .env
	mkdir -p creds
	@echo "Please:"
	@echo "1. Edit .env file with your settings"
	@echo "2. Add your Google service account JSON to creds/service_account.json"
	@echo "3. Run 'make run' to start the application"

# ============= PRODUCTION DEPLOYMENT =============
# Configuration - edit these values for your server
SERVER ?= root@213.199.43.90
APP_PATH ?= /opt/schoola
DOMAIN ?= ymbefree.online

# Commands shortcuts
SSH = ssh $(SERVER)
RSYNC = rsync -az --delete --exclude '.git' --exclude '__pycache__' --exclude '.venv' --exclude '*.pyc' --exclude '.DS_Store'

bootstrap: ## One-time server setup (install Docker, create directories)
	@echo "🚀 Setting up server $(SERVER)..."
	@echo "🔍 Checking existing services first..."
	$(SSH) 'echo "Current processes on ports 80,443:"; netstat -tlnp | grep -E ":(80|443)" || echo "Ports 80,443 are free"'
	@echo "📦 Installing Docker (if not present)..."
	$(SSH) 'which docker || (apt-get update && apt-get install -y docker.io docker-compose-plugin curl)'
	$(SSH) 'systemctl enable --now docker 2>/dev/null || echo "Docker already running"'
	$(SSH) 'usermod -aG docker root 2>/dev/null || echo "User already in docker group"'
	@echo "📁 Creating application directory..."
	$(SSH) 'mkdir -p $(APP_PATH)/creds && chown -R root:root $(APP_PATH)'
	@echo "🔥 Configuring firewall..."
	$(SSH) 'ufw allow 80,443/tcp 2>/dev/null || echo "UFW not available or ports already allowed"'
	@echo "✅ Server setup complete! Now run: make ship"

ship: ## Deploy application to server (sync code + restart containers)
	@echo "🚢 Deploying to $(SERVER)..."
	@echo "📁 Syncing files..."
	$(RSYNC) ./ $(SERVER):$(APP_PATH)/
	@echo "🐳 Building and starting containers..."
	$(SSH) 'cd $(APP_PATH) && docker compose up -d --build'
	@echo "⏳ Waiting for services to start..."
	sleep 10
	@echo "🔍 Checking health..."
	$(SSH) 'cd $(APP_PATH) && docker compose ps'
	@echo "✅ Deployment complete!"
	@echo "🌐 Check: https://$(DOMAIN)/health"

up: ## Restart containers without code sync
	@echo "🔄 Restarting containers on $(SERVER)..."
	$(SSH) 'cd $(APP_PATH) && docker compose up -d --build'
	$(SSH) 'cd $(APP_PATH) && docker compose ps'

down: ## Stop all containers on server
	@echo "🛑 Stopping containers on $(SERVER)..."
	$(SSH) 'cd $(APP_PATH) && docker compose down'

logs: ## Show application logs from server
	@echo "📋 Showing logs from $(SERVER)..."
	$(SSH) 'cd $(APP_PATH) && docker compose logs -f --tail=200 app'

logs-all: ## Show all services logs from server
	$(SSH) 'cd $(APP_PATH) && docker compose logs -f --tail=100'

status: ## Check containers status on server
	@echo "📊 Checking status on $(SERVER)..."
	$(SSH) 'cd $(APP_PATH) && docker compose ps'
	@echo ""
	@echo "💾 Disk usage:"
	$(SSH) 'cd $(APP_PATH) && du -sh .'
	@echo ""
	@echo "🐳 Docker images:"
	$(SSH) 'docker images | head -10'

update: ship ## Alias for ship (deploy updates)

clean-server: ## Clean up Docker images and containers on server
	@echo "🧹 Cleaning up Docker on $(SERVER)..."
	$(SSH) 'docker system prune -af'
	$(SSH) 'docker volume prune -f'

ssh: ## Connect to server via SSH
	$(SSH)

check-server: ## Safely check what's running on server before deployment
	@echo "🔍 Безпечна перевірка сервера $(SERVER)..."
	@echo "📊 Поточні процеси на портах 80, 443, 8000, 5432:"
	$(SSH) 'netstat -tlnp | grep -E ":(80|443|8000|5432)" || echo "Порти вільні"'
	@echo ""
	@echo "🐳 Docker контейнери:"
	$(SSH) 'docker ps 2>/dev/null || echo "Docker не запущений або не встановлений"'
	@echo ""
	@echo "📁 Існуючі програми в /opt:"
	$(SSH) 'ls -la /opt/ 2>/dev/null || echo "Папка /opt не існує"'
	@echo ""
	@echo "💾 Використання диску:"
	$(SSH) 'df -h | head -5'
	@echo ""
	@echo "🔧 Запущені веб-сервери:"
	$(SSH) 'ps aux | grep -E "(nginx|apache|caddy|httpd)" | grep -v grep || echo "Веб-сервери не знайдені"'

# Database operations on server
db-backup: ## Backup database from server
	@echo "💾 Creating database backup..."
	$(SSH) 'cd $(APP_PATH) && docker compose exec -T db pg_dump -U schoola schoola > backup_$(shell date +%Y%m%d_%H%M%S).sql'
	@echo "✅ Backup created on server"

db-restore: ## Restore database on server (usage: make db-restore FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then echo "Usage: make db-restore FILE=backup.sql"; exit 1; fi
	@echo "📥 Restoring database from $(FILE)..."
	$(SSH) 'cd $(APP_PATH) && cat $(FILE) | docker compose exec -T db psql -U schoola schoola'

# Monitoring
monitor: ## Monitor server resources
	$(SSH) 'top -bn1 | head -20; echo ""; df -h | head -10; echo ""; free -h'
