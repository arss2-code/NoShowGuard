import logging
from datetime import timedelta, date, datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Slot, SlotStatus, Booking, Master, utc_now
from app.services.slot_service import release_expired_slots
from app.bot.bot_instance import safe_send_message
from app.bot.keyboards import get_client_reminder_keyboard, get_client_my_bookings_inline_kb
from app.config import settings
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_sent_digests_today: set[tuple[int, date]] = set()

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
                clean_bot = settings.BOT_USERNAME.replace("@", "")
                addr_line = f"📍 <b>Адрес:</b> {b.slot.master.address}\n" if b.slot.master.address else ""
                msg = (
                    f"🔔 <b>Напоминание о записи!</b>\n\n"
                    f"Завтра в <b>{slot_time}</b> у вас запланирован сеанс.\n"
                    f"👤 <b>Мастер:</b> {b.slot.master.full_name}\n"
                    f"💇‍♀️ <b>Услуга:</b> {b.service_title}\n"
                    f"{addr_line}"
                    f"💰 <b>Депозит:</b> {b.deposit_amount} ₽ учтен (доплата на месте: {max(0, b.service_price - b.deposit_amount)} ₽)\n\n"
                    f"Пожалуйста, подтвердите визит или предупредите об отмене.\n\n"
                    f"──────────────\n"
                    f"🛡 <i>Запись через @{clean_bot}</i>"
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
                clean_bot = settings.BOT_USERNAME.replace("@", "")
                addr_line = f"📍 <b>Адрес:</b> {b.slot.master.address}\n" if b.slot.master.address else ""
                msg = (
                    f"⏳ <b>До вашего сеанса осталось 2 часа!</b>\n\n"
                    f"Ждем вас сегодня к <b>{slot_time}</b>.\n"
                    f"👤 <b>Мастер:</b> {b.slot.master.full_name}\n"
                    f"💇‍♀️ <b>Услуга:</b> {b.service_title}\n"
                    f"{addr_line}\n"
                    f"Хорошего вам дня и отличного результата!\n\n"
                    f"──────────────\n"
                    f"🛡 <i>Запись через @{clean_bot}</i>"
                )
                await safe_send_message(
                    chat_id=b.client_tg_id,
                    text=msg,
                    reply_markup=get_client_my_bookings_inline_kb()
                )
            b.reminder_2h_sent = True

        if bookings_24h or bookings_2h:
            await db.commit()

        # 4. Проверка утреннего дайджеста и статуса подписки мастеров
        await process_master_digests(db, now)


async def process_master_digests(db, now: datetime):
    """Отправка персонального утреннего дайджеста мастерам в выбранное время."""
    today = now.date()
    current_hh_mm = now.strftime("%H:%M")

    stmt = select(Master).where(
        and_(
            Master.is_active == True,
            Master.digest_enabled == True
        )
    )
    masters = (await db.execute(stmt)).scalars().all()

    for m in masters:
        if (m.id, today) in _sent_digests_today:
            continue

        # Сверяем время дайджеста (например, "09:00")
        target_time = m.digest_time or "09:00"
        # Даем 5-минутное окно для совпадения с шагом планировщика
        if current_hh_mm == target_time or (now.hour == int(target_time.split(":")[0]) and abs(now.minute - int(target_time.split(":")[1])) <= 2):
            # Собираем статистику на сегодня
            start_today = datetime.combine(today, time.min)
            end_today = datetime.combine(today, time.max)

            slot_stmt = (
                select(Slot)
                .options(selectinload(Slot.booking))
                .where(
                    and_(
                        Slot.master_id == m.id,
                        Slot.start_time >= start_today,
                        Slot.start_time <= end_today
                    )
                )
                .order_by(Slot.start_time.asc())
            )
            slots = (await db.execute(slot_stmt)).scalars().all()
            booked = [s for s in slots if s.status == SlotStatus.BOOKED]
            free = [s for s in slots if s.status == SlotStatus.FREE]

            first_client_text = ""
            if booked:
                first_s = booked[0]
                client_name = first_s.booking.client_name if first_s.booking else "Клиент"
                first_client_text = f"\n👉 <i>Первая запись в {first_s.start_time.strftime('%H:%M')} ({client_name}).</i>"

            text = (
                f"☀️ <b>Доброе утро, {m.full_name}!</b>\n\n"
                f"📅 <b>Ваше расписание на сегодня ({today.strftime('%d.%m.%Y')}):</b>\n"
                f"• Запланировано визитов: <b>{len(booked)}</b> (депозиты гарантированы)\n"
                f"• Свободных окон: <b>{len(free)}</b>"
                f"{first_client_text}\n\n"
                f"Желаем продуктивного дня без отмен и неявок!"
            )

            # Инлайн-кнопка быстрого перехода в кабинет мастера
            master_cabinet_kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 Открыть расписание (TMA)",
                        web_app=WebAppInfo(url=f"{settings.resolved_webapp_url}?role=master&master_id={m.tg_id}")
                    )
                ]
            ])

            await safe_send_message(chat_id=m.tg_id, text=text, reply_markup=master_cabinet_kb)
            _sent_digests_today.add((m.id, today))


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
