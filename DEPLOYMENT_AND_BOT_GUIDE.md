# Полное руководство: Запуск Telegram-бота, TMA и Деплой NoShowGuard

В данном руководстве описан пошаговый процесс подключения реального Telegram-бота, настройки Telegram Mini App (TMA), локального тестирования и развертывания на production-сервере (Docker / Systemd + Nginx).

---

## 1. Регистрация и настройка бота в @BotFather

### Шаг 1.1: Создание бота
1. Откройте в Telegram официального бота [@BotFather](https://t.me/BotFather).
2. Отправьте команду `/newbot`.
3. Введите отображаемое имя (например, `NoShowGuard | Защита от неявок`).
4. Введите юзернейм бота, заканчивающийся на `bot` (например, `NoShowGuard_demo_bot`).
5. Скопируйте полученный **HTTP API Token** (формат: `123456789:ABCdefGHI...`).

### Шаг 1.2: Создание Telegram Mini App (/newapp)
Для того чтобы работали прямые ссылки вида `https://t.me/BotName/app?startapp=master_12345`:
1. В @BotFather отправьте команду `/newapp`.
2. Выберите созданного бота.
3. Введите название приложения: `NoShowGuard`.
4. Введите краткое описание сервиса.
5. Загрузите изображение-обложку (размер 640x360 пикселей).
6. Введите Web App URL:
   - **Локально/Тест:** ваш HTTPS-туннель (например, `https://xxxx.ngrok-free.app/app`).
   - **Продакшн:** ваш боевой HTTPS-домен (например, `https://noshowguard.ru/app`).
7. Введите **Short Name**: укажите `app`.
8. @BotFather сгенерирует прямую ссылку: `https://t.me/ВашБот/app`.

### Шаг 1.3: Настройка постоянной кнопки меню чата (/setmenubutton)
Чтобы у любого пользователя в чате с ботом в левом нижнем углу всегда была видна кнопка запуска WebApp:
1. В @BotFather отправьте команду `/setmenubutton`.
2. Выберите бота.
3. Отправьте URL: `https://ваш-домен/app`.
4. Введите название кнопки: `Запись / Кабинет`.
*(Примечание: бот также автоматически попытается установить эту кнопку через Bot API при старте бэкенда).*

### Шаг 1.4: Рекомендуемые команды (/setcommands)
Отправьте `/setcommands`, выберите бота и вставьте список:
```text
start - Запуск и главное меню
my_bookings - Мои активные записи и история
master - Кабинет мастера (расписание и слоты)
link - Моя персональная ссылка для клиентов
help - Справка и правила отмены (ст. 381.1 ГК РФ)
```

---

## 2. Конфигурация переменных окружения (`.env`)

Создайте или отредактируйте файл `backend/.env`:

```env
# Telegram Bot
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz_ВАШ_ТОКЕН
BOT_USERNAME=ВашЮзернеймБота_без_собаки
MINI_APP_SHORT_NAME=app

# WebApp URL (Telegram Mini App)
# Внимание: для Telegram TMA требуется HTTPS!
WEBAPP_URL=https://ваш-домен.ru/app
MINI_APP_URL=https://t.me/ВашЮзернеймБота/app

# База данных (по умолчанию локальный SQLite в WAL-режиме)
DATABASE_URL=sqlite+aiosqlite:///./noshowguard.db

# Платежи ЮKassa (СБП)
# Оставьте пустыми для работы в демонстрационном режиме (Sandbox/Mock)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_SANDBOX=True

# Настройки бэкенда
HOST=0.0.0.0
PORT=8000
WEBHOOK_BASE_URL=https://ваш-домен.ru
DEFAULT_DEPOSIT_AMOUNT=300
DEPOSIT_LOCK_MINUTES=10
```

---

## 3. Локальное тестирование с реальным Telegram (через Ngrok / Cloudflared)

Telegram WebApp открывается внутри Telegram Webview и **требует валидный HTTPS-сертификат**. Для локального тестирования:

1. **Соберите фронтенд:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
2. **Запустите туннель к порту 8000:**
   ```bash
   ngrok http 8000
   # Либо через Cloudflare:
   cloudflared tunnel --url http://localhost:8000
   ```
3. Скопируйте выданный HTTPS-адрес (например, `https://abc-123.ngrok-free.app`) и укажите его в `backend/.env`:
   ```env
   WEBAPP_URL=https://abc-123.ngrok-free.app/app
   WEBHOOK_BASE_URL=https://abc-123.ngrok-free.app
   ```
4. **Запустите бэкенд:**
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate   # (на Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
5. Перейдите в Telegram в созданного бота, нажмите `/start` или кнопку меню — откроется полноценное приложение!

---

## 4. Развертывание в Production

### Вариант А: Быстрый запуск через Docker Compose (Рекомендуется)

В проекте настроен multi-stage Dockerfile, который автоматически собирает React-фронтенд и упаковывает всё в единый легковесный контейнер с Python 3.12, FastAPI и aiogram:

```bash
# 1. Клонирование репозитория на сервере
git clone https://github.com/arss2-code/NoShowGuard.git
cd NoShowGuard

# 2. Настройка переменных окружения
cp backend/.env.example backend/.env
nano backend/.env   # Вставьте реальный BOT_TOKEN и WEBAPP_URL

# 3. Сборка и запуск в фоновом режиме
docker compose up --build -d

# 4. Проверка логов
docker compose logs -f noshowguard
```

### Вариант Б: Развертывание через Systemd + Nginx (на Ubuntu/Debian)

#### 1. Подготовка окружения
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nodejs npm nginx certbot python3-certbot-nginx
cd /var/www
git clone https://github.com/arss2-code/NoShowGuard.git
cd NoShowGuard

# Сборка фронтенда
cd frontend
npm ci
npm run build
cd ../backend

# Установка бэкенда
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

#### 2. Создание systemd-сервиса
Создайте файл `/etc/systemd/system/noshowguard.service`:
```ini
[Unit]
Description=NoShowGuard Telegram SaaS & TMA Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/NoShowGuard/backend
EnvironmentFile=/var/www/NoShowGuard/backend/.env
ExecStart=/var/www/NoShowGuard/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Включите и запустите сервис:
```bash
sudo chown -R www-data:www-data /var/www/NoShowGuard
sudo systemctl daemon-reload
sudo systemctl enable noshowguard
sudo systemctl start noshowguard
sudo systemctl status noshowguard
```

#### 3. Настройка Nginx и SSL
Создайте конфигурацию `/etc/nginx/sites-available/noshowguard`:
```nginx
server {
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте сайт и выпустите бесплатный SSL-сертификат:
```bash
sudo ln -s /etc/nginx/sites-available/noshowguard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d your-domain.com
```

---

## 5. Подключение реальной ЮKassa (СБП)

1. Зарегистрируйтесь в [ЮKassa для бизнеса](https://yookassa.ru/).
2. Перейдите в раздел **Интеграция -> Ключи API** и сгенерируйте секретный ключ.
3. В `backend/.env` укажите:
   ```env
   YOOKASSA_SHOP_ID=123456
   YOOKASSA_SECRET_KEY=live_ABC123...
   YOOKASSA_SANDBOX=False
   ```
4. В личном кабинете ЮKassa настройте HTTP-уведомления (вебхуки):
   - **URL:** `https://your-domain.com/api/webhooks/yookassa`
   - **События:** `payment.succeeded`, `payment.canceled`
5. Перезапустите сервис: `sudo systemctl restart noshowguard` или `docker compose restart`.

Теперь все депозиты по СБП принимаются в режиме реального времени, а отмены за 12 часов мгновенно производят автовозврат клиенту на банковский счет!
