from datetime import datetime, date, timedelta, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from app.models import Slot, SlotStatus, Booking, Master, utc_now
from app.config import settings

async def release_expired_slots(db: AsyncSession) -> int:
    """Освобождает слоты, у которых истекло время ожидания оплаты (10 мин)."""
    now = utc_now()
    stmt = (
        update(Slot)
        .where(
            and_(
                Slot.status == SlotStatus.PENDING,
                Slot.locked_until.isnot(None),
                Slot.locked_until < now
            )
        )
        .values(
            status=SlotStatus.FREE,
            locked_until=None
        )
    )
    result = await db.execute(stmt)
    if result.rowcount > 0:
        await db.commit()
    return result.rowcount

async def get_master_slots_by_date(
    db: AsyncSession,
    master_tg_id: int,
    target_date: date
) -> list[Slot]:
    """Возвращает свободные слоты мастера на указанную дату."""
    await release_expired_slots(db)

    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)

    stmt = (
        select(Slot)
        .join(Master, Slot.master_id == Master.id)
        .where(
            and_(
                Master.tg_id == master_tg_id,
                Slot.start_time >= start_dt,
                Slot.start_time <= end_dt,
                Slot.status == SlotStatus.FREE
            )
        )
        .order_by(Slot.start_time.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def reserve_slot_for_payment(
    db: AsyncSession,
    slot_id: int,
    client_name: str,
    client_phone: str,
    client_tg_id: int | None,
    service_title: str,
    service_price: int,
    deposit_amount: int
) -> Booking:
    """
    Атомарно блокирует слот на время оплаты с защитой от состояния гонки (Race Condition).
    Работает одинаково надежно как в PostgreSQL, так и в SQLite WAL.
    """
    now = utc_now()
    lock_expires = now + timedelta(minutes=settings.DEPOSIT_LOCK_MINUTES)

    # 1. Атомарный UPDATE: переводит слот в PENDING только если он FREE или просрочен PENDING
    lock_stmt = (
        update(Slot)
        .where(
            Slot.id == slot_id,
            or_(
                Slot.status == SlotStatus.FREE,
                and_(
                    Slot.status == SlotStatus.PENDING,
                    Slot.locked_until.isnot(None),
                    Slot.locked_until < now
                )
            )
        )
        .values(
            status=SlotStatus.PENDING,
            locked_until=lock_expires
        )
    )
    lock_result = await db.execute(lock_stmt)

    if lock_result.rowcount == 0:
        # Проверяем, существует ли слот вообще
        check_stmt = select(Slot.id).where(Slot.id == slot_id)
        slot_exists = (await db.execute(check_stmt)).scalar_one_or_none()
        if not slot_exists:
            raise ValueError("Слот не найден")
        raise ValueError("Слот уже занят или оформляется другим клиентом")

    # 2. Удаляем старые незавершенные черновики бронирования для этого слота (если были)
    await db.execute(delete(Booking).where(Booking.slot_id == slot_id))

    # 3. Создаем черновик бронирования
    booking = Booking(
        slot_id=slot_id,
        client_name=client_name,
        client_phone=client_phone,
        client_tg_id=client_tg_id,
        service_title=service_title,
        service_price=service_price,
        deposit_amount=deposit_amount,
        payment_status="pending"
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking

async def confirm_booking_payment(
    db: AsyncSession,
    booking_id: int,
    payment_id: str | None = None
) -> tuple[Booking, Slot, Master]:
    """
    Подтверждает бронь после успешной оплаты в ЮKassa.
    Переводит Slot в BOOKED, Booking в succeeded.
    """
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.slot).selectinload(Slot.master)
        )
        .where(Booking.id == booking_id)
    )
    result = await db.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise ValueError(f"Бронирование #{booking_id} не найдено")

    slot = booking.slot
    if not slot:
        raise ValueError(f"Слот для бронирования #{booking_id} не найден")

    master = slot.master

    # Переводим статусы
    slot.status = SlotStatus.BOOKED
    slot.locked_until = None

    booking.payment_status = "succeeded"
    if payment_id:
        booking.payment_id = payment_id

    await db.commit()
    await db.refresh(booking)
    await db.refresh(slot)
    return booking, slot, master
