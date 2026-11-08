import asyncio
from datetime import datetime, date, timedelta, time
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Master, Slot, SlotStatus, Booking, utc_now

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_get_master_slots(client: AsyncClient, db_session: AsyncSession):
    # 1. Создаем мастера
    master = Master(
        tg_id=999001,
        full_name="Анна Мастер",
        profession="Колорист",
        deposit_amount=500
    )
    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    # 2. Создаем свободный слот
    today = date.today()
    slot_start = datetime.combine(today, time(12, 0))
    slot_end = datetime.combine(today, time(13, 30))
    slot = Slot(
        master_id=master.id,
        start_time=slot_start,
        end_time=slot_end,
        status=SlotStatus.FREE
    )
    db_session.add(slot)
    await db_session.commit()

    # 3. Запрашиваем слоты через API
    response = await client.get(f"/api/masters/{master.tg_id}/slots?date={today.isoformat()}")
    assert response.status_code == 200
    slots_data = response.json()
    assert len(slots_data) == 1
    assert slots_data[0]["status"] == "free"
    assert slots_data[0]["id"] == slot.id

@pytest.mark.asyncio
async def test_concurrent_slot_reservation_lock(client: AsyncClient, db_session: AsyncSession):
    """
    Тест защиты от гонки (Race Condition):
    Два одновременных клиента пытаются забронировать один и тот же слот.
    Ровно один должен преуспеть, второй получает 400 Bad Request.
    """
    master = Master(
        tg_id=999002,
        full_name="Иван Барбер",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    today = date.today()
    slot = Slot(
        master_id=master.id,
        start_time=datetime.combine(today, time(15, 0)),
        end_time=datetime.combine(today, time(16, 0)),
        status=SlotStatus.FREE
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    payload_1 = {
        "slot_id": slot.id,
        "client_name": "Клиент Один",
        "client_phone": "+79991112233",
        "client_tg_id": 111111,
        "service_title": "Стрижка",
        "service_price": 2000
    }
    payload_2 = {
        "slot_id": slot.id,
        "client_name": "Клиент Два",
        "client_phone": "+79994445566",
        "client_tg_id": 222222,
        "service_title": "Стрижка",
        "service_price": 2000
    }

    # Выполняем два одновременных POST-запроса на один и тот же slot_id
    res1, res2 = await asyncio.gather(
        client.post("/api/bookings/initiate", json=payload_1),
        client.post("/api/bookings/initiate", json=payload_2)
    )

    statuses = [res1.status_code, res2.status_code]
    assert 200 in statuses, "Один из запросов обязан успешно забронировать слот"
    assert 400 in statuses, "Второй одновременный запрос обязан получить 400 Bad Request"

    # Проверяем ответ отклоненного запроса
    failed_res = res1 if res1.status_code == 400 else res2
    assert "уже занят" in failed_res.json()["detail"]

    # Проверяем, что слот перешел в статус pending_payment
    await db_session.refresh(slot)
    assert slot.status == SlotStatus.PENDING
    assert slot.locked_until is not None

@pytest.mark.asyncio
async def test_expired_pending_slot_can_be_reserved(client: AsyncClient, db_session: AsyncSession):
    """
    Если слот был заблокирован (pending), но 10 минут истекли,
    новый клиент может успешно его зарезервировать.
    """
    master = Master(
        tg_id=999003,
        full_name="Ольга Массажист",
        deposit_amount=500
    )
    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    # Слот со старой блокировкой в прошлом
    slot = Slot(
        master_id=master.id,
        start_time=datetime.combine(date.today(), time(17, 0)),
        end_time=datetime.combine(date.today(), time(18, 0)),
        status=SlotStatus.PENDING,
        locked_until=utc_now() - timedelta(minutes=5)  # Истек 5 минут назад
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    # Старый черновик бронирования
    old_booking = Booking(
        slot_id=slot.id,
        client_name="Бросивший оплату",
        client_phone="+79990000000",
        service_title="Массаж",
        service_price=3000,
        deposit_amount=500,
        payment_status="pending"
    )
    db_session.add(old_booking)
    await db_session.commit()

    # Новый клиент инициирует бронирование
    payload = {
        "slot_id": slot.id,
        "client_name": "Новый Клиент",
        "client_phone": "+79997778899",
        "service_title": "Массаж",
        "service_price": 3000
    }
    response = await client.post("/api/bookings/initiate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["deposit_amount"] == 500
    assert "confirmation_url" in data
