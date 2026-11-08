import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routes.public_api import router as public_router
from app.routes.master_api import router as master_router
from app.routes.webhooks import router as webhooks_router
from app.bot.bot_instance import bot, dp, is_test_token
from app.bot.handlers import router as master_bot_router
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("NoShowGuard")

polling_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Инициализация базы данных...")
    await init_db()

    # Запуск планировщика автонапоминаний
    start_scheduler()

    # Подключаем роутеры бота
    dp.include_router(master_bot_router)

    global polling_task
    if not is_test_token:
        logger.info("Запуск Telegram-бота в режиме Long Polling...")
        polling_task = asyncio.create_task(dp.start_polling(bot))
    else:
        logger.warning("BOT_TOKEN не задан или является тестовым. Polling бота пропущен.")

    yield

    # --- Shutdown ---
    stop_scheduler()

    if polling_task:
        logger.info("Остановка Polling бота...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    await bot.session.close()
    logger.info("Бэкенд NoShowGuard успешно остановлен.")

app = FastAPI(
    title="NoShowGuard API",
    description="Микро-SaaS для ликвидации неявок клиентов мастеров услуг за счет сбора СБП-депозитов",
    version="1.2.0",
    lifespan=lifespan
)

# Разрешаем CORS для Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов API
app.include_router(public_router)
app.include_router(master_router)
app.include_router(webhooks_router)

# Раздача статики собранного фронтенда TMA (если собрана)
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "NoShowGuard API",
        "version": "1.1.0"
    }
