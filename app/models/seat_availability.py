from datetime import date
from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
class SeatAvailability(Base):
    __tablename__ = "seat_availability"
    __table_args__ = (UniqueConstraint("train_id", "class_id", "journey_date", name="uq_seats_train_class_date"), CheckConstraint("available_seats >= 0", name="ck_available_seats_nonnegative"))
    availability_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.train_id", ondelete="CASCADE"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("train_classes.class_id", ondelete="CASCADE"), nullable=False)
    journey_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
