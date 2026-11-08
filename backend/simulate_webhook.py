import sys
import asyncio
import httpx

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Booking

async def simulate_last_payment():
    async with AsyncSessionLocal() as db:
        stmt = select(Booking).order_by(Booking.id.desc()).limit(1)
        booking = (await db.execute(stmt)).scalar_one_or_none()

        if not booking:
            print("❌ В базе еще нет созданных бронирований. Сначала забронируйте слот в Mini App!")
            return

        booking_id = booking.id
        print(f"Имитируем успешную оплату СБП для брони #{booking_id}...")

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": f"test_pay_{booking_id}",
            "status": "succeeded",
            "paid": True,
            "amount": {
                "value": "300.00",
                "currency": "RUB"
            },
            "metadata": {
                "booking_id": str(booking_id)
            }
        }
    }

    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/api/webhooks/yookassa", json=payload)
        print("Статус ответа вебхука:", res.status_code)
        print("Тело ответа:", res.json())
        print(f"🎉 Бронь #{booking_id} переведена в BOOKED! Депозит зафиксирован.")

if __name__ == "__main__":
    asyncio.run(simulate_last_payment())
