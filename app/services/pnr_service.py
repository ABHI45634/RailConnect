import secrets
import string
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.booking import Booking
_ALPHABET = string.ascii_uppercase + string.digits

async def generate_unique_pnr(db: AsyncSession) -> str:
    """Generate a cryptographically random unique ten-character PNR, retrying collisions."""
    for _ in range(10):
        candidate = ''.join(secrets.choice(_ALPHABET) for _ in range(10))
        exists = await db.scalar(select(Booking.booking_id).where(Booking.pnr == candidate))
        if exists is None:
            return candidate
    raise HTTPException(503, "Could not allocate a unique PNR; please retry")

async def lookup_pnr(db: AsyncSession, pnr: str) -> Booking:
    """Return a booking by PNR with passengers loaded, or a 404 error."""
    result = await db.execute(select(Booking).where(Booking.pnr == pnr.upper()))
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(404, "PNR not found")
    return booking
