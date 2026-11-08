from datetime import datetime, date, timedelta, time
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Master, Slot, SlotStatus, Booking, utc_now
from app.config import settings
from app.bot.keyboards import (
    get_main_keyboard,
    get_client_reply_keyboard,
    get_master_link_inline_kb,
    get_client_booking_inline_kb,
    get_client_my_bookings_inline_kb,
    get_booking_action_keyboard,
    get_client_reminder_keyboard,
    get_role_choice_inline_kb
)
from app.bot.bot_instance import safe_send_message
from app.services.slot_service import process_client_cancellation
from app.services.payment import payment_service

router = Router(name="hybrid_bot_router")

async def get_or_create_master(tg_id: int, full_name: str, username: str | None = None) -> Master:
    """Регистрация мастера в системе или получение существующего."""
    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        result = await db.execute(stmt)
        master = result.scalar_one_or_none()

        if not master:
            now = utc_now()
            master = Master(
                tg_id=tg_id,
                full_name=full_name,
                username=username,
                profession="Мастер услуг",
                deposit_amount=settings.DEFAULT_DEPOSIT_AMOUNT,
                trial_ends_at=now + timedelta(days=7),
                subscription_tier="trial",
                digest_enabled=True,
                digest_time="09:00"
            )
            db.add(master)
            await db.commit()
            await db.refresh(master)
        return master

async def send_master_welcome(message: Message, master: Master):
    """Приветственное меню и панель управления мастера."""
    tg_id = master.tg_id
    booking_link = settings.get_tma_direct_link(f"master_{tg_id}")

    welcome_text = (
        f"👋 Здравствуйте, <b>{master.full_name}</b>!\n\n"
        f"🛡 <b>NoShowGuard</b> — ваш умный ассистент и защита расписания от неявок.\n"
        f"Клиенты записываются через удобный Telegram Mini App и вносят "
        f"гарантийный депозит <b>{master.deposit_amount} ₽</b> через СБП.\n\n"
        f"🎁 <b>Вам начислен бесплатный пробный период: 7 дней</b> со всеми функциями!\n\n"
        f"🔗 <b>Ваша ссылка для клиентов:</b>\n"
        f"<code>{booking_link}</code>\n\n"
        f"Управляйте расписанием, слотами и подпиской в удобном приложении:"
    )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(tg_id)
    )
    await message.answer(
        "📱 Выберите нужный раздел в Telegram Mini App:",
        reply_markup=get_master_link_inline_kb(tg_id)
    )

@router.message(CommandStart())
async def handle_start(message: Message):
    """
    Гибридный обработчик команды /start:
    - Разбирает параметры deep linking (клиент по ссылке мастера, раздел 'Мои записи', кабинет мастера)
    - Направляет пользователя по правильному сценарию.
    """
    user = message.from_user
    tg_id = user.id
    full_name = user.full_name or "Пользователь"
    username = user.username

    # Извлекаем параметр start, например: /start master_1234567 или /start my_bookings
    text_parts = message.text.split(maxsplit=1) if message.text else []
    start_param = text_parts[1].strip() if len(text_parts) > 1 else ""

    # 1. Сценарий: Клиент перешел по персональной ссылке мастера
    # Формат: master_1234567 или числовой ID мастера
    target_master_tg_id: int | None = None
    if start_param.startswith("master_"):
        raw_id = start_param.replace("master_", "")
        if raw_id.isdigit():
            target_master_tg_id = int(raw_id)
    elif start_param.isdigit() and int(start_param) != tg_id:
        target_master_tg_id = int(start_param)

    if target_master_tg_id:
        async with AsyncSessionLocal() as db:
            stmt = select(Master).where(Master.tg_id == target_master_tg_id)
            target_master = (await db.execute(stmt)).scalar_one_or_none()

        if target_master:
            client_welcome = (
                f"👋 Здравствуйте, <b>{full_name}</b>!\n\n"
                f"Вы перешли для онлайн-записи к мастеру <b>{target_master.full_name}</b> "
                f"({target_master.profession}).\n\n"
                f"🛡 <b>Гарантия бронирования NoShowGuard:</b>\n"
                f"• Фиксация времени за вами без очередей и переписок\n"
                f"• Обеспечительный депозит <b>{target_master.deposit_amount} ₽</b> по СБП (ст. 381.1 ГК РФ)\n"
                f"• Сумма депозита на 100% засчитывается в стоимость вашей услуги\n"
                f"• Бесплатная отмена за 12 часов с мгновенным автовозвратом по СБП\n\n"
                f"Нажмите кнопку ниже, чтобы выбрать удобную дату и время:"
            )
            await message.answer(
                client_welcome,
                parse_mode="HTML",
                reply_markup=get_client_reply_keyboard()
            )
            await message.answer(
                "📅 <b>Онлайн-запись:</b>",
                reply_markup=get_client_booking_inline_kb(target_master.tg_id)
            )
            return
        else:
            await message.answer(
                "ℹ️ Мастер по данной ссылке не найден или изменил настройки. "
                "Вы можете открыть раздел «Мои записи» или зарегистрироваться как мастер.",
                reply_markup=get_role_choice_inline_kb()
            )
            return

    # 2. Сценарий: Прямой переход в «Мои записи»
    if start_param in ("my_bookings", "mybookings"):
        await message.answer(
            "📋 <b>Ваши бронирования и записи:</b>\n\n"
            "Здесь вы можете посмотреть предстоящие визиты, таймер до сеанса или отменить бронь с гарантированным возвратом.",
            parse_mode="HTML",
            reply_markup=get_client_reply_keyboard()
        )
        await message.answer(
            "📱 Нажмите для просмотра:",
            reply_markup=get_client_my_bookings_inline_kb()
        )
        return

    # 3. Сценарий: Реферальная ссылка от коллеги-мастера
    if start_param.startswith("ref_"):
        referrer_id_raw = start_param.replace("ref_", "")
        master = await get_or_create_master(tg_id, full_name, username)
        if referrer_id_raw.isdigit() and int(referrer_id_raw) != tg_id:
            ref_id = int(referrer_id_raw)
            # Уведомляем пригласившего коллегу
            await safe_send_message(
                chat_id=ref_id,
                text=(
                    f"🎉 <b>Коллега присоединился по вашей ссылке!</b>\n\n"
                    f"Мастер <b>{full_name}</b> подключился к NoShowGuard.\n"
                    f"Вам начислен <b>+1 месяц тарифа «Про»</b> в подарок!"
                )
            )
        await send_master_welcome(message, master)
        return

    # 4. Сценарий: Вход или регистрация мастера
    if start_param in ("master_dashboard", "master"):
        master = await get_or_create_master(tg_id, full_name, username)
        await send_master_welcome(message, master)
        return

    # 4. Без параметров: Проверяем, зарегистрирован ли уже пользователь как мастер
    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        existing_master = (await db.execute(stmt)).scalar_one_or_none()

    if existing_master:
        # Пользователь уже является мастером
        await send_master_welcome(message, existing_master)
    else:
        # Новый пользователь: по умолчанию создаем мастера для бесшовного онбординга
        master = await get_or_create_master(tg_id, full_name, username)
        await send_master_welcome(message, master)

@router.callback_query(F.data == "register_master")
async def handle_callback_register_master(call: CallbackQuery):
    """Регистрация мастера по кнопке выбора роли."""
    user = call.from_user
    master = await get_or_create_master(user.id, user.full_name or "Мастер", user.username)
    await call.answer("Вы зарегистрированы как мастер!")
    booking_link = settings.get_tma_direct_link(f"master_{master.tg_id}")

    text = (
        f"🎉 <b>Добро пожаловать в команду мастеров NoShowGuard!</b>\n\n"
        f"Вам начислен бесплатный пробный период <b>7 дней</b>.\n\n"
        f"🔗 <b>Ваша персональная ссылка для записи:</b>\n"
        f"<code>{booking_link}</code>"
    )
    await call.message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(master.tg_id))
    await call.message.answer("📱 Кабинет мастера:", reply_markup=get_master_link_inline_kb(master.tg_id))

@router.message(F.text.in_({"💼 Я мастер (подключить сервис)", "💼 Я мастер", "💼 Подключить мой салон / Я мастер"}))
async def handle_text_register_master(message: Message):
    """Переключение в режим мастера по текстовой кнопке."""
    user = message.from_user
    master = await get_or_create_master(user.id, user.full_name or "Мастер", user.username)
    await send_master_welcome(message, master)

@router.message(Command("my_bookings"))
@router.message(F.text.in_({"📋 Мои записи", "Мои записи"}))
async def handle_cmd_my_bookings(message: Message):
    """Быстрый доступ к разделу «Мои записи» для клиентов."""
    text = (
        f"📋 <b>Ваши записи и активные брони:</b>\n\n"
        f"Отслеживайте статус визита, таймер обратного отсчета до сеанса "
        f"и управляйте отменой с автовозвратом по СБП в приложении:"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_client_my_bookings_inline_kb()
    )

@router.message(Command("master"))
async def handle_cmd_master(message: Message):
    """Команда быстрого перехода в кабинет мастера."""
    user = message.from_user
    master = await get_or_create_master(user.id, user.full_name or "Мастер", user.username)
    await send_master_welcome(message, master)

@router.message(Command("link"))
@router.message(F.text == "🔗 Моя ссылка для записи")
async def handle_get_link(message: Message):
    """Отправка персональной ссылки для записи."""
    tg_id = message.from_user.id
    booking_link = settings.get_tma_direct_link(f"master_{tg_id}")

    text = (
        f"🔗 <b>Ваша персональная ссылка для бронирования:</b>\n"
        f"<code>{booking_link}</code>\n\n"
        f"💡 <b>Куда вставить ссылку:</b>\n"
        f"• В шапку профиля Instagram / Telegram-канала\n"
        f"• В автоответчик WhatsApp / Telegram\n"
        f"• Отправлять клиентам в ответ на «Хочу записаться!»"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_master_link_inline_kb(tg_id)
    )

@router.message(Command("invite"))
@router.message(F.text.in_({"🎁 Пригласить коллегу (+1 мес Про)", "🎁 Пригласить коллегу"}))
async def handle_invite_partner(message: Message):
    """Партнерская программа для мастеров: +1 месяц тарифа Про за приглашение коллеги."""
    tg_id = message.from_user.id
    clean_bot = settings.BOT_USERNAME.replace("@", "")
    referral_link = f"https://t.me/{clean_bot}?start=ref_{tg_id}"

    text = (
        f"🎁 <b>Партнерская программа «Пригласи коллегу»:</b>\n\n"
        f"Поделитесь NoShowGuard с коллегой-мастером (бровист, парикмахер, массажист, тренер). "
        f"Когда коллега подключит сервис, <b>вы оба получите +1 месяц максимального тарифа «Про» бесплатно!</b>\n\n"
        f"🔗 <b>Ваша ссылка для приглашения:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"📋 <b>Готовое сообщение для пересылки:</b>\n"
        f"<i>«Привет! Я перевожу клиентов на запись через бота NoShowGuard — он автоматически берет депозит 300 ₽ по СБП и исключает неявки. Попробуй 7 дней бесплатно: {referral_link}»</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("help"))
@router.message(F.text.in_({"ℹ️ О сервисе NoShowGuard", "ℹ️ Правила отмены и СБП"}))
async def handle_help(message: Message):
    """Справка по юридическим правилам и работе сервиса."""
    text = (
        f"🛡 <b>NoShowGuard — надежная защита от срыва записей:</b>\n\n"
        f"<b>1. Обеспечительный платеж (ст. 381.1 ГК РФ):</b>\n"
        f"При бронировании клиент вносит небольшой депозит (обычно 300–500 ₽) через СБП. "
        f"Сумма на 100% засчитывается в оплату сеанса при явке.\n\n"
        f"<b>2. Правило 12 часов:</b>\n"
        f"• <b>За 12 часов и ранее:</b> бесплатная отмена. Депозит мгновенно возвращается клиенту по СБП, а слот освобождается.\n"
        f"• <b>Менее чем за 12 часов:</b> депозит удерживается в пользу мастера в качестве компенсации расходов (ФПР по ст. 32 ЗоЗПП, ст. 782 ГК РФ), а окно возвращается в расписание.\n\n"
        f"<b>3. Автоматические напоминания:</b>\n"
        f"Бот присылает клиенту интерактивное напоминание за 24 часа и за 2 часа до сеанса."
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.in_({"➕ Создать слоты на сегодня", "➕ Создать слоты на завтра"}))
async def handle_create_standard_slots(message: Message):
    """Быстрое создание стандартных рабочих слотов (10:00, 12:00, 14:00, 16:00, 18:00)."""
    tg_id = message.from_user.id
    is_tomorrow = "завтра" in message.text
    target_date = date.today() + (timedelta(days=1) if is_tomorrow else timedelta(days=0))
    date_str = "на завтра" if is_tomorrow else "на сегодня"

    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        result = await db.execute(stmt)
        master = result.scalar_one_or_none()

        if not master:
            await message.answer("Сначала отправьте /start для регистрации.")
            return

        standard_times = [
            (time(10, 0), time(11, 30)),
            (time(12, 0), time(13, 30)),
            (time(14, 0), time(15, 30)),
            (time(16, 0), time(17, 30)),
            (time(18, 0), time(19, 30)),
        ]

        created_count = 0
        for start_t, end_t in standard_times:
            start_dt = datetime.combine(target_date, start_t)
            end_dt = datetime.combine(target_date, end_t)

            check_stmt = select(Slot).where(
                and_(
                    Slot.master_id == master.id,
                    Slot.start_time == start_dt
                )
            )
            existing = (await db.execute(check_stmt)).scalar_one_or_none()
            if not existing:
                new_slot = Slot(
                    master_id=master.id,
                    start_time=start_dt,
                    end_time=end_dt,
                    status=SlotStatus.FREE
                )
                db.add(new_slot)
                created_count += 1

        await db.commit()

    if created_count > 0:
        await message.answer(
            f"✅ Успешно добавлено <b>{created_count}</b> свободных слотов {date_str} ({target_date.strftime('%d.%m.%Y')}).",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"ℹ️ Слоты {date_str} ({target_date.strftime('%d.%m.%Y')}) уже были созданы ранее.",
            parse_mode="HTML"
        )

@router.message(F.text == "📅 Мои слоты на сегодня")
async def handle_today_slots(message: Message):
    """Просмотр расписания на сегодня."""
    tg_id = message.from_user.id
    today = date.today()

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Slot)
            .join(Master, Slot.master_id == Master.id)
            .options(selectinload(Slot.booking))
            .where(
                and_(
                    Master.tg_id == tg_id,
                    Slot.start_time >= datetime.combine(today, time.min),
                    Slot.start_time <= datetime.combine(today, time.max)
                )
            )
            .order_by(Slot.start_time.asc())
        )
        slots = (await db.execute(stmt)).scalars().all()

    if not slots:
        await message.answer(
            f"У вас пока нет слотов на сегодня ({today.strftime('%d.%m.%Y')}).\n"
            f"Нажмите кнопку <b>«➕ Создать слоты на сегодня»</b> ниже.",
            parse_mode="HTML"
        )
        return

    lines = [f"📅 <b>Ваше расписание на сегодня ({today.strftime('%d.%m.%Y')}):</b>\n"]
    for s in slots:
        time_str = f"{s.start_time.strftime('%H:%M')} – {s.end_time.strftime('%H:%M')}"
        if s.status == SlotStatus.FREE:
            lines.append(f"🟢 <code>{time_str}</code> — Свободно")
        elif s.status == SlotStatus.PENDING:
            lines.append(f"🟡 <code>{time_str}</code> — Ожидает оплаты депозита")
        elif s.status == SlotStatus.BOOKED:
            client_info = s.booking.client_name if s.booking else "Клиент"
            service = s.booking.service_title if s.booking else "Услуга"
            lines.append(f"🔴 <code>{time_str}</code> — <b>{client_info}</b> ({service}) [Депозит внесен]")
        elif s.status == SlotStatus.CANCELLED:
            lines.append(f"⚪ <code>{time_str}</code> — Отменено")
        elif s.status == SlotStatus.COMPLETED:
            lines.append(f"✔️ <code>{time_str}</code> — Завершено")

    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text.in_({"📊 Моя статистика", "Статистика"}))
async def handle_stats(message: Message):
    """Спасенная выручка и статистика мастера."""
    tg_id = message.from_user.id
    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        master = (await db.execute(stmt)).scalar_one_or_none()
        if not master:
            await message.answer("Сначала отправьте /start.")
            return

        saved_stmt = (
            select(func.coalesce(func.sum(Booking.deposit_amount), 0))
            .join(Slot, Booking.slot_id == Slot.id)
            .where(
                and_(
                    Slot.master_id == master.id,
                    Booking.payment_status == "no_show_retained"
                )
            )
        )
        saved_revenue = (await db.execute(saved_stmt)).scalar() or 0

        total_stmt = (
            select(func.count(Booking.id))
            .join(Slot, Booking.slot_id == Slot.id)
            .where(
                and_(
                    Slot.master_id == master.id,
                    Booking.payment_status.in_(["succeeded", "no_show_retained"])
                )
            )
        )
        total_bookings = (await db.execute(total_stmt)).scalar() or 0

    text = (
        f"📊 <b>Ваша статистика NoShowGuard:</b>\n\n"
        f"💰 <b>Спасенная выручка от неявок:</b> <code>{saved_revenue} ₽</code>\n"
        f"<i>(Удержанные гарантийные депозиты по ст. 381.1 ГК РФ)</i>\n\n"
        f"📅 <b>Всего сеансов с гарантией:</b> {total_bookings}\n"
        f"🛡 <b>Защита от срывов:</b> 100% предохранение графика\n\n"
        f"Подробный интерактивный график доступен в Telegram Mini App:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_master_link_inline_kb(tg_id))

@router.message(F.text.in_({"💳 Подписка NoShowGuard", "Подписка"}))
async def handle_subscription(message: Message):
    """Информация о подписке и тарифах."""
    tg_id = message.from_user.id
    now = utc_now()
    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        master = (await db.execute(stmt)).scalar_one_or_none()
        if not master:
            await message.answer("Сначала отправьте /start.")
            return

        trial_days = 0
        if master.trial_ends_at and master.trial_ends_at > now:
            trial_days = max(1, (master.trial_ends_at - now).days + 1)

    status_str = f"🎁 <b>Бесплатный триал:</b> осталось {trial_days} дн." if trial_days > 0 else f"Тариф: <b>{master.subscription_tier.upper()}</b>"

    text = (
        f"💳 <b>Управление подпиской NoShowGuard:</b>\n\n"
        f"Текущий статус: {status_str}\n\n"
        f"<b>Доступные тарифы:</b>\n"
        f"• <b>«Старт»</b> — <b>490 ₽/мес</b> (до 40 записей, СБП-депозиты, напоминания)\n"
        f"• <b>«Про»</b> — <b>890 ₽/мес</b> (безлимитные брони, лист ожидания, брендинг)\n\n"
        f"💡 <i>Подписка окупается с первого же сохраненного сеанса!</i>\n\n"
        f"Продлите подписку в 1 клик по СБП в приложении:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_master_link_inline_kb(tg_id))

@router.message(F.text.in_({"⚙️ Настройки профиля", "⚙️ Мой профиль"}))
async def handle_profile(message: Message):
    """Информация о мастере, настройках депозита и дайджеста."""
    tg_id = message.from_user.id
    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        master = (await db.execute(stmt)).scalar_one_or_none()

    if not master:
        await message.answer("Сначала отправьте /start.")
        return

    digest_status = f"Включен (в {master.digest_time})" if master.digest_enabled else "Выключен"

    loc_lines = []
    if master.salon_name:
        loc_lines.append(f"🏢 <b>Салон/студия:</b> {master.salon_name}")
    if master.address:
        loc_lines.append(f"📍 <b>Адрес приёма:</b> {master.address}")
    location_block = ("\n" + "\n".join(loc_lines)) if loc_lines else ""

    text = (
        f"⚙️ <b>Профиль и настройки мастера:</b>\n\n"
        f"👤 <b>Имя:</b> {master.full_name}\n"
        f"💼 <b>Специализация:</b> {master.profession}\n"
        f"{location_block}\n"
        f"💰 <b>Размер обеспечительного депозита:</b> {master.deposit_amount} ₽\n"
        f"☀️ <b>Утренний дайджест:</b> {digest_status}\n"
        f"🛡 <b>Юридическое основание:</b> ст. 381.1 ГК РФ (обеспечительный платеж на возмещение ФПР)\n\n"
        f"Изменить размер депозита, адрес, услуги или расписание можно в приложении:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_master_link_inline_kb(tg_id))

@router.callback_query(F.data.startswith("no_show:"))
async def handle_no_show_callback(call: CallbackQuery):
    """Обработка кнопки «Клиент не пришел»."""
    booking_id = int(call.data.split(":")[1])

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.slot))
            .where(Booking.id == booking_id)
        )
        booking = (await db.execute(stmt)).scalar_one_or_none()

        if not booking:
            await call.answer("Запись не найдена.", show_alert=True)
            return

        slot = booking.slot
        slot.status = SlotStatus.COMPLETED
        booking.payment_status = "no_show_retained"
        await db.commit()

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        f"⚠️ <b>Зафиксирована неявка (No-Show) по брони #{booking_id}!</b>\n\n"
        f"Сумма гарантийного депозита <b>{booking.deposit_amount} ₽</b> удержана "
        f"в счет покрытия фактических расходов мастера (ст. 381.1 ГК РФ).",
        parse_mode="HTML"
    )
    await call.answer("Неявка зафиксирована, депозит удержан.")

@router.callback_query(F.data.startswith("cancel_booking:"))
async def handle_cancel_booking_callback(call: CallbackQuery):
    """Отмена записи мастером и возврат слота в статус FREE."""
    booking_id = int(call.data.split(":")[1])

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.slot).selectinload(Slot.master))
            .where(Booking.id == booking_id)
        )
        booking = (await db.execute(stmt)).scalar_one_or_none()

        if not booking:
            await call.answer("Запись не найдена.", show_alert=True)
            return

        slot = booking.slot
        slot.status = SlotStatus.FREE
        slot.locked_until = None
        booking.payment_status = "cancelled_by_master"
        await db.commit()

        # Если клиент вносил депозит и у него есть Telegram ID, возвращаем депозит и уведомляем
        if booking.payment_id:
            payment_service.refund_deposit(
                payment_id=booking.payment_id,
                amount=booking.deposit_amount,
                booking_id=booking.id
            )

        if booking.client_tg_id:
            slot_time_str = slot.start_time.strftime("%d.%m.%Y в %H:%M")
            await safe_send_message(
                chat_id=booking.client_tg_id,
                text=(
                    f"⚠️ <b>Внимание: ваша запись отменена мастером</b>\n\n"
                    f"Сеанс на <b>{slot_time_str}</b> был отменен специалистом.\n"
                    f"Сумма обеспечительного депозита <b>{booking.deposit_amount} ₽</b> автоматически возвращена на ваш счет СБП."
                )
            )

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        f"ℹ️ Запись #{booking_id} отменена мастером. Слот снова свободен для бронирования.",
        parse_mode="HTML"
    )
    await call.answer("Запись отменена.")

@router.callback_query(F.data.startswith("confirm_visit:"))
async def handle_confirm_visit(call: CallbackQuery):
    """Клиент подтверждает визит через интерактивное напоминание."""
    booking_id = int(call.data.split(":")[1])

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.slot).selectinload(Slot.master))
            .where(Booking.id == booking_id)
        )
        booking = (await db.execute(stmt)).scalar_one_or_none()

        if booking and booking.slot and booking.slot.master:
            slot_time = booking.slot.start_time.strftime("%d.%m.%Y в %H:%M")
            master_msg = (
                f"✅ <b>Клиент подтвердил визит!</b>\n\n"
                f"Клиент <b>{booking.client_name}</b> подтвердил явку на сеанс <b>{slot_time}</b>.\n"
                f"Услуга: {booking.service_title}"
            )
            await safe_send_message(chat_id=booking.slot.master.tg_id, text=master_msg)

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        "✅ <b>Отлично, спасибо!</b>\nМы уведомили мастера, что вы будете вовремя.",
        parse_mode="HTML"
    )
    await call.answer("Визит подтвержден!")

@router.callback_query(F.data.startswith("cancel_client:"))
async def handle_cancel_client(call: CallbackQuery):
    """Клиент отменяет запись через напоминание по правилу 12 часов."""
    booking_id = int(call.data.split(":")[1])

    async with AsyncSessionLocal() as db:
        try:
            res = await process_client_cancellation(db, booking_id)
        except ValueError as e:
            await call.answer(str(e), show_alert=True)
            return

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        f"ℹ️ {res['message']}",
        parse_mode="HTML"
    )
    await call.answer("Запись отменена.")
