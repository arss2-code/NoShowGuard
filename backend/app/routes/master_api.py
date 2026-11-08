from datetime import datetime, date, timedelta, time
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Master, Slot, SlotStatus, Booking, SubscriptionPayment, Service, utc_now
from app.schemas import (
    MasterDashboardResponse,
    MasterResponse,
    MasterDashboardSlot,
    MasterBookingInfo,
    MasterSettingsUpdate,
    SlotAddRequest,
    SubscriptionCheckoutRequest,
    SubscriptionCheckoutResponse,
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse
)
from app.services.payment import payment_service
from app.config import settings

router = APIRouter(prefix="/api/masters", tags=["Master Cabinet API"])

async def get_master_or_404(tg_id: int, db: AsyncSession) -> Master:
    stmt = select(Master).where(Master.tg_id == tg_id)
    master = (await db.execute(stmt)).scalar_one_or_none()
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Мастер с Telegram ID {tg_id} не найден"
        )
    return master

async def get_or_create_master_db(tg_id: int, db: AsyncSession, full_name: str = "Мастер") -> Master:
    """Получает профиль мастера или автоматически создает новый с 7-дневным триалом."""
    stmt = select(Master).where(Master.tg_id == tg_id)
    master = (await db.execute(stmt)).scalar_one_or_none()
    if not master:
        now = utc_now()
        master = Master(
            tg_id=tg_id,
            full_name=full_name,
            profession="Мастер услуг",
            deposit_amount=settings.DEFAULT_DEPOSIT_AMOUNT,
            trial_ends_at=now + timedelta(days=7),
            subscription_tier="trial",
            digest_enabled=True,
            digest_time="09:00"
        )
        db.add(master)
        await db.commit()
        await db.refresh(master)

    if not master.services:
        default_svc = Service(
            master_id=master.id,
            title="Основная услуга / Сеанс",
            price=2000,
            duration_minutes=60,
            is_active=True
        )
        db.add(default_svc)
        await db.commit()
        await db.refresh(master)

    return master

@router.get("/{tg_id}/dashboard", response_model=MasterDashboardResponse)
@router.get("/{tg_id}/dashboard/", response_model=MasterDashboardResponse, include_in_schema=False)
async def get_master_dashboard(
    tg_id: int,
    target_date: date | None = Query(None, description="Фильтр слотов по дате"),
    db: AsyncSession = Depends(get_db)
):
    """
    Полная сводка для кабинета мастера:
    - Профиль и настройки
    - Спасенная выручка (удержанные депозиты No-Show)
    - Статус 7-дневного триала и подписки
    - Список слотов с деталями клиентов
    """
    master = await get_or_create_master_db(tg_id, db)
    now = utc_now()

    # Инициализация триала при первом входе, если не установлен
    if not master.trial_ends_at:
        master.trial_ends_at = master.created_at + timedelta(days=7)
        await db.commit()
        await db.refresh(master)

    # Расчет оставшихся дней триала
    trial_days_left = 0
    if master.trial_ends_at and master.trial_ends_at > now:
        trial_days_left = max(1, (master.trial_ends_at - now).days + 1)

    subscription_active = trial_days_left > 0 or (
        master.subscription_active_until is not None and master.subscription_active_until > now
    )

    # 1. Расчет спасенной выручки от неявок (ст. 381.1 ГК РФ)
    saved_stmt = (
        select(func.coalesce(func.sum(Booking.deposit_amount), 0))
        .join(Slot, Booking.slot_id == Slot.id)
        .where(
            and_(
                Slot.master_id == master.id,
                Booking.payment_status == "no_show_retained"
            )
        )
    )
    saved_revenue = (await db.execute(saved_stmt)).scalar() or 0

    # 2. Общее число подтвержденных записей
    total_bookings_stmt = (
        select(func.count(Booking.id))
        .join(Slot, Booking.slot_id == Slot.id)
        .where(
            and_(
                Slot.master_id == master.id,
                Booking.payment_status.in_(["succeeded", "no_show_retained"])
            )
        )
    )
    total_bookings_count = (await db.execute(total_bookings_stmt)).scalar() or 0

    # 3. Получение слотов
    slot_stmt = (
        select(Slot)
        .options(selectinload(Slot.booking))
        .where(Slot.master_id == master.id)
    )

    if target_date:
        start_filter = datetime.combine(target_date, time.min)
        end_filter = datetime.combine(target_date, time.max)
        slot_stmt = slot_stmt.where(
            and_(
                Slot.start_time >= start_filter,
                Slot.start_time <= end_filter
            )
        )
    else:
        # По умолчанию слоты от начала сегодняшнего дня
        today_start = datetime.combine(now.date(), time.min)
        slot_stmt = slot_stmt.where(Slot.start_time >= today_start)

    slot_stmt = slot_stmt.order_by(Slot.start_time.asc())
    slots_db = (await db.execute(slot_stmt)).scalars().all()

    slots_result = []
    for s in slots_db:
        booking_info = None
        # Отображаем данные брони ТОЛЬКО для занятых слотов или слотов в процессе оплаты
        if s.booking and s.status in [SlotStatus.BOOKED, SlotStatus.PENDING, SlotStatus.COMPLETED]:
            booking_info = MasterBookingInfo(
                id=s.booking.id,
                client_name=s.booking.client_name,
                client_phone=s.booking.client_phone,
                service_title=s.booking.service_title,
                service_price=s.booking.service_price,
                deposit_amount=s.booking.deposit_amount,
                payment_status=s.booking.payment_status
            )
        slots_result.append(
            MasterDashboardSlot(
                id=s.id,
                start_time=s.start_time,
                end_time=s.end_time,
                status=s.status,
                booking=booking_info
            )
        )

    return MasterDashboardResponse(
        master=MasterResponse.model_validate(master),
        saved_revenue=saved_revenue,
        total_bookings_count=total_bookings_count,
        trial_days_left=trial_days_left,
        subscription_tier=master.subscription_tier,
        subscription_active=subscription_active,
        digest_enabled=master.digest_enabled,
        digest_time=master.digest_time,
        slots=slots_result,
        services=[ServiceResponse.model_validate(svc) for svc in master.services if svc.is_active]
    )

@router.post("/{tg_id}/slots", status_code=status.HTTP_201_CREATED)
async def add_slot(
    tg_id: int,
    payload: SlotAddRequest,
    db: AsyncSession = Depends(get_db)
):
    """Добавление индивидуального рабочего слота."""
    master = await get_master_or_404(tg_id, db)

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Время окончания слота должно быть позже времени начала"
        )

    # Проверка на пересечение слотов мастера
    overlap_stmt = select(Slot).where(
        and_(
            Slot.master_id == master.id,
            Slot.status != SlotStatus.CANCELLED,
            or_(
                and_(Slot.start_time <= payload.start_time, Slot.end_time > payload.start_time),
                and_(Slot.start_time < payload.end_time, Slot.end_time >= payload.end_time),
                and_(Slot.start_time >= payload.start_time, Slot.end_time <= payload.end_time)
            )
        )
    )
    existing = (await db.execute(overlap_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Слот пересекается с уже существующим окном в вашем расписании"
        )

    new_slot = Slot(
        master_id=master.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=SlotStatus.FREE
    )
    db.add(new_slot)
    await db.commit()
    await db.refresh(new_slot)

    return {"message": "Слот успешно добавлен", "slot_id": new_slot.id}

@router.post("/{tg_id}/slots/template")
async def generate_standard_slots(
    tg_id: int,
    target_date: date = Query(..., description="Дата для генерации слотов (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """Быстрое заполнение дня стандартной рабочей сеткой (10:00, 12:00, 14:00, 16:00, 18:00)."""
    master = await get_master_or_404(tg_id, db)

    standard_times = [
        (time(10, 0), time(11, 30)),
        (time(12, 0), time(13, 30)),
        (time(14, 0), time(15, 30)),
        (time(16, 0), time(17, 30)),
        (time(18, 0), time(19, 30)),
    ]

    created = 0
    for st, et in standard_times:
        start_dt = datetime.combine(target_date, st)
        end_dt = datetime.combine(target_date, et)

        check_stmt = select(Slot).where(
            and_(
                Slot.master_id == master.id,
                Slot.start_time == start_dt
            )
        )
        if not (await db.execute(check_stmt)).scalar_one_or_none():
            slot = Slot(
                master_id=master.id,
                start_time=start_dt,
                end_time=end_dt,
                status=SlotStatus.FREE
            )
            db.add(slot)
            created += 1

    await db.commit()
    return {"message": f"Добавлено {created} стандартных слотов на {target_date}", "created_count": created}

@router.delete("/{tg_id}/slots/{slot_id}")
async def delete_slot(
    tg_id: int,
    slot_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление свободного слота."""
    master = await get_master_or_404(tg_id, db)

    stmt = select(Slot).where(
        and_(
            Slot.id == slot_id,
            Slot.master_id == master.id
        )
    )
    slot = (await db.execute(stmt)).scalar_one_or_none()

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Слот не найден"
        )

    if slot.status == SlotStatus.BOOKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить забронированный слот. Сначала отмените запись клиента."
        )

    await db.delete(slot)
    await db.commit()
    return {"message": "Слот успешно удален"}

@router.patch("/{tg_id}/settings")
@router.patch("/{tg_id}/settings/", include_in_schema=False)
async def update_settings(
    tg_id: int,
    payload: MasterSettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление настроек мастера: ФИО, салон, адрес, депозит, профессия, утренний дайджест."""
    master = await get_or_create_master_db(tg_id, db)

    if payload.full_name is not None and payload.full_name.strip():
        master.full_name = payload.full_name.strip()
    if payload.profession is not None and payload.profession.strip():
        master.profession = payload.profession.strip()
    if payload.salon_name is not None:
        master.salon_name = payload.salon_name.strip() or None
    if payload.address is not None:
        master.address = payload.address.strip() or None
    if payload.deposit_amount is not None:
        master.deposit_amount = payload.deposit_amount
    if payload.digest_enabled is not None:
        master.digest_enabled = payload.digest_enabled
    if payload.digest_time is not None:
        master.digest_time = payload.digest_time

    await db.commit()
    await db.refresh(master)
    return {"message": "Настройки успешно сохранены", "master": MasterResponse.model_validate(master)}

@router.get("/{tg_id}/services", response_model=list[ServiceResponse])
@router.get("/{tg_id}/services/", response_model=list[ServiceResponse], include_in_schema=False)
async def get_master_services(
    tg_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение каталога услуг мастера."""
    master = await get_or_create_master_db(tg_id, db)
    return [ServiceResponse.model_validate(s) for s in master.services if s.is_active]

@router.post("/{tg_id}/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{tg_id}/services/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_master_service(
    tg_id: int,
    payload: ServiceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Добавление новой услуги в прайс-лист мастера."""
    master = await get_or_create_master_db(tg_id, db)
    new_svc = Service(
        master_id=master.id,
        title=payload.title.strip(),
        price=payload.price,
        duration_minutes=payload.duration_minutes,
        is_active=True
    )
    db.add(new_svc)
    await db.commit()
    await db.refresh(new_svc)
    return ServiceResponse.model_validate(new_svc)

@router.patch("/{tg_id}/services/{service_id}", response_model=ServiceResponse)
@router.patch("/{tg_id}/services/{service_id}/", response_model=ServiceResponse, include_in_schema=False)
async def update_master_service(
    tg_id: int,
    service_id: int,
    payload: ServiceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Редактирование услуги мастера."""
    master = await get_or_create_master_db(tg_id, db)
    stmt = select(Service).where(and_(Service.id == service_id, Service.master_id == master.id))
    svc = (await db.execute(stmt)).scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")

    if payload.title is not None and payload.title.strip():
        svc.title = payload.title.strip()
    if payload.price is not None:
        svc.price = payload.price
    if payload.duration_minutes is not None:
        svc.duration_minutes = payload.duration_minutes
    if payload.is_active is not None:
        svc.is_active = payload.is_active

    await db.commit()
    await db.refresh(svc)
    return ServiceResponse.model_validate(svc)

@router.delete("/{tg_id}/services/{service_id}")
@router.delete("/{tg_id}/services/{service_id}/", include_in_schema=False)
async def delete_master_service(
    tg_id: int,
    service_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление услуги мастера."""
    master = await get_or_create_master_db(tg_id, db)
    stmt = select(Service).where(and_(Service.id == service_id, Service.master_id == master.id))
    svc = (await db.execute(stmt)).scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")

    await db.delete(svc)
    await db.commit()
    return {"message": "Услуга успешно удалена"}

@router.post("/{tg_id}/subscription/checkout", response_model=SubscriptionCheckoutResponse)
async def checkout_subscription(
    tg_id: int,
    payload: SubscriptionCheckoutRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Генерация счета на оплату SaaS-подписки по СБП:
    - «Старт» = 490 ₽/мес
    - «Про» = 890 ₽/мес
    """
    master = await get_master_or_404(tg_id, db)

    SUBSCRIPTION_PRICES = {
        ("start", "1m"): (490, 30, "1 мес."),
        ("start", "3m"): (1250, 90, "3 мес."),
        ("start", "1y"): (4100, 365, "1 год"),
        ("pro", "1m"): (890, 30, "1 мес."),
        ("pro", "3m"): (2270, 90, "3 мес."),
        ("pro", "1y"): (7470, 365, "1 год"),
    }
    amount, days_to_add, label = SUBSCRIPTION_PRICES.get((payload.tier, payload.period), (490, 30, "1 мес."))

    # Формируем платеж
    payment_info = payment_service.create_sbp_payment(
        booking_id=999900 + master.id,
        deposit_amount=amount,
        service_title=f"Подписка NoShowGuard ({payload.tier.upper()}) на {label}",
        client_phone=f"+7900{master.id:06d}"
    )

    sub_payment = SubscriptionPayment(
        master_id=master.id,
        amount=amount,
        tier=payload.tier,
        payment_id=payment_info.get("payment_id"),
        payment_status="pending"
    )
    db.add(sub_payment)
    await db.commit()

    return SubscriptionCheckoutResponse(
        payment_id=payment_info.get("payment_id", "mock_sub_id"),
        tier=payload.tier,
        amount=amount,
        confirmation_url=payment_info.get("confirmation_url", "")
    )

@router.post("/{tg_id}/subscription/simulate-success")
async def simulate_subscription_success(
    tg_id: int,
    tier: str = Query("start", pattern=r"^(start|pro)$"),
    period: str = Query("1m", pattern=r"^(1m|3m|1y)$"),
    db: AsyncSession = Depends(get_db)
):
    """Тестовое мгновенное продление подписки (на 1 мес, 3 мес или 1 год)."""
    master = await get_master_or_404(tg_id, db)
    now = utc_now()

    days_map = {"1m": 30, "3m": 90, "1y": 365}
    days_to_add = days_map.get(period, 30)

    current_until = master.subscription_active_until or now
    if current_until < now:
        current_until = now

    master.subscription_tier = tier
    master.subscription_active_until = current_until + timedelta(days=days_to_add)
    await db.commit()
    await db.refresh(master)

    return {
        "message": f"Подписка «{tier.upper()}» успешно активирована на {days_to_add} дн.",
        "active_until": master.subscription_active_until
    }


@router.post("/{tg_id}/slots/{slot_id}/no-show")
async def mark_slot_no_show(
    tg_id: int,
    slot_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Фиксация неявки клиента (No-Show) мастером прямо из веб-кабинета.
    Переводит слот в COMPLETED, а депозит в no_show_retained (ст. 381.1 ГК РФ).
    """
    master = await get_master_or_404(tg_id, db)
    stmt = (
        select(Slot)
        .options(selectinload(Slot.booking))
        .where(
            and_(
                Slot.id == slot_id,
                Slot.master_id == master.id
            )
        )
    )
    slot = (await db.execute(stmt)).scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")

    if not slot.booking:
        raise HTTPException(status_code=400, detail="На данный слот нет бронирования")

    deposit = slot.booking.deposit_amount
    slot.status = SlotStatus.COMPLETED
    slot.booking.payment_status = "no_show_retained"
    await db.commit()

    # Уведомление в Telegram бота мастера
    from app.bot.bot_instance import safe_send_message
    await safe_send_message(
        chat_id=master.tg_id,
        text=(
            f"⚠️ <b>Зафиксирована неявка (No-Show)!</b>\n\n"
            f"Клиент: <b>{slot.booking.client_name}</b>\n"
            f"Сеанс: <b>{slot.start_time.strftime('%d.%m.%Y в %H:%M')}</b>\n"
            f"Сумма депозита <b>{deposit} ₽</b> удержана в вашу пользу (ст. 381.1 ГК РФ) "
            f"и зачислена в спасенную выручку."
        )
    )

    return {
        "success": True,
        "message": f"Неявка зафиксирована. Депозит {deposit} ₽ удержан по ст. 381.1 ГК РФ.",
        "slot_id": slot.id,
        "status": slot.status.value,
        "saved_deposit": deposit
    }

