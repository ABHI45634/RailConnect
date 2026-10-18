from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models.booking import BookingStatus
from app.models.passenger import PassengerStatus
class PassengerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=120)
    gender: str = Field(min_length=1, max_length=20)
class BookingCreate(BaseModel):
    train_id: int
    class_id: int
    journey_date: date
    passengers: list[PassengerCreate] = Field(min_length=1, max_length=6)
    payment_method: str = Field(default="DEMO", min_length=1, max_length=40)
class PassengerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    passenger_id: int
    name: str
    age: int
    gender: str
    seat_number: str | None
    status: PassengerStatus
class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    booking_id: int
    pnr: str
    user_id: int
    train_id: int
    class_id: int
    journey_date: date
    booking_date: datetime
    total_fare: Decimal
    status: BookingStatus
    passengers: list[PassengerRead]
class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    payment_id: int
    booking_id: int
    amount: Decimal
    payment_method: str
    transaction_id: str
    status: str
    created_at: datetime
class PNRRead(BaseModel):
    pnr: str
    booking_id: int
    train_id: int
    journey_date: date
    status: BookingStatus
    passengers: list[PassengerRead]
