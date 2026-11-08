import pytest
from datetime import timedelta
from sqlalchemy import select

from app.models import Master, Slot, SlotStatus, Booking, utc_now

@pytest.mark.asyncio
async def test_client_cancel_more_than_12_hours_refunds(client, db_session):
    """
    Отмена клиентом более чем за 12 часов до записи:
    - Депозит возвращается через ЮKassa СБП (mock/sandbox).
    - Слот освобождается (SlotStatus.FREE) для других клиентов.
    - Статус платежа = cancelled_refunded.
    """
    now = utc_now()
    master = Master(
        tg_id=888001,
        full_name="Мастер Для Возврата",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()

    # Слот через 24 часа (> 12 часов)
    slot = Slot(
        master_id=master.id,
        start_time=now + timedelta(hours=24),
        end_time=now + timedelta(hours=25),
        status=SlotStatus.BOOKED
    )
    db_session.add(slot)
    await db_session.commit()

    booking = Booking(
        slot_id=slot.id,
        client_name="Ольга Возвратная",
        client_phone="+79991112233",
        service_title="Маникюр",
        service_price=2000,
        deposit_amount=300,
        payment_status="succeeded",
        payment_id="mock_pay_123"
    )
    db_session.add(booking)
    await db_session.commit()

    response = await client.post(f"/api/bookings/{booking.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["refunded"] is True
    assert "возвращен" in data["message"].lower()

    # Проверяем базу данных
    await db_session.refresh(slot)
    await db_session.refresh(booking)
    assert slot.status == SlotStatus.FREE
    assert booking.payment_status == "cancelled_refunded"


@pytest.mark.asyncio
async def test_client_cancel_less_than_12_hours_retains_fpr(client, db_session):
    """
    Отмена клиентом менее чем за 12 часов до визита:
    - Депозит не возвращается (ФПР, ст. 381.1 ГК РФ).
    - Слот освобождается (SlotStatus.FREE) для других клиентов.
    - Статус платежа = cancelled_fdr_retained.
    """
    now = utc_now()
    master = Master(
        tg_id=888002,
        full_name="Мастер ФПР",
        deposit_amount=500
    )
    db_session.add(master)
    await db_session.commit()

    # Слот через 3 часа (< 12 часов)
    slot = Slot(
        master_id=master.id,
        start_time=now + timedelta(hours=3),
        end_time=now + timedelta(hours=4),
        status=SlotStatus.BOOKED
    )
    db_session.add(slot)
    await db_session.commit()

    booking = Booking(
        slot_id=slot.id,
        client_name="Иван Опоздавший",
        client_phone="+79992223344",
        service_title="Стрижка Fade",
        service_price=1500,
        deposit_amount=500,
        payment_status="succeeded",
        payment_id="mock_pay_456"
    )
    db_session.add(booking)
    await db_session.commit()

    response = await client.post(f"/api/bookings/{booking.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["refunded"] is False
    assert "381.1 ГК РФ" in data["message"]

    # Проверяем БД
    await db_session.refresh(slot)
    await db_session.refresh(booking)
    assert slot.status == SlotStatus.FREE
    assert booking.payment_status == "cancelled_fdr_retained"


@pytest.mark.asyncio
async def test_master_mark_no_show(client, db_session):
    """
    Мастер нажимает кнопку 'Клиент не пришел' (No-Show):
    - Слот отмечается как COMPLETED.
    - Статус брони = no_show_retained.
    - Депозит зачисляется в спасенную выручку мастера (saved_revenue).
    """
    now = utc_now()
    master = Master(
        tg_id=888003,
        full_name="Мастер NoShow",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()

    slot = Slot(
        master_id=master.id,
        start_time=now - timedelta(hours=1),
        end_time=now,
        status=SlotStatus.BOOKED
    )
    db_session.add(slot)
    await db_session.commit()

    booking = Booking(
        slot_id=slot.id,
        client_name="Неявившийся Гость",
        client_phone="+79993334455",
        service_title="Массаж спины",
        service_price=2500,
        deposit_amount=300,
        payment_status="succeeded",
        payment_id="mock_pay_noshow"
    )
    db_session.add(booking)
    await db_session.commit()

    response = await client.post(f"/api/masters/{master.tg_id}/slots/{slot.id}/no-show")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["saved_deposit"] == 300

    # Проверяем БД
    await db_session.refresh(slot)
    await db_session.refresh(booking)

    assert slot.status == SlotStatus.COMPLETED
    assert booking.payment_status == "no_show_retained"

    # Проверяем дашборд мастера - спасенная выручка должна быть 300 ₽
    dash_res = await client.get(f"/api/masters/{master.tg_id}/dashboard")
    assert dash_res.status_code == 200
    assert dash_res.json()["saved_revenue"] == 300


@pytest.mark.asyncio
async def test_get_my_bookings(client, db_session):
    """
    Получение списка записей клиента по номеру телефона, tg_id или списку booking_ids.
    """
    now = utc_now()
    master = Master(
        tg_id=888004,
        full_name="Мастер Клиентских Записей",
        profession="Колорист",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()

    # Запись 1: через 20 часов (> 12h, can_cancel_with_refund = True)
    slot1 = Slot(
        master_id=master.id,
        start_time=now + timedelta(hours=20),
        end_time=now + timedelta(hours=21),
        status=SlotStatus.BOOKED
    )
    # Запись 2: через 5 часов (< 12h, can_cancel_with_refund = False)
    slot2 = Slot(
        master_id=master.id,
        start_time=now + timedelta(hours=5),
        end_time=now + timedelta(hours=6),
        status=SlotStatus.BOOKED
    )
    db_session.add_all([slot1, slot2])
    await db_session.commit()

    booking1 = Booking(
        slot_id=slot1.id,
        client_name="Анна Тестовая",
        client_phone="+79995556677",
        client_tg_id=555111,
        service_title="Окрашивание AirTouch",
        service_price=6000,
        deposit_amount=300,
        payment_status="succeeded",
        payment_id="mock_pay_1"
    )
    booking2 = Booking(
        slot_id=slot2.id,
        client_name="Анна Тестовая",
        client_phone="+79995556677",
        client_tg_id=555111,
        service_title="Укладка",
        service_price=2000,
        deposit_amount=300,
        payment_status="succeeded",
        payment_id="mock_pay_2"
    )
    db_session.add_all([booking1, booking2])
    await db_session.commit()

    # 1. Поиск по client_phone
    res_phone = await client.get("/api/bookings/my?client_phone=+79995556677")
    assert res_phone.status_code == 200
    items = res_phone.json()
    assert len(items) == 2
    b1_data = next(b for b in items if b["id"] == booking1.id)
    b2_data = next(b for b in items if b["id"] == booking2.id)

    assert b1_data["can_cancel_with_refund"] is True
    assert b1_data["is_active"] is True
    assert b2_data["can_cancel_with_refund"] is False
    assert b2_data["is_active"] is True

    # 2. Поиск по booking_ids (как в localStorage браузера)
    res_ids = await client.get(f"/api/bookings/my?booking_ids={booking1.id}")
    assert res_ids.status_code == 200
    items_ids = res_ids.json()
    assert len(items_ids) == 1
    assert items_ids[0]["id"] == booking1.id
