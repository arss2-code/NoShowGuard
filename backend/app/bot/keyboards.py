from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)
from app.config import settings

def get_main_keyboard(master_tg_id: int | None = None) -> ReplyKeyboardMarkup:
    """Главная клавиатура: быстрый запуск TMA + сервисные кнопки."""
    tma_url = settings.MINI_APP_URL
    if master_tg_id:
        tma_url = f"{settings.MINI_APP_URL}?role=master&master_id={master_tg_id}"

    keyboard = [
        [
            KeyboardButton(
                text="🚀 Открыть NoShowGuard (Кабинет)",
                web_app=WebAppInfo(url=tma_url)
            )
        ],
        [
            KeyboardButton(text="🔗 Моя ссылка для записи"),
            KeyboardButton(text="📊 Моя статистика")
        ],
        [
            KeyboardButton(text="💳 Подписка NoShowGuard"),
            KeyboardButton(text="⚙️ Настройки профиля")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )

def get_master_link_inline_kb(master_tg_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки для открытия Mini App (кабинет мастера или витрина клиента)."""
    bot_name = settings.BOT_USERNAME.replace("@", "")
    client_tma_url = f"https://t.me/{bot_name}/app?startapp=master_{master_tg_id}"
    master_tma_url = f"{settings.MINI_APP_URL}?role=master&master_id={master_tg_id}"

    keyboard = [
        [
            InlineKeyboardButton(
                text="🚀 Открыть кабинет мастера (TMA)",
                web_app=WebAppInfo(url=master_tma_url)
            )
        ],
        [
            InlineKeyboardButton(
                text="📱 Открыть витрину (как видит клиент)",
                url=client_tma_url
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_booking_action_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Кнопки действия по конкретной брони (для пуш-уведомления мастера)."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="⚠️ Клиент не пришел (No-Show)",
                callback_data=f"no_show:{booking_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить запись (вернуть слот)",
                callback_data=f"cancel_booking:{booking_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
