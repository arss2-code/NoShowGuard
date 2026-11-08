import sys
import asyncio
from datetime import datetime, date, time, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.database import AsyncSessionLocal, init_db
from app.models import Master, Slot, SlotStatus, Booking, utc_now

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        now = utc_now()
        from sqlalchemy import select
        stmt = select(Master).where(Master.tg_id == 1234567)
        master = (await db.execute(stmt)).scalar_one_or_none()

        if not master:
            master = Master(
                tg_id=1234567,
                full_name="Анна Мастер",
                profession="Стилист-колорист",
                deposit_amount=300,
                trial_ends_at=now + timedelta(days=7),
                subscription_tier="trial",
                digest_enabled=True,
                digest_time="09:00"
            )
            db.add(master)
            await db.commit()
            await db.refresh(master)
        else:
            # Обновляем поля триала и дайджеста, если еще не были выставлены
            if not master.trial_ends_at:
                master.trial_ends_at = now + timedelta(days=7)
                master.subscription_tier = "trial"
                master.digest_enabled = True
                master.digest_time = "09:00"
                await db.commit()
                await db.refresh(master)

        # Создаем слоты на сегодня и на завтра
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        # 1. Добавляем исторический слот No-Show (вчера) для красивой демонстрации спасенной выручки
        yesterday_st = datetime.combine(yesterday, time(14, 0))
        check_past = select(Slot).where(Slot.master_id == master.id, Slot.start_time == yesterday_st)
        if not (await db.execute(check_past)).scalar_one_or_none():
            past_slot = Slot(
                master_id=master.id,
                start_time=yesterday_st,
                end_time=datetime.combine(yesterday, time(15, 30)),
                status=SlotStatus.COMPLETED
            )
            db.add(past_slot)
            await db.commit()
            await db.refresh(past_slot)

            past_booking = Booking(
                slot_id=past_slot.id,
                client_name="Алина Неявка",
                client_phone="+79991112233",
                service_title="Сложное окрашивание",
                service_price=5000,
                deposit_amount=300,
                payment_status="no_show_retained"
            )
            db.add(past_booking)
            await db.commit()

        slot_times = [
            (time(10, 0), time(11, 30)),
            (time(12, 0), time(13, 30)),
            (time(14, 0), time(15, 30)),
            (time(16, 0), time(17, 30)),
            (time(18, 0), time(19, 30)),
        ]

        for d in [today, tomorrow]:
            for start_t, end_t in slot_times:
                st = datetime.combine(d, start_t)
                check = select(Slot).where(Slot.master_id == master.id, Slot.start_time == st)
                if not (await db.execute(check)).scalar_one_or_none():
                    slot = Slot(
                        master_id=master.id,
                        start_time=st,
                        end_time=datetime.combine(d, end_t),
                        status=SlotStatus.FREE
                    )
                    db.add(slot)

        await db.commit()
        print(f"✅ База наполнена! Мастер ID: {master.tg_id}")
        print("🔗 Ссылка для тестирования в браузере:")
        print(f"👉 http://localhost:8000/app/?startapp=master_{master.tg_id}")


if __name__ == "__main__":
    asyncio.run(seed())
