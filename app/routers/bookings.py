from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingRead
from app.services.booking_service import create_booking, cancel_booking, get_user_booking
router = APIRouter(prefix="/bookings", tags=["Bookings"])
@router.post("", response_model=BookingRead, status_code=201)
async def book(payload: BookingCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Create a booking using the transactional booking service."""
    return await create_booking(db, user, payload)
@router.get("/my", response_model=list[BookingRead])
async def my_bookings(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """List bookings for the currently authenticated user."""
    result = await db.execute(select(Booking).where(Booking.user_id == user.user_id).order_by(Booking.booking_date.desc()))
    bookings = list(result.scalars().all())
    for booking in bookings: await db.refresh(booking, attribute_names=["passengers"])
    return bookings
@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Return a booking only to its owner or an administrator."""
    return await get_user_booking(db, booking_id, user)
@router.delete("/{booking_id}", response_model=BookingRead)
async def cancel(booking_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Cancel a booking and restore or promote inventory through service logic."""
    return await cancel_booking(db, booking_id, user)
