# План для чата: Фаза 1.1 — Бэкенд, База данных и Telegram-бот (День 2)

> **Как использовать этот файл:**  
> Скопируйте текст ниже в новый чат с вашим AI-агентом для кодинга бэкенда и Telegram-бота. Файл содержит полную архитектурную спецификацию, схему БД, API-эндпоинты и интеграцию с СБП ЮKassa.

---

```markdown
### КОНТЕКСТ ДЛЯ AI-АГЕНТА
Ты — Senior Python / FastAPI / aiogram 3 разработчик. Мы создаем бэкенд микро-SaaS NoShowGuard за 24 часа.
Стек: Python 3.12, FastAPI, aiogram 3.10+, SQLAlchemy 2.0 (async), SQLite WAL (на старте) / PostgreSQL, YooKassa API (СБП).
Твоя задача — пошагово реализовать и протестировать модели данных, роуты FastAPI, обработчик вебхуков платежей и бота управления расписанием мастера.
Строгий запрет: никакого складского учета, зарплат и enterprise-функций. Только связка: Мастер → Слоты → Бронь → СБП-депозит.
```

---

## 🏗 Архитектура каталогов проекта

```
backend/
├── app/
│   ├── main.py               # Точка входа: инициализация FastAPI, aiogram, lifespan
│   ├── config.py             # Переменные окружения (BOT_TOKEN, YOOKASSA_*, DB_URL)
│   ├── database.py           # Async engine, sessionmaker, Base
│   ├── models.py             # Модели SQLAlchemy: Master, Service, Slot, Booking
│   ├── schemas.py            # Pydantic-схемы для валидации запросов и ответов
│   ├── bot/
│   │   ├── handlers.py       # Обработчики команд мастера (/start, расписание, слоты)
│   │   └── keyboards.py      # Инлайн-кнопки и запуск WebApp
│   ├── services/
│   │   ├── slot_service.py   # Логика резервации с Pessimistic Lock
│   │   └── payment.py        # Интеграция с ЮKassa СБП API
│   └── routes/
│       ├── public_api.py     # Эндпоинты для Mini App (слоты, бронирование)
│       └── webhooks.py       # Вебхук ЮKassa (payment.succeeded)
├── alembic/                  # Миграции базы данных
├── requirements.txt
└── Dockerfile
```

---

## 📋 Пошаговый план разработки на День 2

### Шаг 1: Настройка окружения и зависимостей
Создать файл `requirements.txt`:
```txt
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
aiogram>=3.14.0
sqlalchemy>=2.0.36
aiosqlite>=0.20.0
asyncpg>=0.30.0
alembic>=1.13.3
pydantic>=2.9.2
pydantic-settings>=2.5.2
yookassa>=3.3.0
httpx>=0.27.2
```

---

### Шаг 2: Модели базы данных (`models.py`)

```python
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class SlotStatus(str, enum.Enum):
    FREE = "free"
    PENDING = "pending_payment"  # Заблокирован на 10 минут во время оплаты
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Master(Base):
    __tablename__ = "masters"
    
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), nullable=True)
    profession = Column(String(100), default="Мастер услуг")
    deposit_amount = Column(Integer, default=300) # Размер депозита (300/500 ₽)
    yookassa_shop_id = Column(String(50), nullable=True)
    yookassa_secret_key = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    slots = relationship("Slot", back_populates="master", cascade="all, delete-orphan")

class Slot(Base):
    __tablename__ = "slots"
    
    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey("masters.id"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(SlotStatus), default=SlotStatus.FREE, nullable=False, index=True)
    locked_until = Column(DateTime, nullable=True) # Время разблокировки при неуплате
    
    master = relationship("Master", back_populates="slots")
    booking = relationship("Booking", back_populates="slot", uselist=False)

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False, unique=True)
    client_tg_id = Column(BigInteger, nullable=True)
    client_name = Column(String(100), nullable=False)
    client_phone = Column(String(20), nullable=False)
    service_title = Column(String(150), nullable=False)
    service_price = Column(Integer, nullable=False)
    deposit_amount = Column(Integer, nullable=False)
    payment_id = Column(String(100), unique=True, nullable=True)
    payment_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    slot = relationship("Slot", back_populates="booking")
```

---

### Шаг 3: Логика бронирования с защитой от гонки (`slot_service.py`)

```python
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Slot, SlotStatus, Booking

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
    # 1. Pessimistic lock слота: никто другой не сможет взять его одновременно
    stmt = select(Slot).where(Slot.id == slot_id).with_for_update()
    result = await db.execute(stmt)
    slot = result.scalar_one_or_none()

    if not slot:
        raise ValueError("Слот не найден")

    # Слот доступен, если он FREE, или если PENDING, но время блокировки истекло
    now = datetime.utcnow()
    if slot.status == SlotStatus.PENDING and slot.locked_until and slot.locked_until < now:
        slot.status = SlotStatus.FREE

    if slot.status != SlotStatus.FREE:
        raise ValueError("Слот уже занят или оформляется другим клиентом")

    # 2. Блокируем на 10 минут
    slot.status = SlotStatus.PENDING
    slot.locked_until = now + timedelta(minutes=10)

    # 3. Создаем черновик бронирования
    booking = Booking(
        slot_id=slot.id,
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
```

---

### Шаг 4: Эндпоинты для Telegram Mini App (`public_api.py`)

1. `GET /api/masters/{tg_id}/slots?date=2026-11-10`
   - Возвращает список слотов мастера на выбранный день.
   - Фильтрует слоты со статусом `FREE` (а также просроченные `PENDING`).

2. `POST /api/bookings/initiate`
   - Принимает: `slot_id`, `client_name`, `client_phone`, `client_tg_id`, `service_title`, `service_price`.
   - Вызывает `reserve_slot_for_payment`.
   - Генерирует платеж в ЮKassa (метод `sbp`).
   - Возвращает: `booking_id`, `confirmation_url` (ссылка СБП для мобильного банка).

3. `GET /api/bookings/{booking_id}/status`
   - Возвращает текущий статус бронирования (`pending`, `booked`, `cancelled`).

---

### Шаг 5: Обработка Webhook ЮKassa (`webhooks.py`)
- Слушает `POST /api/webhooks/yookassa`.
- При событии `payment.succeeded`:
  1. Извлекает `metadata.booking_id`.
  2. Переводит `Slot.status = SlotStatus.BOOKED`.
  3. Переводит `Booking.payment_status = "succeeded"`.
  4. Отправляет Telegram-уведомление мастеру через `bot.send_message`:
     > *«✅ Новая запись с гарантией! Клиент [Имя] внес депозит [300] ₽ по СБП на [Дата Время].»*
  5. Отправляет подтверждение клиенту с кнопкой вызова оферты и отмены.

---

### Шаг 6: Telegram-бот мастера (`bot/handlers.py`)
- `/start`: Регистрация мастера, ввод профессии, настройка слотов.
- Генерация персональной ссылки для шапки профиля:
  `https://t.me/NoShowGuardBot/app?startapp=master_{master_tg_id}`
- Уведомление об отмене записи клиентом.
- Кнопка «Клиент не пришел» (активируется через 15 минут после начала слота).

---

## 🧪 Тестирование бэкенда
- [ ] Проверить генерацию тестового СБП-платежа через песочницу ЮKassa.
- [ ] Запустить 2 одновременных запроса на один `slot_id` — второй обязан получить `400 Bad Request`.
- [ ] Сымитировать вебхук `payment.succeeded` и убедиться, что бот присылает пуш в Telegram.
