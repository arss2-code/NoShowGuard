from datetime import datetime, date, timedelta, time
from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import Message, User, Chat, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Master, Slot, SlotStatus, Booking, utc_now
from app.bot.handlers import (
    handle_start,
    handle_create_standard_slots,
    handle_today_slots,
    handle_no_show_callback,
    handle_confirm_visit,
    handle_cancel_client
)
from tests.conftest import TestAsyncSessionLocal

def create_mock_message(user_id: int, text: str, full_name: str = "Иван Мастер") -> Message:
    msg = MagicMock(spec=Message)
    msg.from_user = User(
        id=user_id,
        is_bot=False,
        first_name=full_name,
        last_name="",
        username="ivan_master"
    )
    msg.chat = Chat(id=user_id, type="private")
    msg.text = text
    msg.answer = AsyncMock()
    return msg

@pytest.mark.asyncio
async def test_bot_start_handler():
    msg = create_mock_message(user_id=1234567, text="/start", full_name="Алексей Мастер")
    await handle_start(msg)

    # Проверяем, что мастер создался в БД
    async with TestAsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == 1234567)
        master = (await db.execute(stmt)).scalar_one_or_none()
        assert master is not None
        assert master.full_name == "Алексей Мастер"
        assert master.deposit_amount == 300

    # Проверяем, что бот ответил сообщением со ссылкой
    assert msg.answer.call_count >= 1
    args, kwargs = msg.answer.call_args_list[0]
    assert "NoShowGuard" in args[0]
    assert "startapp=master_1234567" in args[0]

@pytest.mark.asyncio
async def test_bot_create_standard_slots():
    # Создаем мастера
    async with TestAsyncSessionLocal() as db:
        master = Master(tg_id=7654321, full_name="Мария Косметолог")
        db.add(master)
        await db.commit()

    msg = create_mock_message(user_id=7654321, text="➕ Создать слоты на сегодня")
    await handle_create_standard_slots(msg)

    # Проверяем, что слоты создались
    async with TestAsyncSessionLocal() as db:
        stmt = select(Slot).join(Master).where(Master.tg_id == 7654321)
        slots = (await db.execute(stmt)).scalars().all()
        assert len(slots) == 5  # 5 стандартных слотов

    assert msg.answer.call_count == 1
    assert "Успешно добавлено <b>5</b> свободных слотов" in msg.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_bot_no_show_callback():
    # Создаем тестовую запись
    async with TestAsyncSessionLocal() as db:
        master = Master(tg_id=888999, full_name="Артур Барбер")
        db.add(master)
        await db.flush()

        slot = Slot(
            master_id=master.id,
            start_time=datetime.combine(date.today(), time(10, 0)),
            end_time=datetime.combine(date.today(), time(11, 0)),
            status=SlotStatus.BOOKED
        )
        db.add(slot)
        await db.flush()

        booking = Booking(
            slot_id=slot.id,
            client_name="Неявившийся",
            client_phone="+79991234567",
            service_title="Стрижка",
            service_price=1500,
            deposit_amount=300,
            payment_status="succeeded"
        )
        db.add(booking)
        await db.commit()
        booking_id = booking.id

    call = MagicMock(spec=CallbackQuery)
    call.data = f"no_show:{booking_id}"
    call.answer = AsyncMock()
    call.message = MagicMock(spec=Message)
    call.message.answer = AsyncMock()
    call.message.edit_reply_markup = AsyncMock()

    await handle_no_show_callback(call)

    # Проверяем обновление статуса в базе
    async with TestAsyncSessionLocal() as db:
        stmt = select(Booking).where(Booking.id == booking_id)
        b = (await db.execute(stmt)).scalar_one_or_none()
        assert b.payment_status == "no_show_retained"

    assert call.answer.called
    assert call.message.edit_reply_markup.called
    assert "Зафиксирована неявка" in call.message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_bot_start_with_master_link_for_client():
    """Клиент переходит по ссылке /start master_1234567."""
    async with TestAsyncSessionLocal() as db:
        master = Master(
            tg_id=9876543,
            full_name="Ольга Маникюр",
            profession="Мастер ногтевого сервиса",
            deposit_amount=500
        )
        db.add(master)
        await db.commit()

    # Клиент с tg_id 111222 пишет боту
    msg = create_mock_message(user_id=111222, text="/start master_9876543", full_name="Екатерина Клиент")
    await handle_start(msg)

    # Проверяем, что клиент НЕ создался в таблице Master
    async with TestAsyncSessionLocal() as db:
        stmt = select(Master).where(Master.tg_id == 111222)
        client_as_master = (await db.execute(stmt)).scalar_one_or_none()
        assert client_as_master is None

    # Проверяем, что бот ответил карточкой мастера
    assert msg.answer.call_count >= 1
    first_reply = msg.answer.call_args_list[0][0][0]
    assert "Ольга Маникюр" in first_reply
    assert "500 ₽" in first_reply
    assert "ст. 381.1 ГК РФ" in first_reply

@pytest.mark.asyncio
async def test_bot_cancel_client_rule_12h():
    """Проверка отмены записи клиентом через кнопку бота с правилом 12 часов."""
    now = utc_now()

    # 1. Запись через 20 часов (>= 12ч -> автовозврат)
    async with TestAsyncSessionLocal() as db:
        master = Master(tg_id=444555, full_name="Сергей Массаж")
        db.add(master)
        await db.flush()

        slot_future = Slot(
            master_id=master.id,
            start_time=now + timedelta(hours=20),
            end_time=now + timedelta(hours=21),
            status=SlotStatus.BOOKED
        )
        db.add(slot_future)
        await db.flush()

        booking_future = Booking(
            slot_id=slot_future.id,
            client_name="Клиент Своевременный",
            client_phone="+79990001122",
            service_title="Массаж",
            service_price=3000,
            deposit_amount=300,
            payment_status="succeeded"
        )
        db.add(booking_future)
        await db.commit()
        booking_future_id = booking_future.id

    call1 = MagicMock(spec=CallbackQuery)
    call1.data = f"cancel_client:{booking_future_id}"
    call1.answer = AsyncMock()
    call1.message = MagicMock(spec=Message)
    call1.message.answer = AsyncMock()
    call1.message.edit_reply_markup = AsyncMock()

    await handle_cancel_client(call1)

    async with TestAsyncSessionLocal() as db:
        stmt = select(Booking).where(Booking.id == booking_future_id)
        b1 = (await db.execute(stmt)).scalar_one_or_none()
        assert b1.payment_status == "cancelled_refunded"

        stmt_slot = select(Slot).where(Slot.id == b1.slot_id)
        s1 = (await db.execute(stmt_slot)).scalar_one_or_none()
        assert s1.status == SlotStatus.FREE

    assert "автоматически возвращен" in call1.message.answer.call_args[0][0]

    # 2. Запись через 4 часа (< 12ч -> удержание депозита как ФПР по ст. 381.1 ГК РФ)
    async with TestAsyncSessionLocal() as db:
        slot_late = Slot(
            master_id=master.id,
            start_time=now + timedelta(hours=4),
            end_time=now + timedelta(hours=5),
            status=SlotStatus.BOOKED
        )
        db.add(slot_late)
        await db.flush()

        booking_late = Booking(
            slot_id=slot_late.id,
            client_name="Клиент Опоздавший",
            client_phone="+79993334455",
            service_title="Массаж спины",
            service_price=2500,
            deposit_amount=300,
            payment_status="succeeded"
        )
        db.add(booking_late)
        await db.commit()
        booking_late_id = booking_late.id

    call2 = MagicMock(spec=CallbackQuery)
    call2.data = f"cancel_client:{booking_late_id}"
    call2.answer = AsyncMock()
    call2.message = MagicMock(spec=Message)
    call2.message.answer = AsyncMock()
    call2.message.edit_reply_markup = AsyncMock()

    await handle_cancel_client(call2)

    async with TestAsyncSessionLocal() as db:
        stmt = select(Booking).where(Booking.id == booking_late_id)
        b2 = (await db.execute(stmt)).scalar_one_or_none()
        assert b2.payment_status == "cancelled_fdr_retained"

        stmt_slot2 = select(Slot).where(Slot.id == b2.slot_id)
        s2 = (await db.execute(stmt_slot2)).scalar_one_or_none()
        assert s2.status == SlotStatus.FREE

    assert "ст. 381.1 ГК РФ" in call2.message.answer.call_args[0][0]
    assert "удержан в пользу мастера" in call2.message.answer.call_args[0][0]
