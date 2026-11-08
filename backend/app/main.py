import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routes.public_api import router as public_router
from app.routes.master_api import router as master_router
from app.routes.webhooks import router as webhooks_router
from app.bot.bot_instance import bot, dp, is_test_token
from app.bot.handlers import router as master_bot_router
from app.services.scheduler import start_scheduler, stop_scheduler
from aiogram.types import MenuButtonWebApp, WebAppInfo

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
        async def run_bot_polling():
            try:
                # Настройка кнопки Menu Button (WebApp) в Telegram с таймаутом
                try:
                    await asyncio.wait_for(
                        bot.set_chat_menu_button(
                            menu_button=MenuButtonWebApp(
                                text="Запись / Кабинет",
                                web_app=WebAppInfo(url=settings.resolved_webapp_url)
                            )
                        ),
                        timeout=5.0
                    )
                    logger.info("Telegram Menu Button успешно установлена: %s", settings.resolved_webapp_url)
                except Exception as e:
                    logger.warning("Установка Menu Button отложена или завершилась по таймауту: %s", e)

                # Регистрация команд бота в меню Telegram
                try:
                    from aiogram.types import BotCommand
                    await asyncio.wait_for(
                        bot.set_my_commands([
                            BotCommand(command="start", description="Запуск и главное меню"),
                            BotCommand(command="my_bookings", description="Мои записи и бронирования"),
                            BotCommand(command="master", description="Кабинет мастера (расписание и слоты)"),
                            BotCommand(command="link", description="Моя персональная ссылка для клиентов"),
                            BotCommand(command="invite", description="Пригласить коллегу (+1 мес Про)"),
                            BotCommand(command="help", description="Справка и правила отмены (ст. 381.1 ГК РФ)")
                        ]),
                        timeout=5.0
                    )
                    logger.info("Команды бота успешно зарегистрированы в Telegram")
                except Exception as e:
                    logger.warning("Регистрация команд бота отложена: %s", e)

                logger.info("Запуск Telegram-бота в режиме Long Polling...")
                await dp.start_polling(bot)
            except asyncio.CancelledError:
                logger.info("Polling Telegram-бота остановлен.")
            except Exception as e:
                logger.error("Ошибка при работе Polling Telegram-бота: %s", e)

        polling_task = asyncio.create_task(run_bot_polling())
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

# Сжатие трафика Gzip (ускоряет отдачу JS/CSS бандла в 3.5 раза)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Кеширование ассетов Vite (ассеты с хешами кешируются навсегда в браузере)
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if "/assets/" in request.url.path:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.url.path in ("/app", "/app/", "/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

app.add_middleware(CacheControlMiddleware)

# Подключение маршрутов API
app.include_router(public_router)
app.include_router(master_router)
app.include_router(webhooks_router)

# Раздача статики собранного фронтенда TMA (если собрана)
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/app/")

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "NoShowGuard API",
        "version": "1.1.0"
    }
