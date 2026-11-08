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
    if not payload.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо согласиться с условиями публичной оферты и обеспечительного платежа (ст. 381.1 ГК РФ)"
        )

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

    if slot.master and slot.master.subscription_tier == "expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Запись к мастеру временно приостановлена (требуется продление тарифа)"
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
            deposit_amount=deposit_amount,
            terms_accepted=payload.terms_accepted
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


@router.post("/bookings/{booking_id}/confirm", response_model=BookingStatusResponse)
async def confirm_booking_endpoint(
    booking_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Подтверждение оплаты депозита клиентом (перевод слота в BOOKED)."""
    from app.services.slot_service import confirm_booking_payment, send_booking_confirmed_notifications
    try:
        booking, slot, master = await confirm_booking_payment(db, booking_id, "mock_confirmed_payment")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Отправляем мгновенные Telegram-уведомления мастеру и клиенту
    await send_booking_confirmed_notifications(booking, slot, master)

    return BookingStatusResponse(
        booking_id=booking.id,
        slot_id=booking.slot_id,
        status=slot.status.value,
        payment_status=booking.payment_status,
        client_name=booking.client_name,
        service_title=booking.service_title,
        deposit_amount=booking.deposit_amount,
        start_time=slot.start_time
    )


@router.get("/bookings/my")
async def get_my_bookings(
    client_tg_id: int | None = Query(None, description="Telegram ID клиента"),
    client_phone: str | None = Query(None, description="Номер телефона клиента"),
    booking_ids: str | None = Query(None, description="Список ID броней через запятую"),
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает список бронирований конкретного клиента (активных и истории).
    Ищет по client_tg_id, телефону или списку ID броней.
    """
    from app.models import utc_now, SlotStatus
    now = utc_now()

    conditions = []
    if client_tg_id and client_tg_id != 999999:
        conditions.append(Booking.client_tg_id == client_tg_id)

    if client_phone:
        clean_phone = "".join(filter(str.isdigit, client_phone))
        if len(clean_phone) >= 10:
            conditions.append(Booking.client_phone.like(f"%{clean_phone[-10:]}%"))

    if booking_ids:
        parsed_ids = [int(x.strip()) for x in booking_ids.split(",") if x.strip().isdigit()]
        if parsed_ids:
            conditions.append(Booking.id.in_(parsed_ids))

    if not conditions:
        return []

    from sqlalchemy import or_
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.slot).selectinload(Slot.master)
        )
        .where(or_(*conditions))
        .order_by(Booking.id.desc())
    )
    bookings_db = (await db.execute(stmt)).scalars().all()

    results = []
    for b in bookings_db:
        if not b.slot:
            continue

        master = b.slot.master
        hours_left = (b.slot.start_time - now).total_seconds() / 3600.0
        can_refund = hours_left >= 12.0
        is_active = (
            b.slot.status in [SlotStatus.BOOKED, SlotStatus.PENDING]
            and b.slot.start_time > now
            and b.payment_status in ["pending", "succeeded"]
        )

        results.append({
            "id": b.id,
            "slot_id": b.slot_id,
            "master_name": master.full_name if master else "Мастер",
            "master_profession": master.profession if master else "Специалист",
            "service_title": b.service_title,
            "service_price": b.service_price,
            "deposit_amount": b.deposit_amount,
            "start_time": b.slot.start_time.isoformat(),
            "end_time": b.slot.end_time.isoformat(),
            "slot_status": b.slot.status.value,
            "payment_status": b.payment_status,
            "hours_until_start": round(hours_left, 1),
            "can_cancel_with_refund": can_refund,
            "is_active": is_active,
            "created_at": b.created_at.isoformat()
        })

    return results


@router.post("/bookings/{booking_id}/cancel")
async def cancel_client_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Отмена бронирования клиентом с проверкой правила 12 часов:
    - >= 12 часов: возврат депозита по СБП ЮKassa, слот -> FREE, cancelled_refunded.
    - < 12 часов: удержание депозита как ФПР (ст. 381.1 ГК РФ), слот -> FREE, cancelled_fdr_retained.
    """
    from app.services.slot_service import process_client_cancellation
    try:
        result = await process_client_cancellation(db, booking_id)
        # Исключаем объекты SQLAlchemy из ответа для сериализации
        return {
            "success": result["success"],
            "refunded": result["refunded"],
            "hours_left": result["hours_left"],
            "refund_info": result.get("refund_info"),
            "message": result["message"]
        }
    except ValueError as e:
        err_msg = str(e)
        if "не найдено" in err_msg or "не найден" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)




@router.get("/public/offer")
async def get_legal_offer():
    """Публичная оферта и правила обеспечительного платежа (ст. 381.1 ГК РФ)."""
    return {
        "title": "Условия бронирования и правила обеспечительного платежа",
        "legal_basis": "ст. 381.1 ГК РФ, ст. 32 Закона РФ «О защите прав потребителей», ст. 782 ГК РФ",
        "sections": [
            {
                "heading": "1. Правовая природа обеспечительного платежа",
                "text": "Вносимая клиентом сумма является обеспечительным платежом в соответствии со статьей 381.1 Гражданского кодекса РФ, вносимым в обеспечение обязательства клиента явиться на выбранный сеанс в назначенное время."
            },
            {
                "heading": "2. Зачет суммы при явке",
                "text": "При надлежащем исполнении обязательства (своевременная явка на сеанс) обеспечительный платеж на 100% засчитывается в счет оплаты стоимости оказываемой мастером услуги. Клиент доплачивает лишь остаток стоимости непосредственно на месте."
            },
            {
                "heading": "3. Правила отмены и компенсация расходов",
                "text": "Клиент вправе отменить запись не позднее чем за 12 часов до начала сеанса с полным сохранением или возвратом обеспечительного платежа. В случае неявки клиента либо отмены записи менее чем за 12 часов, сумма обеспечительного платежа удерживается исполнителем в качестве возмещения фактически понесенных расходов (ФПР), связанных с бронированием рабочего места, подготовкой материалов и простоем графика (ст. 32 ЗоЗПП, ст. 782 ГК РФ)."
            },
            {
                "heading": "4. Безопасность расчетов",
                "text": "Все расчеты осуществляются через Систему быстрых платежей (СБП) Банка России по защищенному протоколу с мгновенным формированием фискального/электронного подтверждения."
            }
        ]
    }

