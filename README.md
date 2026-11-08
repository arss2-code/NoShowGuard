# NoShowGuard

Микро-SaaS продукт в экосистеме Telegram: бот + Telegram Mini App для частных мастеров сферы услуг (бьюти, массаж, частные тренеры), устраняющий неявки клиентов ("no-show") через гарантированный обеспечительный депозит по СБП.

## Документация проекта

- 🚀 **[Руководство по запуску бота, TMA и деплою (DEPLOYMENT_AND_BOT_GUIDE.md)](./DEPLOYMENT_AND_BOT_GUIDE.md)** — пошаговая инструкция: получение токена BotFather, настройка `/newapp` и `/setmenubutton`, локальный запуск (ngrok) и деплой (Docker Compose / Systemd).
- 📄 **[Краткий общий план проекта (PROJECT_OVERVIEW.md)](./PROJECT_OVERVIEW.md)** — архитектура, ценность, юридическая модель (ст. 381.1 ГК РФ) и сводный роадмап.
- 📁 **[Планы для отдельных чатов по фазам](./plans/)**:
  - `plans/phase_0_prevalidation.md` — Фаза 0: Предвалидация без кода (День 1).
  - `plans/phase_1_1_backend_bot.md` — Фаза 1.1: Backend, БД, aiogram 3 и интеграция СБП (День 2).
  - `plans/phase_1_2_frontend_tma.md` — Фаза 1.2: Frontend Telegram Mini App и автонапоминания (День 3).
  - `plans/phase_2_growth.md` — Фаза 2: Партизанский маркетинг и первые 100 мастеров (Недели 2–4).
- 🔬 **[Исследования рынка (research/2026-11-07/)](./research/2026-11-07/)** — сигналы, конкуренты, кластеры и отчёт.

## Быстрый старт (Docker Compose)

```bash
cp backend/.env.example backend/.env
# Укажите BOT_TOKEN в backend/.env
docker compose up --build -d
```
Приложение будет доступно по адресу `http://localhost:8000/app/`, а бот автоматически запустится и установит кнопку Menu Button в Telegram!
