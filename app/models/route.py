from sqlalchemy import ForeignKey, Integer, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (UniqueConstraint("train_id", "station_id", "stop_sequence", name="uq_route_train_station_sequence"),)
    route_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.train_id", ondelete="CASCADE"), nullable=False, index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.station_id", ondelete="RESTRICT"), nullable=False)
    stop_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_time: Mapped[object | None] = mapped_column(Time, nullable=True)
    departure_time: Mapped[object | None] = mapped_column(Time, nullable=True)
    distance_from_source: Mapped[int] = mapped_column(Integer, nullable=False)
    train: Mapped["Train"] = relationship(back_populates="routes")
    station: Mapped["Station"] = relationship()
