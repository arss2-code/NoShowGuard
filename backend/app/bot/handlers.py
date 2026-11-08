from datetime import datetime, date, timedelta, time
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Master, Slot, SlotStatus, Booking, utc_now
from app.config import settings
from app.bot.keyboards import (
    get_main_keyboard,
    get_master_link_inline_kb,
    get_booking_action_keyboard
)
from app.bot.bot_instance import safe_send_message

router = Router(name="master_router")

@router.message(CommandStart())
async def handle_start(message: Message):
    """Регистрация мастера и приветственное меню."""
    tg_id = message.from_user.id
    full_name = message.from_user.full_name or "Мастер"
    username = message.from_user.username

    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        result = await db.execute(stmt)
        master = result.scalar_one_or_none()

        if not master:
            master = Master(
                tg_id=tg_id,
                full_name=full_name,
                username=username,
                profession="Мастер услуг",
                deposit_amount=settings.DEFAULT_DEPOSIT_AMOUNT
            )
            db.add(master)
            await db.commit()

    bot_name = settings.BOT_USERNAME.replace("@", "")
    booking_link = f"https://t.me/{bot_name}/app?startapp=master_{tg_id}"

    welcome_text = (
        f"👋 Здравствуйте, <b>{full_name}</b>!\n\n"
        f"🛡 <b>NoShowGuard</b> защищает ваше расписание от неявок.\n"
        f"Клиенты записываются через удобный Telegram Mini App и вносят "
        f"гарантийный депозит <b>{settings.DEFAULT_DEPOSIT_AMOUNT} ₽</b> через СБП.\n\n"
        f"🔗 <b>Ваша ссылка для клиентов:</b>\n"
        f"<code>{booking_link}</code>\n\n"
        f"Разместите ее в шапке профиля или отправляйте клиентам в ЛС."
    )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await message.answer(
        "📱 Вы можете протестировать, как выглядит страница бронирования для ваших клиентов:",
        reply_markup=get_master_link_inline_kb(tg_id)
    )

@router.message(F.text == "🔗 Моя ссылка для записи")
async def handle_get_link(message: Message):
    """Отправка персональной ссылки для записи."""
    tg_id = message.from_user.id
    bot_name = settings.BOT_USERNAME.replace("@", "")
    booking_link = f"https://t.me/{bot_name}/app?startapp=master_{tg_id}"

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

        # Стандартная сетка слотов (по 1.5 часа)
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

            # Проверяем, нет ли уже слота на это время
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

@router.message(F.text == "⚙️ Мой профиль")
async def handle_profile(message: Message):
    """Информация о мастере и настройках депозита."""
    tg_id = message.from_user.id
    async with AsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == tg_id)
        master = (await db.execute(stmt)).scalar_one_or_none()

    if not master:
        await message.answer("Сначала отправьте /start.")
        return

    text = (
        f"⚙️ <b>Профиль мастера:</b>\n\n"
        f"👤 <b>Имя:</b> {master.full_name}\n"
        f"💼 <b>Специализация:</b> {master.profession}\n"
        f"💰 <b>Размер обеспечительного депозита:</b> {master.deposit_amount} ₽\n"
        f"🛡 <b>Юридическое основание:</b> ст. 381.1 ГК РФ (обеспечительный платеж на возмещение ФПР)\n\n"
        f"<i>При явке клиента сумма депозита засчитывается в оплату услуги, а при неявке компенсирует ваш простой.</i>"
    )
    await message.answer(text, parse_mode="HTML")

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
            .options(selectinload(Booking.slot))
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

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        f"ℹ️ Запись #{booking_id} отменена мастером. Слот снова свободен для бронирования.",
        parse_mode="HTML"
    )
    await call.answer("Запись отменена.")

@router.callback_query(F.data.startswith("confirm_visit:"))
async def handle_confirm_visit(call: CallbackQuery):
    """Клиент подтверждает визит через напоминание."""
    booking_id = int(call.data.split(":")[1])
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("✅ <b>Отлично, спасибо!</b>\nМы уведомили мастера, что вы будете вовремя.", parse_mode="HTML")
    await call.answer("Визит подтвержден!")

@router.callback_query(F.data.startswith("cancel_client:"))
async def handle_cancel_client(call: CallbackQuery):
    """Клиент отменяет запись через напоминание."""
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
        master = slot.master if slot else None

        slot.status = SlotStatus.FREE
        slot.locked_until = None
        booking.payment_status = "cancelled_by_client"
        await db.commit()

        # Уведомляем мастера об освободившемся слоте
        if master:
            time_str = slot.start_time.strftime("%d.%m.%Y в %H:%M")
            master_alert = (
                f"🔔 <b>Внимание: клиент отменил запись!</b>\n\n"
                f"Клиент <b>{booking.client_name}</b> отменил бронь на <b>{time_str}</b>.\n"
                f"Слот автоматически освобожден и снова доступен в вашем расписании."
            )
            await safe_send_message(chat_id=master.tg_id, text=master_alert)

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        "ℹ️ Ваша запись отменена. Слот возвращен в расписание мастера.",
        parse_mode="HTML"
    )
    await call.answer("Запись отменена.")

