from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Master, Slot, Booking
from app.schemas import (
    MasterResponse,
    SlotResponse,
    BookingInitiateRequest,
    BookingInitiateResponse,
    BookingStatusResponse
)
from app.services.slot_service import (
    get_master_slots_by_date,
    reserve_slot_for_payment
)
from app.services.payment import payment_service

router = APIRouter(prefix="/api", tags=["Public API"])

@router.get("/masters/{tg_id}", response_model=MasterResponse)
async def get_master_profile(
    tg_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение публичной информации о мастере для Mini App."""
    stmt = select(Master).where(Master.tg_id == tg_id)
    result = await db.execute(stmt)
    master = result.scalar_one_or_none()
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мастер не найден"
        )
    return master

@router.get("/masters/{tg_id}/slots", response_model=list[SlotResponse])
async def get_master_slots(
    tg_id: int,
    date_query: date = Query(..., alias="date", description="Дата в формате YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение доступных слотов мастера на выбранный день.
    Автоматически очищает просроченные брони (статус PENDING > 10 минут).
    """
    stmt = select(Master).where(Master.tg_id == tg_id)
    master = (await db.execute(stmt)).scalar_one_or_none()
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мастер с указанным Telegram ID не найден"
        )

    slots = await get_master_slots_by_date(db, tg_id, date_query)
    return slots

@router.post("/bookings/initiate", response_model=BookingInitiateResponse)
async def initiate_booking(
    payload: BookingInitiateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Инициация бронирования:
    1. Блокирует слот на 10 минут (Pessimistic Lock).
    2. Создает платеж на сумму депозита через СБП ЮKassa.
    3. Возвращает ссылку на оплату для мобильного банка.
    """
    # Получаем информацию о слоте и мастере для определения депозита
    slot_stmt = (
        select(Slot)
        .options(selectinload(Slot.master))
        .where(Slot.id == payload.slot_id)
    )
    result = await db.execute(slot_stmt)
    slot = result.scalar_one_or_none()

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выбранный временной слот не существует"
        )

    deposit_amount = slot.master.deposit_amount if slot.master else 300

    try:
        # Резервируем слот
        booking = await reserve_slot_for_payment(
            db=db,
            slot_id=payload.slot_id,
            client_name=payload.client_name,
            client_phone=payload.client_phone,
            client_tg_id=payload.client_tg_id,
            service_title=payload.service_title,
            service_price=payload.service_price,
            deposit_amount=deposit_amount
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Создаем платеж в ЮKassa через СБП
    payment_info = payment_service.create_sbp_payment(
        booking_id=booking.id,
        deposit_amount=deposit_amount,
        service_title=payload.service_title,
        client_phone=payload.client_phone
    )

    # Привязываем payment_id к брони
    booking.payment_id = payment_info.get("payment_id")
    await db.commit()
    await db.refresh(booking)

    return BookingInitiateResponse(
        booking_id=booking.id,
        slot_id=booking.slot_id,
        deposit_amount=booking.deposit_amount,
        payment_id=booking.payment_id,
        confirmation_url=payment_info.get("confirmation_url", ""),
        status=booking.payment_status
    )

@router.get("/bookings/{booking_id}/status", response_model=BookingStatusResponse)
async def get_booking_status(
    booking_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Проверка текущего статуса бронирования и платежа."""
    stmt = (
        select(Booking)
        .options(selectinload(Booking.slot))
        .where(Booking.id == booking_id)
    )
    result = await db.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бронирование не найдено"
        )

    slot_status = booking.slot.status.value if booking.slot else "unknown"
    start_time = booking.slot.start_time if booking.slot else None

    return BookingStatusResponse(
        booking_id=booking.id,
        slot_id=booking.slot_id,
        status=slot_status,
        payment_status=booking.payment_status,
        client_name=booking.client_name,
        service_title=booking.service_title,
        deposit_amount=booking.deposit_amount,
        start_time=start_time
    )
