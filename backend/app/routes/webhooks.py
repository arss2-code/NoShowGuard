import logging
from typing import Any
from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Booking, Slot, SlotStatus
from app.services.slot_service import (
    confirm_booking_payment,
    send_booking_confirmed_notifications
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

@router.post("/yookassa")
async def handle_yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Обработчик вебхуков ЮKassa (СБП).
    При payment.succeeded:
      - фиксирует депозит
      - переводит слот в BOOKED
      - отправляет уведомление мастеру и клиенту в Telegram
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception as e:
        logger.error("Некорректный JSON в вебхуке: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_type = body.get("event")
    payment_obj = body.get("object", {})
    metadata = payment_obj.get("metadata", {})
    payment_id = payment_obj.get("id")

    booking_id_raw = metadata.get("booking_id")
    if not booking_id_raw:
        logger.warning("Вебхук ЮKassa получен без booking_id в metadata: %s", payment_obj)
        return {"status": "ignored", "reason": "no booking_id"}

    try:
        booking_id = int(booking_id_raw)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid booking_id format")

    logger.info("Получен вебхук ЮKassa: событие %s для брони #%s", event_type, booking_id)

    if event_type == "payment.succeeded":
        try:
            booking, slot, master = await confirm_booking_payment(
                db=db,
                booking_id=booking_id,
                payment_id=payment_id
            )
        except ValueError as e:
            logger.error("Ошибка при подтверждении брони #%s: %s", booking_id, e)
            return {"status": "error", "message": str(e)}

        # Отправляем мгновенные Push-уведомления мастеру и клиенту
        await send_booking_confirmed_notifications(booking, slot, master)

        return {"status": "ok", "booking_id": booking.id, "slot_status": slot.status.value}

    elif event_type == "payment.canceled":
        # Если клиент отменил оплату или истек срок, возвращаем слот в FREE
        stmt = (
            select(Booking)
            .options(selectinload(Booking.slot))
            .where(Booking.id == booking_id)
        )
        res = await db.execute(stmt)
        booking = res.scalar_one_or_none()
        if booking:
            booking.payment_status = "canceled"
            if booking.slot and booking.slot.status == SlotStatus.PENDING:
                booking.slot.status = SlotStatus.FREE
                booking.slot.locked_until = None
            await db.commit()
        return {"status": "canceled", "booking_id": booking_id}

    return {"status": "ignored", "event": event_type}
