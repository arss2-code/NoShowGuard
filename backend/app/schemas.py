from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field
from app.models import SlotStatus

class MasterBase(BaseModel):
    full_name: str = Field(..., max_length=100)
    username: str | None = Field(None, max_length=50)
    profession: str = Field("Мастер услуг", max_length=100)
    deposit_amount: int = Field(300, ge=0)

class MasterCreate(MasterBase):
    tg_id: int

class MasterResponse(MasterBase):
    id: int
    tg_id: int
    is_active: bool
    created_at: datetime

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
