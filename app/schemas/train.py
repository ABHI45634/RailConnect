from datetime import date, time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.train_class import ClassType
class StationCreate(BaseModel):
    station_name: str = Field(min_length=1, max_length=120)
    station_code: str = Field(min_length=2, max_length=10, pattern=r"^[A-Za-z0-9]+$")
class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    station_id: int
    station_name: str
    station_code: str
class TrainCreate(BaseModel):
    train_number: str = Field(min_length=1, max_length=12)
    train_name: str = Field(min_length=1, max_length=160)
    source_station_id: int
    destination_station_id: int
    departure_time: time
    arrival_time: time
    runs_on: str = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
    @model_validator(mode="after")
    def different_stations(self):
        if self.source_station_id == self.destination_station_id:
            raise ValueError("Source and destination stations must differ")
        return self
class TrainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    train_id: int
    train_number: str
    train_name: str
    source_station_id: int
    destination_station_id: int
    departure_time: time
    arrival_time: time
    runs_on: str
class TrainClassCreate(BaseModel):
    class_type: ClassType
    total_seats: int = Field(gt=0, le=2000)
    fare_per_km: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
class TrainClassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    class_id: int
    train_id: int
    class_type: ClassType
    total_seats: int
    fare_per_km: Decimal
class RouteCreate(BaseModel):
    station_id: int
    stop_sequence: int = Field(ge=0)
    arrival_time: time | None = None
    departure_time: time | None = None
    distance_from_source: int = Field(ge=0)
class RouteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    route_id: int
    train_id: int
    station_id: int
    stop_sequence: int
    arrival_time: time | None
    departure_time: time | None
    distance_from_source: int
class AvailabilityRead(BaseModel):
    train_id: int
    class_id: int
    class_type: ClassType
    journey_date: date
    available_seats: int
