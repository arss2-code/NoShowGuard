import pytest
from datetime import datetime, timedelta, date, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.models import Master, Slot, SlotStatus, Booking, utc_now

@pytest.mark.asyncio
async def test_get_legal_offer(client):
    """Проверка отдачи публичной оферты со ссылками на ст. 381.1 ГК РФ."""
    response = await client.get("/api/public/offer")
    assert response.status_code == 200
    data = response.json()
    assert "381.1 ГК РФ" in data["legal_basis"]
    assert len(data["sections"]) >= 3

@pytest.mark.asyncio
async def test_booking_rejected_without_terms(client, db_session):
    """Попытка бронирования без принятия оферты возвращает 400 Bad Request."""
    now = utc_now()
    master = Master(
        tg_id=777001,
        full_name="Тест Мастер Оферты",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()

    slot = Slot(
        master_id=master.id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, hours=1),
        status=SlotStatus.FREE
    )
    db_session.add(slot)
    await db_session.commit()

    payload = {
        "slot_id": slot.id,
        "client_name": "Несогласный Клиент",
        "client_phone": "+79990001122",
        "service_title": "Стрижка",
        "service_price": 2000,
        "terms_accepted": False
    }
    response = await client.post("/api/bookings/initiate", json=payload)
    assert response.status_code == 400
    assert "оферты" in response.json()["detail"]

@pytest.mark.asyncio
async def test_master_dashboard_and_settings(client, db_session):
    """Проверка получения дашборда мастера, спасенной выручки и обновления настроек дайджеста."""
    now = utc_now()
    master = Master(
        tg_id=888001,
        full_name="Ольга Мастер",
        profession="Колорист",
        deposit_amount=500,
        trial_ends_at=now + timedelta(days=7),
        subscription_tier="trial",
        digest_enabled=True,
        digest_time="09:00"
    )
    db_session.add(master)
    await db_session.commit()

    # Добавляем завершенный слот с удержанным депозитом (No-Show)
    slot1 = Slot(
        master_id=master.id,
        start_time=now - timedelta(days=1),
        end_time=now - timedelta(days=1, hours=1),
        status=SlotStatus.COMPLETED
    )
    db_session.add(slot1)
    await db_session.commit()

    booking_no_show = Booking(
        slot_id=slot1.id,
        client_name="Клиент Прогульщик",
        client_phone="+79998887766",
        service_title="Окрашивание",
        service_price=5000,
        deposit_amount=500,
        payment_status="no_show_retained"
    )
    db_session.add(booking_no_show)
    await db_session.commit()

    # 1. Проверяем дашборд
    dash_res = await client.get(f"/api/masters/{master.tg_id}/dashboard")
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert data["saved_revenue"] == 500
    assert data["trial_days_left"] >= 6
    assert data["subscription_tier"] == "trial"
    assert data["digest_enabled"] is True
    assert data["digest_time"] == "09:00"

    # 2. Обновляем настройки (изменяем депозит и время дайджеста)
    patch_res = await client.patch(
        f"/api/masters/{master.tg_id}/settings",
        json={
            "deposit_amount": 300,
            "digest_enabled": False,
            "digest_time": "10:30"
        }
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()["master"]
    assert updated["deposit_amount"] == 300
    assert updated["digest_enabled"] is False
    assert updated["digest_time"] == "10:30"

@pytest.mark.asyncio
async def test_master_slot_management(client, db_session):
    """Проверка добавления и удаления слотов мастером."""
    now = utc_now().replace(microsecond=0)
    master = Master(
        tg_id=888002,
        full_name="Елена Мастер",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()

    # Добавляем одиночный слот
    start_t = now + timedelta(days=2, hours=10)
    end_t = now + timedelta(days=2, hours=11, minutes=30)
    add_res = await client.post(
        f"/api/masters/{master.tg_id}/slots",
        json={
            "start_time": start_t.isoformat(),
            "end_time": end_t.isoformat()
        }
    )
    assert add_res.status_code == 201
    slot_id = add_res.json()["slot_id"]

    # Проверяем удаление свободного слота
    del_res = await client.delete(f"/api/masters/{master.tg_id}/slots/{slot_id}")
    assert del_res.status_code == 200

    # Заполняем шаблоном стандартных слотов
    template_res = await client.post(
        f"/api/masters/{master.tg_id}/slots/template?target_date={(now + timedelta(days=3)).date().isoformat()}"
    )
    assert template_res.status_code == 200
    assert template_res.json()["created_count"] == 5

@pytest.mark.asyncio
async def test_subscription_checkout_and_simulation(client, db_session):
    """Проверка оформления подписки через СБП и симуляции продления."""
    master = Master(
        tg_id=888003,
        full_name="Светлана Мастер",
        deposit_amount=300
    )
    db_session.add(master)
    await db_session.commit()

    # 1. Запрос на оплату тарифа Старт (490 ₽)
    checkout_res = await client.post(
        f"/api/masters/{master.tg_id}/subscription/checkout",
        json={"tier": "start"}
    )
    assert checkout_res.status_code == 200
    data = checkout_res.json()
    assert data["amount"] == 490
    assert data["tier"] == "start"
    assert "confirmation_url" in data

    # 2. Тестовое продление тарифа
    sim_res = await client.post(
        f"/api/masters/{master.tg_id}/subscription/simulate-success?tier=start"
    )
    assert sim_res.status_code == 200
    assert "успешно активирована" in sim_res.json()["message"]

