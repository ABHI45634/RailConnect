from enum import Enum
from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
class PassengerStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    WAITING = "WAITING"
    RAC = "RAC"
    CANCELLED = "CANCELLED"
class Passenger(Base):
    __tablename__ = "passengers"
    passenger_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    seat_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[PassengerStatus] = mapped_column(SAEnum(PassengerStatus, name="passenger_status", values_callable=lambda e: [x.value for x in e]), nullable=False)
    booking: Mapped["Booking"] = relationship(back_populates="passengers")
