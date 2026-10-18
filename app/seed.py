import asyncio
from datetime import date, timedelta, time
from decimal import Decimal
from sqlalchemy import select
from app.database import AsyncSessionLocal, engine, Base
from app.config import settings
from app.models import User, UserRole, Station, Train, Route, TrainClass, ClassType, SeatAvailability
from app.core.security import hash_password

STATIONS = [("Hyderabad Deccan", "HYB"), ("Secunderabad Junction", "SC"), ("Vijayawada Junction", "BZA"), ("Visakhapatnam", "VSKP"), ("Chennai Central", "MAS"), ("KSR Bengaluru", "SBC"), ("Tirupati", "TPTY"), ("New Delhi", "NDLS"), ("Bhubaneswar", "BBS"), ("Pune Junction", "PUNE")]
TRAINS = [
    ("12727", "Godavari Express", "HYB", "VSKP", time(17, 15), time(6, 45), ["HYB", "SC", "BZA", "VSKP"], [0, 10, 275, 699]),
    ("12007", "Shatabdi Express", "MAS", "SBC", time(6, 0), time(10, 45), ["MAS", "TPTY", "SBC"], [0, 135, 362]),
    ("12801", "Purushottam Express", "NDLS", "BBS", time(22, 40), time(4, 15), ["NDLS", "BBS"], [0, 1744]),
    ("12163", "Chennai Express", "MAS", "PUNE", time(18, 20), time(20, 10), ["MAS", "SBC", "PUNE"], [0, 350, 1196]),
    ("12704", "Falaknuma Express", "SC", "BZA", time(16, 50), time(22, 15), ["SC", "HYB", "BZA"], [0, 10, 275]),
]
async def seed():
    """Create database tables and idempotently add demo users, stations, trains, classes, and inventory."""
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        if not await db.scalar(select(User.user_id).where(User.email == "admin@train.com")):
            db.add(User(name="System Administrator", email="admin@train.com", phone="9000000000", password_hash=hash_password("Admin@123"), role=UserRole.ADMIN))
        for email, name, phone in [("passenger1@train.com", "Aarav Sharma", "9000000001"), ("passenger2@train.com", "Ananya Rao", "9000000002")]:
            if not await db.scalar(select(User.user_id).where(User.email == email)):
                db.add(User(name=name, email=email, phone=phone, password_hash=hash_password("Passenger@123"), role=UserRole.PASSENGER))
        await db.flush()
        station_ids = {}
        for name, code in STATIONS:
            row = await db.scalar(select(Station).where(Station.station_code == code))
            if row is None:
                row = Station(station_name=name, station_code=code); db.add(row); await db.flush()
            station_ids[code] = row.station_id
        await db.flush()
        for number, name, src, dst, depart, arrive, route_codes, distances in TRAINS:
            train = await db.scalar(select(Train).where(Train.train_number == number))
            if train is None:
                train = Train(train_number=number, train_name=name, source_station_id=station_ids[src], destination_station_id=station_ids[dst], departure_time=depart, arrival_time=arrive, runs_on="Mon,Tue,Wed,Thu,Fri,Sat,Sun")
                db.add(train); await db.flush()
            for sequence, (code, distance) in enumerate(zip(route_codes, distances)):
                route = await db.scalar(select(Route).where(Route.train_id == train.train_id, Route.stop_sequence == sequence))
                if route is None:
                    db.add(Route(train_id=train.train_id, station_id=station_ids[code], stop_sequence=sequence, arrival_time=depart if sequence == 0 else None, departure_time=depart if sequence == 0 else None, distance_from_source=distance))
            await db.flush()
            for class_type, capacity, rate in [(ClassType.SL, 72, Decimal("0.50")), (ClassType.A3, 64, Decimal("1.20")), (ClassType.A2, 46, Decimal("1.80"))]:
                cls = await db.scalar(select(TrainClass).where(TrainClass.train_id == train.train_id, TrainClass.class_type == class_type))
                if cls is None:
                    cls = TrainClass(train_id=train.train_id, class_type=class_type, total_seats=capacity, fare_per_km=rate); db.add(cls); await db.flush()
                for offset in range(30):
                    journey_date = date.today() + timedelta(days=offset)
                    exists = await db.scalar(select(SeatAvailability.availability_id).where(SeatAvailability.train_id == train.train_id, SeatAvailability.class_id == cls.class_id, SeatAvailability.journey_date == journey_date))
                    if not exists: db.add(SeatAvailability(train_id=train.train_id, class_id=cls.class_id, journey_date=journey_date, available_seats=capacity, version=0))
        await db.commit()
    print("Seed completed. Admin: admin@train.com / Admin@123")

if __name__ == "__main__": asyncio.run(seed())
