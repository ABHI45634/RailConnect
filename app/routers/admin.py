from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.dependencies import get_current_admin
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingRead
from app.schemas.user import UserRead
router = APIRouter(prefix="/admin", tags=["Administration"])
@router.get("/bookings", response_model=list[BookingRead])
async def all_bookings(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """List all bookings; admin-only endpoint."""
    rows = list((await db.scalars(select(Booking).order_by(Booking.booking_date.desc()))).all())
    for row in rows: await db.refresh(row, attribute_names=["passengers"])
    return rows
@router.get("/users", response_model=list[UserRead])
async def all_users(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """List user profiles without password hashes; admin-only endpoint."""
    return list((await db.scalars(select(User).order_by(User.user_id))).all())
