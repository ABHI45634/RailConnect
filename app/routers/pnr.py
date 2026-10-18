from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.booking import PNRRead
from app.services.pnr_service import lookup_pnr
router = APIRouter(prefix="/pnr", tags=["PNR"])
@router.get("/{pnr}", response_model=PNRRead)
async def pnr_status(pnr: str, db: AsyncSession = Depends(get_db)):
    """Expose the limited passenger and status information available to PNR lookups."""
    booking = await lookup_pnr(db, pnr)
    await db.refresh(booking, attribute_names=["passengers"])
    return PNRRead(pnr=booking.pnr, booking_id=booking.booking_id, train_id=booking.train_id, journey_date=booking.journey_date, status=booking.status, passengers=booking.passengers)
