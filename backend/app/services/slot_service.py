from datetime import datetime, date, timedelta, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from app.models import Slot, SlotStatus, Booking, Master, utc_now
from app.config import settings

async def release_expired_slots(db: AsyncSession) -> int:
    """Освобождает слоты, у которых истекло время ожидания оплаты (10 мин)."""
    now = utc_now()
    stmt = (
        update(Slot)
        .where(
            and_(
                Slot.status == SlotStatus.PENDING,
                Slot.locked_until.isnot(None),
                Slot.locked_until < now
            )
        )
        .values(
            status=SlotStatus.FREE,
            locked_until=None
        )
    )
    result = await db.execute(stmt)
    if result.rowcount > 0:
        await db.commit()
    return result.rowcount

async def get_master_slots_by_date(
    db: AsyncSession,
    master_tg_id: int,
    target_date: date
) -> list[Slot]:
    """Возвращает свободные слоты мастера на указанную дату."""
    await release_expired_slots(db)

    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)

    stmt = (
        select(Slot)
        .join(Master, Slot.master_id == Master.id)
        .where(
            and_(
                Master.tg_id == master_tg_id,
                Slot.start_time >= start_dt,
                Slot.start_time <= end_dt,
                Slot.status == SlotStatus.FREE
            )
        )
        .order_by(Slot.start_time.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def reserve_slot_for_payment(
    db: AsyncSession,
    slot_id: int,
    client_name: str,
    client_phone: str,
    client_tg_id: int | None,
    service_title: str,
    service_price: int,
    deposit_amount: int,
    terms_accepted: bool = True
) -> Booking:
    """
    Атомарно блокирует слот на время оплаты с защитой от состояния гонки (Race Condition).
    Работает одинаково надежно как в PostgreSQL, так и в SQLite WAL.
    """
    now = utc_now()
    lock_expires = now + timedelta(minutes=settings.DEPOSIT_LOCK_MINUTES)

    # 1. Атомарный UPDATE: переводит слот в PENDING только если он FREE или просрочен PENDING
    lock_stmt = (
        update(Slot)
        .where(
            Slot.id == slot_id,
            or_(
                Slot.status == SlotStatus.FREE,
                and_(
                    Slot.status == SlotStatus.PENDING,
                    Slot.locked_until.isnot(None),
                    Slot.locked_until < now
                )
            )
        )
        .values(
            status=SlotStatus.PENDING,
            locked_until=lock_expires
        )
    )
    lock_result = await db.execute(lock_stmt)

    if lock_result.rowcount == 0:
        # Проверяем, существует ли слот вообще
        check_stmt = select(Slot.id).where(Slot.id == slot_id)
        slot_exists = (await db.execute(check_stmt)).scalar_one_or_none()
        if not slot_exists:
            raise ValueError("Слот не найден")
        raise ValueError("Слот уже занят или оформляется другим клиентом")

    # 2. Удаляем старые незавершенные черновики бронирования для этого слота (если были)
    await db.execute(delete(Booking).where(Booking.slot_id == slot_id))

    # 3. Создаем черновик бронирования
    booking = Booking(
        slot_id=slot_id,
        client_name=client_name,
        client_phone=client_phone,
        client_tg_id=client_tg_id,
        service_title=service_title,
        service_price=service_price,
        deposit_amount=deposit_amount,
        payment_status="pending",
        terms_accepted=terms_accepted,
        terms_accepted_at=now
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking

async def confirm_booking_payment(
    db: AsyncSession,
    booking_id: int,
    payment_id: str | None = None
) -> tuple[Booking, Slot, Master]:
    """
    Подтверждает бронь после успешной оплаты в ЮKassa.
    Переводит Slot в BOOKED, Booking в succeeded.
    """
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.slot).selectinload(Slot.master)
        )
        .where(Booking.id == booking_id)
    )
    result = await db.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise ValueError(f"Бронирование #{booking_id} не найдено")

    slot = booking.slot
    if not slot:
        raise ValueError(f"Слот для бронирования #{booking_id} не найден")

    master = slot.master

    # Переводим статусы
    slot.status = SlotStatus.BOOKED
    slot.locked_until = None

    booking.payment_status = "succeeded"
    if payment_id:
        booking.payment_id = payment_id

    await db.commit()
    await db.refresh(booking)
    await db.refresh(slot)
    return booking, slot, master

async def process_client_cancellation(
    db: AsyncSession,
    booking_id: int
) -> dict:
    """
    Единая логика отмены бронирования клиентом с соблюдением правила 12 часов:
    - >= 12 часов: 100% автовозврат депозита через ЮKassa СБП, слот -> FREE, cancelled_refunded.
    - < 12 часов: удержание депозита как ФПР (ст. 381.1 ГК РФ), слот -> FREE, cancelled_fdr_retained.
    Отправляет соответствующие Telegram Push-уведомления мастеру.
    """
    from app.services.payment import payment_service
    from app.bot.bot_instance import safe_send_message

    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.slot).selectinload(Slot.master)
        )
        .where(Booking.id == booking_id)
    )
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if not booking:
        raise ValueError("Бронирование не найдено")

    slot = booking.slot
    if not slot:
        raise ValueError("Слот не найден")

    if slot.status not in [SlotStatus.BOOKED, SlotStatus.PENDING]:
        raise ValueError("Данная запись уже отменена или завершена")

    master = slot.master
    now = utc_now()
    hours_left = (slot.start_time - now).total_seconds() / 3600.0
    slot_time_str = slot.start_time.strftime("%d.%m.%Y в %H:%M")

    # Слот всегда возвращается в расписание мастера для других клиентов
    slot.status = SlotStatus.FREE
    slot.locked_until = None

    if hours_left >= 12.0:
        # Автовозврат через ЮKassa
        refund_info = payment_service.refund_deposit(
            payment_id=booking.payment_id,
            amount=booking.deposit_amount,
            booking_id=booking.id
        )
        booking.payment_status = "cancelled_refunded"
        await db.commit()

        if master:
            master_alert = (
                f"ℹ️ <b>Клиент отменил запись</b>\n\n"
                f"Клиент <b>{booking.client_name}</b> отменил бронь на <b>{slot_time_str}</b>.\n"
                f"Отмена произведена более чем за 12 часов ({round(hours_left, 1)} ч. до визита).\n"
                f"Депозит {booking.deposit_amount} ₽ возвращен клиенту по СБП.\n"
                f"Слот автоматически вернулся в ваше расписание!"
            )
            await safe_send_message(chat_id=master.tg_id, text=master_alert)

        return {
            "success": True,
            "refunded": True,
            "hours_left": round(hours_left, 1),
            "refund_info": refund_info,
            "booking": booking,
            "slot": slot,
            "master": master,
            "message": f"Запись отменена. Гарантийный депозит {booking.deposit_amount} ₽ автоматически возвращен на ваш счет СБП."
        }
    else:
        # Депозит удерживается в пользу мастера (ст. 381.1 ГК РФ)
        booking.payment_status = "cancelled_fdr_retained"
        await db.commit()

        if master:
            master_alert = (
                f"⚠️ <b>Внимание: поздняя отмена записи!</b>\n\n"
                f"Клиент <b>{booking.client_name}</b> отменил бронь на <b>{slot_time_str}</b> менее чем за 12 часов ({round(hours_left, 1)} ч. до визита).\n"
                f"По ст. 381.1 ГК РФ сумма депозита <b>{booking.deposit_amount} ₽</b> удержана в вашу пользу как компенсация расходов (ФПР).\n"
                f"Слот освобожден и снова доступен для новых клиентов!"
            )
            await safe_send_message(chat_id=master.tg_id, text=master_alert)

        return {
            "success": True,
            "refunded": False,
            "hours_left": round(hours_left, 1),
            "booking": booking,
            "slot": slot,
            "master": master,
            "message": f"Запись отменена. До начала оставалось менее 12 часов ({round(hours_left, 1)} ч.), поэтому в соответствии со ст. 381.1 ГК РФ и офертой депозит {booking.deposit_amount} ₽ удержан в пользу мастера."
        }

async def send_booking_confirmed_notifications(
    booking: Booking,
    slot: Slot,
    master: Master
) -> None:
    """Мгновенные Telegram Push-уведомления мастеру и клиенту при успешном внесении депозита."""
    from app.bot.bot_instance import safe_send_message
    from app.bot.keyboards import get_booking_action_keyboard, get_client_my_bookings_inline_kb

    start_time_str = slot.start_time.strftime("%d.%m.%Y в %H:%M")
    remaining_price = max(0, booking.service_price - booking.deposit_amount)

    # 1. Пуш мастеру с инлайн-кнопками управления
    master_msg = (
        f"✅ <b>Новая запись с гарантией!</b>\n\n"
        f"Клиент <b>{booking.client_name}</b> внес депозит <b>{booking.deposit_amount} ₽</b> по СБП.\n\n"
        f"📅 <b>Дата и время:</b> {start_time_str}\n"
        f"💇‍♀️ <b>Услуга:</b> {booking.service_title}\n"
        f"💰 <b>Стоимость:</b> {booking.service_price} ₽ (к доплате на месте: {remaining_price} ₽)\n"
        f"📞 <b>Телефон:</b> {booking.client_phone}\n\n"
        f"<i>Слот зафиксирован. При неявке депозит компенсирует простой графика.</i>"
    )
    await safe_send_message(
        chat_id=master.tg_id,
        text=master_msg,
        reply_markup=get_booking_action_keyboard(booking.id)
    )

    # 2. Подтверждение клиенту с кнопкой WebApp «Мои записи»
    if booking.client_tg_id:
        clean_bot = settings.BOT_USERNAME.replace("@", "")
        client_msg = (
            f"✅ <b>Ваша запись успешно подтверждена!</b>\n\n"
            f"👤 <b>Мастер:</b> {master.full_name}\n"
            f"📅 <b>Дата и время:</b> {start_time_str}\n"
            f"💇‍♀️ <b>Услуга:</b> {booking.service_title}\n"
            f"🛡 <b>Гарантийный депозит:</b> {booking.deposit_amount} ₽ внесен через СБП.\n"
            f"💵 <b>К оплате на месте:</b> {remaining_price} ₽\n\n"
            f"Ждем вас вовремя! Накануне сеанса мы пришлем напоминание.\n\n"
            f"──────────────\n"
            f"🛡 <i>Запись оформлена через @{clean_bot} — защита расписания от неявок по СБП.</i>"
        )
        await safe_send_message(
            chat_id=booking.client_tg_id,
            text=client_msg,
            reply_markup=get_client_my_bookings_inline_kb()
        )
