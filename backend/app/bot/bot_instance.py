import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.token import validate_token, TokenValidationError
from app.config import settings

logger = logging.getLogger(__name__)

token_to_use = settings.BOT_TOKEN
is_test_token = False

try:
    validate_token(token_to_use)
    if "test" in token_to_use.lower() or "sample" in token_to_use.lower():
        is_test_token = True
except TokenValidationError:
    logger.warning("BOT_TOKEN не является валидным токеном Telegram BotFather. Бот будет работать в mock-режиме для тестов.")
    token_to_use = "123456789:AAG_test_token_for_mocking_purposes1234"
    is_test_token = True

bot = Bot(
    token=token_to_use,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

async def safe_send_message(chat_id: int, text: str, reply_markup=None) -> bool:
    """Безопасная отправка сообщения в Telegram с защитой от сбоев при тестовом токене."""
    if is_test_token:
        logger.info("[MOCK TELEGRAM] Отправка сообщения в чат %s: %s", chat_id, text)
        return True
    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        return True
    except Exception as e:
        logger.error("Не удалось отправить сообщение пользователю %s: %s", chat_id, e)
        return False
