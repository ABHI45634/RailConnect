from datetime import date, timedelta
import pytest
from app.seed import seed
from sqlalchemy import select
from app.models import User, Train, TrainClass, SeatAvailability
@pytest.mark.asyncio
async def test_booking_and_cancellation(client):
    await seed()
    token=(await client.post("/auth/login",json={"email":"passenger1@train.com","password":"Passenger@123"})).json()["access_token"]
    headers={"Authorization":f"Bearer {token}"}
    train_id=1
    # Read the seed class for the train.
    av=await client.get(f"/trains/{train_id}/availability",params={"date":str(date.today()+timedelta(days=1)),"class":"SL"})
    assert av.status_code==200, av.text
    class_id=av.json()["class_id"]
    payload={"train_id":train_id,"class_id":class_id,"journey_date":str(date.today()+timedelta(days=1)),"passengers":[{"name":"Test Passenger","age":22,"gender":"F"}],"payment_method":"UPI"}
    booked=await client.post("/bookings",json=payload,headers=headers)
    assert booked.status_code==201, booked.text
    assert len(booked.json()["pnr"])==10
    pnr=await client.get(f"/pnr/{booked.json()['pnr']}")
    assert pnr.status_code==200
    cancel=await client.delete(f"/bookings/{booked.json()['booking_id']}",headers=headers)
    assert cancel.status_code==200 and cancel.json()["status"]=="CANCELLED"
@pytest.mark.asyncio
async def test_insufficient_seats_returns_conflict_when_waiting_disabled(client, monkeypatch):
    await seed()
    from app.config import settings
    monkeypatch.setattr(settings,"allow_waiting_list",False)
    token=(await client.post("/auth/login",json={"email":"passenger1@train.com","password":"Passenger@123"})).json()["access_token"]
    headers={"Authorization":f"Bearer {token}"}
    train_id=1; journey_date=date.today()+timedelta(days=1)
    av=(await client.get(f"/trains/{train_id}/availability",params={"date":str(journey_date),"class":"SL"})).json()
    # Force inventory to zero in the test database.
    from tests.conftest import TestSession
    async with TestSession() as db:
        row=await db.scalar(select(SeatAvailability).where(SeatAvailability.train_id==train_id,SeatAvailability.class_id==av["class_id"],SeatAvailability.journey_date==journey_date))
        row.available_seats=0; await db.commit()
    payload={"train_id":train_id,"class_id":av["class_id"],"journey_date":str(journey_date),"passengers":[{"name":"Test Passenger","age":22,"gender":"F"}]}
    r=await client.post("/bookings",json=payload,headers=headers)
    assert r.status_code==409
