from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)
from app.config import settings

def get_main_keyboard(master_tg_id: int | None = None) -> ReplyKeyboardMarkup:
    """Главная клавиатура мастера: быстрый запуск TMA + сервисные кнопки."""
    tma_url = settings.resolved_webapp_url
    if master_tg_id:
        tma_url = f"{settings.resolved_webapp_url}?role=master&master_id={master_tg_id}"

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
        ],
        [
            KeyboardButton(text="🎁 Пригласить коллегу (+1 мес Про)")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )

def get_client_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура для клиентов."""
    my_bookings_url = f"{settings.resolved_webapp_url}?tab=my-bookings"
    keyboard = [
        [
            KeyboardButton(
                text="📋 Мои записи",
                web_app=WebAppInfo(url=my_bookings_url)
            )
        ],
        [
            KeyboardButton(text="ℹ️ О сервисе NoShowGuard"),
            KeyboardButton(text="💼 Я мастер (подключить сервис)")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )

def get_master_link_inline_kb(master_tg_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки для мастера: открыть свой кабинет или витрину клиента."""
    client_tma_url = settings.get_tma_direct_link(f"master_{master_tg_id}")
    master_tma_url = f"{settings.resolved_webapp_url}?role=master&master_id={master_tg_id}"

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

def get_client_booking_inline_kb(master_tg_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки для клиента при переходе по ссылке мастера."""
    booking_tma_url = f"{settings.resolved_webapp_url}?master_id={master_tg_id}"
    my_bookings_tma_url = f"{settings.resolved_webapp_url}?tab=my-bookings"

    keyboard = [
        [
            InlineKeyboardButton(
                text="📅 Выбрать дату и записаться (СБП)",
                web_app=WebAppInfo(url=booking_tma_url)
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Мои записи",
                web_app=WebAppInfo(url=my_bookings_tma_url)
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_client_my_bookings_inline_kb() -> InlineKeyboardMarkup:
    """Инлайн-кнопка для открытия раздела «Мои записи»."""
    my_bookings_tma_url = f"{settings.resolved_webapp_url}?tab=my-bookings"
    keyboard = [
        [
            InlineKeyboardButton(
                text="📋 Открыть «Мои записи»",
                web_app=WebAppInfo(url=my_bookings_tma_url)
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

def get_client_reminder_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Кнопки интерактивного напоминания клиенту (за 24 часа)."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтверждаю визит",
                callback_data=f"confirm_visit:{booking_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Не смогу прийти (отменить)",
                callback_data=f"cancel_client:{booking_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_role_choice_inline_kb() -> InlineKeyboardMarkup:
    """Выбор роли для нового пользователя без параметров."""
    my_bookings_url = f"{settings.resolved_webapp_url}?tab=my-bookings"
    keyboard = [
        [
            InlineKeyboardButton(
                text="💼 Я мастер услуг (7 дней бесплатно)",
                callback_data="register_master"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Я клиент (мои записи)",
                web_app=WebAppInfo(url=my_bookings_url)
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
