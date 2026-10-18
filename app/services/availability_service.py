from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.seat_availability import SeatAvailability
from app.models.train_class import TrainClass

async def get_or_create_availability(db: AsyncSession, train_id: int, class_id: int, journey_date: date, *, lock: bool = False) -> SeatAvailability:
    """Fetch the daily inventory row, optionally locking it to serialize bookings."""
    query = select(SeatAvailability).where(SeatAvailability.train_id == train_id, SeatAvailability.class_id == class_id, SeatAvailability.journey_date == journey_date)
    if lock:
        query = query.with_for_update()
    result = await db.execute(query)
    row = result.scalar_one_or_none()
    if row is None:
        cls = await db.get(TrainClass, class_id)
        if cls is None or cls.train_id != train_id:
            raise HTTPException(404, "Train class not found for this train")
        # The booking service holds a FOR UPDATE lock on the parent class, which serializes
        # first-time inventory creation for this train/class across concurrent transactions.
        row = SeatAvailability(train_id=train_id, class_id=class_id, journey_date=journey_date, available_seats=cls.total_seats, version=0)
        db.add(row)
        await db.flush()
        if lock:
            result = await db.execute(query)
            row = result.scalar_one()
    return row

async def read_availability(db: AsyncSession, train_id: int, class_id: int, journey_date: date) -> SeatAvailability:
    """Read current availability, creating the initial inventory row if necessary."""
    return await get_or_create_availability(db, train_id, class_id, journey_date)
