from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)
from app.config import settings

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура управления для мастера."""
    keyboard = [
        [
            KeyboardButton(text="🔗 Моя ссылка для записи"),
            KeyboardButton(text="📅 Мои слоты на сегодня")
        ],
        [
            KeyboardButton(text="➕ Создать слоты на сегодня"),
            KeyboardButton(text="➕ Создать слоты на завтра")
        ],
        [
            KeyboardButton(text="⚙️ Мой профиль")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )

def get_master_link_inline_kb(master_tg_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопка для открытия Mini App мастера и копирования ссылки."""
    # startapp параметр передает tg_id мастера в Mini App
    bot_name = settings.BOT_USERNAME.replace("@", "")
    tma_url = f"https://t.me/{bot_name}/app?startapp=master_{master_tg_id}"
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📱 Открыть витрину (как видит клиент)",
                url=tma_url
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_booking_action_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Кнопки действия по конкретной брони (для пуш-уведомления мастера)."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Отменить запись (вернуть слот)",
                callback_data=f"cancel_booking:{booking_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚠️ Клиент не пришел (No-Show)",
                callback_data=f"no_show:{booking_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
