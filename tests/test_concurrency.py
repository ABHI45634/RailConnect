import asyncio
from datetime import date, timedelta
import pytest
from sqlalchemy import select
from app.seed import seed
from app.models import SeatAvailability, TrainClass
from tests.conftest import TestSession
@pytest.mark.asyncio
async def test_ten_parallel_requests_for_one_seat_exactly_one_wins(client, monkeypatch):
    """Integration test: PostgreSQL row locks must serialize ten competing bookings."""
    await seed()
    from app.config import settings
    monkeypatch.setattr(settings,"allow_waiting_list",False)
    login=(await client.post("/auth/login",json={"email":"passenger1@train.com","password":"Passenger@123"})).json()
    token=login["access_token"]; headers={"Authorization":f"Bearer {token}"}
    journey_date=date.today()+timedelta(days=2); train_id=1
    async with TestSession() as db:
        cls=await db.scalar(select(TrainClass).where(TrainClass.train_id==train_id,TrainClass.class_type=="SL"))
        row=await db.scalar(select(SeatAvailability).where(SeatAvailability.train_id==train_id,SeatAvailability.class_id==cls.class_id,SeatAvailability.journey_date==journey_date))
        row.available_seats=1; await db.commit(); class_id=cls.class_id
    payload={"train_id":train_id,"class_id":class_id,"journey_date":str(journey_date),"passengers":[{"name":"Concurrency Test","age":25,"gender":"X"}]}
    async def attempt():
        return await client.post("/bookings",json=payload,headers=headers)
    responses=await asyncio.gather(*(attempt() for _ in range(10)))
    assert sum(r.status_code==201 for r in responses)==1, [(r.status_code,r.text) for r in responses]
    assert all(r.status_code in (201,409) for r in responses)
    async with TestSession() as db:
        row=await db.scalar(select(SeatAvailability).where(SeatAvailability.train_id==train_id,SeatAvailability.class_id==class_id,SeatAvailability.journey_date==journey_date))
        assert row.available_seats==0
