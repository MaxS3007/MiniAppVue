from datetime import date, time
from typing import List, Dict
from pydantic import BaseModel, ConfigDict

class BookingRequest(BaseModel):
    doctor_id: int
    user_id: int
    day_booking: date
    time_booking: time

class TelegramIDModel(BaseModel):
    telegram_id: int

    model_config = ConfigDict(from_attributes=True)

class SpecIDModel(BaseModel):
    specialization_id: int

class UserModel(TelegramIDModel):
    username: str | None
    first_name: str | None
    last_name: str | None

class BookingSlot(BaseModel):
    time: str
    isAvailable: bool

class BookingWeek(BaseModel):
    week: Dict[str, List[BookingSlot]]