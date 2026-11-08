import sys
import asyncio
from datetime import datetime, date, time, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.database import AsyncSessionLocal, init_db
from app.models import Master, Slot, SlotStatus

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Проверяем, существует ли мастер
        from sqlalchemy import select
        stmt = select(Master).where(Master.tg_id == 1234567)
        master = (await db.execute(stmt)).scalar_one_or_none()

        if not master:
            master = Master(
                tg_id=1234567,
                full_name="Анна Мастер",
                profession="Стилист-колорист",
                deposit_amount=300
            )
            db.add(master)
            await db.commit()
            await db.refresh(master)

        # Создаем слоты на сегодня и на завтра
        today = date.today()
        tomorrow = today + timedelta(days=1)

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
