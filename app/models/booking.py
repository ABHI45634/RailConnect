from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    WAITING = "WAITING"
    CANCELLED = "CANCELLED"
class Booking(Base):
    __tablename__ = "bookings"
    booking_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pnr: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.train_id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("train_classes.class_id", ondelete="RESTRICT"), nullable=False)
    journey_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    booking_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    total_fare: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(SAEnum(BookingStatus, name="booking_status", values_callable=lambda e: [x.value for x in e]), default=BookingStatus.CONFIRMED, nullable=False)
    user: Mapped["User"] = relationship(back_populates="bookings")
    passengers: Mapped[list["Passenger"]] = relationship(back_populates="booking", cascade="all, delete-orphan", order_by="Passenger.passenger_id")
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
