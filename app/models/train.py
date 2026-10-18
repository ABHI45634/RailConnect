from sqlalchemy import ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
class Train(Base):
    __tablename__ = "trains"
    train_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    train_number: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    train_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_station_id: Mapped[int] = mapped_column(ForeignKey("stations.station_id", ondelete="RESTRICT"), nullable=False)
    destination_station_id: Mapped[int] = mapped_column(ForeignKey("stations.station_id", ondelete="RESTRICT"), nullable=False)
    departure_time: Mapped[object] = mapped_column(Time, nullable=False)
    arrival_time: Mapped[object] = mapped_column(Time, nullable=False)
    runs_on: Mapped[str] = mapped_column(String(80), default="Mon,Tue,Wed,Thu,Fri,Sat,Sun", nullable=False)
    source: Mapped["Station"] = relationship(foreign_keys=[source_station_id])
    destination: Mapped["Station"] = relationship(foreign_keys=[destination_station_id])
    routes: Mapped[list["Route"]] = relationship(back_populates="train", cascade="all, delete-orphan")
    classes: Mapped[list["TrainClass"]] = relationship(back_populates="train", cascade="all, delete-orphan")
