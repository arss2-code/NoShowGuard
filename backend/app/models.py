import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class SlotStatus(str, enum.Enum):
    FREE = "free"
    PENDING = "pending_payment"  # Заблокирован на 10 минут во время оплаты
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Master(Base):
    __tablename__ = "masters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(BigInteger, unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), nullable=True)
    profession = Column(String(100), default="Мастер услуг")
    deposit_amount = Column(Integer, default=300)  # Размер депозита (300/500 ₽)
    yookassa_shop_id = Column(String(50), nullable=True)
    yookassa_secret_key = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    slots = relationship("Slot", back_populates="master", cascade="all, delete-orphan")

class Slot(Base):
    __tablename__ = "slots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    master_id = Column(Integer, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    status = Column(
        Enum(SlotStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=SlotStatus.FREE,
        nullable=False,
        index=True
    )
    locked_until = Column(DateTime, nullable=True)  # Время истечения бронирования при неоплате
    
    master = relationship("Master", back_populates="slots")
    booking = relationship("Booking", back_populates="slot", uselist=False, cascade="all, delete-orphan")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slot_id = Column(Integer, ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, unique=True)
    client_tg_id = Column(BigInteger, nullable=True)
    client_name = Column(String(100), nullable=False)
    client_phone = Column(String(20), nullable=False)
    service_title = Column(String(150), nullable=False)
    service_price = Column(Integer, nullable=False)
    deposit_amount = Column(Integer, nullable=False)
    payment_id = Column(String(100), unique=True, nullable=True, index=True)
    payment_status = Column(String(50), default="pending", nullable=False)
    reminder_24h_sent = Column(Boolean, default=False, nullable=False)
    reminder_2h_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    slot = relationship("Slot", back_populates="booking")
