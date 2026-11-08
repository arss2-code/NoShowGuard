import logging
from datetime import timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Slot, SlotStatus, Booking, utc_now
from app.services.slot_service import release_expired_slots
from app.bot.bot_instance import safe_send_message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def get_client_reminder_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтверждаю визит",
                callback_data=f"confirm_visit:{booking_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить запись (вернуть слот)",
                callback_data=f"cancel_client:{booking_id}"
            )
        ]
    ])

async def send_appointment_reminders():
    """Фоновая задача: отправляет напоминания за 24ч и 2ч и освобождает просроченные слоты."""
    async with AsyncSessionLocal() as db:
        now = utc_now()

        # 1. Освобождение зависших слотов
        released = await release_expired_slots(db)
        if released > 0:
            logger.info("Scheduler: освобождено %d просроченных PENDING слотов", released)

        # 2. Напоминание за 24 часа
        target_24h = now + timedelta(hours=24)
        stmt_24h = (
            select(Booking)
            .join(Slot, Booking.slot_id == Slot.id)
            .options(selectinload(Booking.slot).selectinload(Slot.master))
            .where(
                and_(
                    Slot.status == SlotStatus.BOOKED,
                    Booking.reminder_24h_sent.is_(False),
                    Slot.start_time <= target_24h,
                    Slot.start_time > now
                )
            )
        )
        bookings_24h = (await db.execute(stmt_24h)).scalars().all()
        for b in bookings_24h:
            if b.client_tg_id and b.slot and b.slot.master:
                slot_time = b.slot.start_time.strftime("%d.%m.%Y в %H:%M")
                msg = (
                    f"🔔 <b>Напоминание о записи!</b>\n\n"
                    f"Завтра в <b>{slot_time}</b> у вас запланирован сеанс.\n"
                    f"👤 <b>Мастер:</b> {b.slot.master.full_name}\n"
                    f"💇‍♀️ <b>Услуга:</b> {b.service_title}\n"
                    f"💰 <b>Депозит:</b> {b.deposit_amount} ₽ учтен (доплата на месте: {max(0, b.service_price - b.deposit_amount)} ₽)\n\n"
                    f"Пожалуйста, подтвердите визит или предупредите об отмене."
                )
                await safe_send_message(
                    chat_id=b.client_tg_id,
                    text=msg,
                    reply_markup=get_client_reminder_keyboard(b.id)
                )
            b.reminder_24h_sent = True

        # 3. Напоминание за 2 часа
        target_2h = now + timedelta(hours=2)
        stmt_2h = (
            select(Booking)
            .join(Slot, Booking.slot_id == Slot.id)
            .options(selectinload(Booking.slot).selectinload(Slot.master))
            .where(
                and_(
                    Slot.status == SlotStatus.BOOKED,
                    Booking.reminder_2h_sent.is_(False),
                    Slot.start_time <= target_2h,
                    Slot.start_time > now
                )
            )
        )
        bookings_2h = (await db.execute(stmt_2h)).scalars().all()
        for b in bookings_2h:
            if b.client_tg_id and b.slot and b.slot.master:
                slot_time = b.slot.start_time.strftime("%H:%M")
                msg = (
                    f"⏳ <b>До вашего сеанса осталось 2 часа!</b>\n\n"
                    f"Ждем вас сегодня к <b>{slot_time}</b>.\n"
                    f"👤 <b>Мастер:</b> {b.slot.master.full_name}\n"
                    f"💇‍♀️ <b>Услуга:</b> {b.service_title}\n\n"
                    f"Хорошего вам дня и отличного результата!"
                )
                await safe_send_message(
                    chat_id=b.client_tg_id,
                    text=msg
                )
            b.reminder_2h_sent = True

        if bookings_24h or bookings_2h:
            await db.commit()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            send_appointment_reminders,
            "interval",
            minutes=2,
            id="appointment_reminders",
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler успешно запущен (интервал: каждые 2 минуты).")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler остановлен.")
