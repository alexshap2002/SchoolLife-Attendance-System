#!/bin/bash

echo "🛑 Зупинка локального додатку 'Школа Життя'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

docker compose -f docker-compose.local.yml down

echo ""
echo "✅ Додаток зупинено!"
echo ""
echo "ℹ️  База даних school-db НЕ була зупинена (вона працює окремо)"
echo ""
echo "🔍 Перевірити що працює:"
echo "   docker ps"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

