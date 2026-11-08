from datetime import datetime, date, timedelta, time
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Master, Slot, SlotStatus, Booking, utc_now

@pytest.mark.asyncio
async def test_yookassa_webhook_payment_succeeded(client: AsyncClient, db_session: AsyncSession):
    """Тест успешного вебхука payment.succeeded: слот становится BOOKED, статус succeeded."""
    # 1. Создаем мастера
    master = Master(
        tg_id=777001,
        full_name="Елена Маникюр",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    # 2. Создаем слот в статусе PENDING
    slot = Slot(
        master_id=master.id,
        start_time=datetime.combine(date.today(), time(14, 0)),
        end_time=datetime.combine(date.today(), time(15, 30)),
        status=SlotStatus.PENDING,
        locked_until=utc_now() + timedelta(minutes=10)
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    # 3. Создаем бронь в статусе pending
    booking = Booking(
        slot_id=slot.id,
        client_tg_id=888001,
        client_name="Мария",
        client_phone="+79161234567",
        service_title="Маникюр с покрытием",
        service_price=2500,
        deposit_amount=300,
        payment_status="pending"
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)

    # 4. Имитируем входящий вебхук от ЮKassa
    webhook_payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": "22d6d577-000f-5000-9000-145f6df21d6f",
            "status": "succeeded",
            "paid": True,
            "amount": {
                "value": "300.00",
                "currency": "RUB"
            },
            "metadata": {
                "booking_id": str(booking.id)
            }
        }
    }

    response = await client.post("/api/webhooks/yookassa", json=webhook_payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["slot_status"] == "booked"

    # 5. Проверяем состояние в базе данных
    await db_session.refresh(slot)
    await db_session.refresh(booking)

    assert slot.status == SlotStatus.BOOKED
    assert slot.locked_until is None
    assert booking.payment_status == "succeeded"
    assert booking.payment_id == "22d6d577-000f-5000-9000-145f6df21d6f"

@pytest.mark.asyncio
async def test_yookassa_webhook_payment_canceled(client: AsyncClient, db_session: AsyncSession):
    """Тест отмены платежа payment.canceled: слот возвращается в статус FREE."""
    master = Master(
        tg_id=777002,
        full_name="Сергей Тренер",
        deposit_amount=500
    )
    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    slot = Slot(
        master_id=master.id,
        start_time=datetime.combine(date.today(), time(18, 0)),
        end_time=datetime.combine(date.today(), time(19, 0)),
        status=SlotStatus.PENDING,
        locked_until=utc_now() + timedelta(minutes=10)
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    booking = Booking(
        slot_id=slot.id,
        client_name="Алексей",
        client_phone="+79261234567",
        service_title="Персональная тренировка",
        service_price=3500,
        deposit_amount=500,
        payment_status="pending"
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)

    webhook_payload = {
        "type": "notification",
        "event": "payment.canceled",
        "object": {
            "id": "cancel_id_123",
            "status": "canceled",
            "metadata": {
                "booking_id": str(booking.id)
            }
        }
    }

    response = await client.post("/api/webhooks/yookassa", json=webhook_payload)
    assert response.status_code == 200

    await db_session.refresh(slot)
    await db_session.refresh(booking)

    # Слот вернулся в FREE
    assert slot.status == SlotStatus.FREE
    assert slot.locked_until is None
    assert booking.payment_status == "canceled"
