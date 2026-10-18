from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
class Station(Base):
    __tablename__ = "stations"
    station_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    station_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
