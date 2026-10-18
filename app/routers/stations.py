from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.dependencies import get_current_admin
from app.models.station import Station
from app.models.user import User
from app.schemas.train import StationCreate, StationRead
from app.schemas.common import Message
router = APIRouter(prefix="/stations", tags=["Stations"])
@router.get("", response_model=list[StationRead])
async def list_stations(db: AsyncSession = Depends(get_db)):
    """List stations ordered by code for public timetable queries."""
    return list((await db.scalars(select(Station).order_by(Station.station_code))).all())
@router.post("", response_model=StationRead, status_code=201)
async def create_station(payload: StationCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Create a station; only an admin can mutate station data."""
    station = Station(station_name=payload.station_name.strip(), station_code=payload.station_code.upper())
    db.add(station)
    try: await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "Station code already exists")
    await db.refresh(station); return station
@router.put("/{station_id}", response_model=StationRead)
async def update_station(station_id: int, payload: StationCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Update an existing station's display name and code."""
    station = await db.get(Station, station_id)
    if station is None: raise HTTPException(404, "Station not found")
    station.station_name = payload.station_name.strip(); station.station_code = payload.station_code.upper()
    try: await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "Station code already exists")
    await db.refresh(station); return station
@router.delete("/{station_id}", response_model=Message)
async def delete_station(station_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Delete a station when no train or route references it."""
    station = await db.get(Station, station_id)
    if station is None: raise HTTPException(404, "Station not found")
    await db.delete(station)
    try: await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "Station is referenced by a train or route")
    return Message(message="Station deleted")
