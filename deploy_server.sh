#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🚀 АВТОМАТИЧЕСКИЙ ДЕПЛОЙ NoShowGuard НА PRODUCTION VPS"
echo "=========================================================="

DOMAIN="lightweight-oval-falling-crossing.trycloudflare.com"
WEBAPP_URL="https://${DOMAIN}/app"
BOT_TOKEN="9223503605:AAHbBYxWZHuq0aCJgzI44eWSl9il5gJ1M8I"
BOT_USERNAME="NoShowGuard_demo_bot"

echo "[1/6] Обновление пакетов и установка зависимостей..."
apt-get update -y
apt-get install -y curl git nginx certbot python3-certbot-nginx

# Установка Docker, если еще не установлен
if ! command -v docker &> /dev/null; then
    echo "Установка Docker..."
    curl -fsSL https://get.docker.com | sh
fi

echo "[2/6] Клонирование репозитория в /opt/noshowguard..."
if [ -d "/opt/noshowguard/.git" ]; then
    cd /opt/noshowguard
    git pull origin main
else
    rm -rf /opt/noshowguard
    git clone https://github.com/arss2-code/NoShowGuard.git /opt/noshowguard
    cd /opt/noshowguard
fi

echo "[3/6] Настройка production .env..."
cat <<EOF > /opt/noshowguard/backend/.env
BOT_TOKEN=${BOT_TOKEN}
BOT_USERNAME=${BOT_USERNAME}
MINI_APP_SHORT_NAME=app
WEBAPP_URL=${WEBAPP_URL}
MINI_APP_URL=https://t.me/${BOT_USERNAME}/app
DATABASE_URL=sqlite+aiosqlite:///./noshowguard.db
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_SANDBOX=True
HOST=0.0.0.0
PORT=8000
WEBHOOK_BASE_URL=https://${DOMAIN}
DEFAULT_DEPOSIT_AMOUNT=300
DEPOSIT_LOCK_MINUTES=10
EOF

echo "[4/6] Настройка Nginx reverse proxy..."
cat <<EOF > /etc/nginx/sites-available/noshowguard
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/noshowguard /etc/nginx/sites-enabled/noshowguard
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "[5/6] Выпуск Let's Encrypt SSL сертификата для ${DOMAIN}..."
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --register-unsafely-without-email --redirect || echo "SSL сертификат уже настроен или обновлен."

systemctl reload nginx

echo "[6/6] Запуск NoShowGuard в Docker Compose..."
cd /opt/noshowguard
docker compose down || true
docker compose up -d --build

echo ""
echo "=========================================================="
echo "🎉 NoShowGuard УСПЕШНО РАЗВЕРНУТ И РАБОТАЕТ 24/7!"
echo "=========================================================="
echo "🌐 Боевой WebApp URL: ${WEBAPP_URL}"
echo "🤖 Telegram-бот: https://t.me/${BOT_USERNAME}"
echo "=========================================================="
