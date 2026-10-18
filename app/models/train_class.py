from enum import Enum
from decimal import Decimal
from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, Integer, Numeric, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
class ClassType(str, Enum):
    SL = "SL"
    A3 = "3A"
    A2 = "2A"
    A1 = "1A"
class TrainClass(Base):
    __tablename__ = "train_classes"
    __table_args__ = (UniqueConstraint("train_id", "class_type", name="uq_train_class_type"), CheckConstraint("total_seats > 0", name="ck_class_seats_positive"), CheckConstraint("fare_per_km >= 0", name="ck_class_fare_nonnegative"))
    class_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.train_id", ondelete="CASCADE"), nullable=False, index=True)
    class_type: Mapped[ClassType] = mapped_column(SAEnum(ClassType, name="class_type", values_callable=lambda e: [x.value for x in e]), nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    fare_per_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    train: Mapped["Train"] = relationship(back_populates="classes")
