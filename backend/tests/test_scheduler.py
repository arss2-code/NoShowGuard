from datetime import datetime, timedelta, date, time
import pytest
from sqlalchemy import select
from app.models import Master, Slot, SlotStatus, Booking, utc_now
from app.services.scheduler import send_appointment_reminders
from tests.conftest import TestAsyncSessionLocal

@pytest.mark.asyncio
async def test_scheduler_reminders_and_slot_release():
    now = utc_now()
    async with TestAsyncSessionLocal() as db:
        master = Master(tg_id=555001, full_name="Мастер Напоминаний")
        db.add(master)
        await db.flush()

        # 1. Запись на завтра (через 23 часа)
        slot_24h = Slot(
            master_id=master.id,
            start_time=now + timedelta(hours=23),
            end_time=now + timedelta(hours=24),
            status=SlotStatus.BOOKED
        )
        db.add(slot_24h)
        await db.flush()

        booking_24h = Booking(
            slot_id=slot_24h.id,
            client_tg_id=444001,
            client_name="Клиент 24ч",
            client_phone="+79001234567",
            service_title="Стрижка",
            service_price=2000,
            deposit_amount=300,
            payment_status="succeeded",
            reminder_24h_sent=False
        )
        db.add(booking_24h)

        # 2. Просроченный PENDING слот
        expired_slot = Slot(
            master_id=master.id,
            start_time=now + timedelta(hours=5),
            end_time=now + timedelta(hours=6),
            status=SlotStatus.PENDING,
            locked_until=now - timedelta(minutes=5)
        )
        db.add(expired_slot)

        await db.commit()
        booking_id = booking_24h.id
        expired_slot_id = expired_slot.id

    # Запускаем проверку планировщика
    await send_appointment_reminders()

    # Проверяем результаты
    async with TestAsyncSessionLocal() as db:
        stmt1 = select(Booking).where(Booking.id == booking_id)
        b = (await db.execute(stmt1)).scalar_one()
        assert b.reminder_24h_sent is True

        stmt2 = select(Slot).where(Slot.id == expired_slot_id)
        s = (await db.execute(stmt2)).scalar_one()
        assert s.status == SlotStatus.FREE
        assert s.locked_until is None
