from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field
from app.models import SlotStatus

class MasterBase(BaseModel):
    full_name: str = Field(..., max_length=100)
    username: str | None = Field(None, max_length=50)
    profession: str = Field("Мастер услуг", max_length=100)
    salon_name: str | None = Field(None, max_length=150)
    address: str | None = Field(None, max_length=255)
    deposit_amount: int = Field(300, ge=0)

class ServiceBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    price: int = Field(..., gt=0)
    duration_minutes: int = Field(60, ge=5, le=480)

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=150)
    price: int | None = Field(None, gt=0)
    duration_minutes: int | None = Field(None, ge=5, le=480)
    is_active: bool | None = None

class ServiceResponse(ServiceBase):
    id: int
    master_id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MasterCreate(MasterBase):
    tg_id: int

class MasterResponse(MasterBase):
    id: int
    tg_id: int
    is_active: bool
    trial_ends_at: datetime | None = None
    subscription_tier: str = "trial"
    subscription_active_until: datetime | None = None
    digest_enabled: bool = True
    digest_time: str = "09:00"
    created_at: datetime
    services: list[ServiceResponse] = []

    model_config = ConfigDict(from_attributes=True)

class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime

class SlotResponse(BaseModel):
    id: int
    master_id: int
    start_time: datetime
    end_time: datetime
    status: SlotStatus

    model_config = ConfigDict(from_attributes=True)

class BookingInitiateRequest(BaseModel):
    slot_id: int
    client_name: str = Field(..., min_length=2, max_length=100)
    client_phone: str = Field(..., min_length=10, max_length=20)
    client_tg_id: int | None = None
    service_title: str = Field(..., min_length=2, max_length=150)
    service_price: int = Field(..., gt=0)
    terms_accepted: bool = Field(True, description="Согласие с условиями оферты ст. 381.1 ГК РФ")

class BookingInitiateResponse(BaseModel):
    booking_id: int
    slot_id: int
    deposit_amount: int
    payment_id: str | None
    confirmation_url: str
    status: str

    model_config = ConfigDict(from_attributes=True)

class BookingStatusResponse(BaseModel):
    booking_id: int
    slot_id: int
    status: str
    payment_status: str
    client_name: str
    service_title: str
    deposit_amount: int
    start_time: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MasterBookingInfo(BaseModel):
    id: int
    client_name: str
    client_phone: str
    service_title: str
    service_price: int
    deposit_amount: int
    payment_status: str

    model_config = ConfigDict(from_attributes=True)


class MasterDashboardSlot(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    status: SlotStatus
    booking: MasterBookingInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class MasterDashboardResponse(BaseModel):
    master: MasterResponse
    saved_revenue: int
    total_bookings_count: int
    trial_days_left: int
    subscription_tier: str
    subscription_active: bool
    digest_enabled: bool
    digest_time: str
    slots: list[MasterDashboardSlot]
    services: list[ServiceResponse] = []


class MasterSettingsUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=100)
    profession: str | None = Field(None, max_length=100)
    salon_name: str | None = Field(None, max_length=150)
    address: str | None = Field(None, max_length=255)
    deposit_amount: int | None = Field(None, ge=0, le=5000)
    digest_enabled: bool | None = None
    digest_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")


class SlotAddRequest(BaseModel):
    start_time: datetime
    end_time: datetime


class SubscriptionCheckoutRequest(BaseModel):
    tier: str = Field("start", pattern=r"^(start|pro)$")
    period: str = Field("1m", pattern=r"^(1m|3m|1y)$")


class SubscriptionCheckoutResponse(BaseModel):
    payment_id: str
    tier: str
    amount: int
    confirmation_url: str

