from datetime import datetime, date, timedelta, time
from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import Message, User, Chat, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Master, Slot, SlotStatus, Booking
from app.bot.handlers import (
    handle_start,
    handle_create_standard_slots,
    handle_today_slots,
    handle_no_show_callback
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
