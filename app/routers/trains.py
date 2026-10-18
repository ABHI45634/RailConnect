from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.dependencies import get_current_admin
from app.models.train import Train
from app.models.station import Station
from app.models.route import Route
from app.models.train_class import TrainClass
from app.models.seat_availability import SeatAvailability
from app.models.user import User
from app.schemas.train import TrainCreate, TrainRead, TrainClassCreate, TrainClassRead, RouteCreate, RouteRead, AvailabilityRead
from app.services.availability_service import read_availability
router = APIRouter(prefix="/trains", tags=["Trains"])
@router.get("", response_model=list[TrainRead])
async def list_trains(db: AsyncSession = Depends(get_db)):
    """List all trains."""
    return list((await db.scalars(select(Train).order_by(Train.train_number))).all())
@router.get("/search", response_model=list[TrainRead])
async def search_trains(source: str = Query(..., min_length=2), destination: str = Query(..., min_length=2), journey_date: date = Query(..., alias="date"), class_type: str | None = Query(None, alias="class"), db: AsyncSession = Depends(get_db)):
    """Search trains that call at source before destination and optionally include a class."""
    if journey_date < date.today(): raise HTTPException(400, "Search date cannot be in the past")
    src = await db.scalar(select(Station).where(Station.station_code == source.upper()))
    dst = await db.scalar(select(Station).where(Station.station_code == destination.upper()))
    if src is None or dst is None: raise HTTPException(404, "Source or destination station code not found")
    source_routes = select(Route.train_id, Route.stop_sequence).where(Route.station_id == src.station_id).subquery()
    dest_routes = select(Route.train_id, Route.stop_sequence).where(Route.station_id == dst.station_id).subquery()
    query = select(Train).join(source_routes, Train.train_id == source_routes.c.train_id).join(dest_routes, Train.train_id == dest_routes.c.train_id).where(source_routes.c.stop_sequence < dest_routes.c.stop_sequence)
    if class_type:
        query = query.join(TrainClass, TrainClass.train_id == Train.train_id).where(TrainClass.class_type == class_type.upper())
    return list((await db.scalars(query.distinct().order_by(Train.train_number))).all())
@router.get("/{train_id}", response_model=TrainRead)
async def get_train(train_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a train by its primary key."""
    train = await db.get(Train, train_id)
    if train is None: raise HTTPException(404, "Train not found")
    return train
@router.post("", response_model=TrainRead, status_code=201)
async def create_train(payload: TrainCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Create a train after validating both endpoint stations."""
    for sid in [payload.source_station_id, payload.destination_station_id]:
        if await db.get(Station, sid) is None: raise HTTPException(400, f"Station {sid} does not exist")
    train = Train(**payload.model_dump()); db.add(train)
    try: await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "Train number already exists")
    await db.refresh(train); return train
@router.put("/{train_id}", response_model=TrainRead)
async def update_train(train_id: int, payload: TrainCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Update train master data."""
    train = await db.get(Train, train_id)
    if train is None: raise HTTPException(404, "Train not found")
    for sid in [payload.source_station_id, payload.destination_station_id]:
        if await db.get(Station, sid) is None: raise HTTPException(400, f"Station {sid} does not exist")
    for key, value in payload.model_dump().items(): setattr(train, key, value)
    try: await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "Train number already exists")
    await db.refresh(train); return train
@router.delete("/{train_id}")
async def delete_train(train_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Delete a train that is not referenced by historical bookings."""
    train = await db.get(Train, train_id)
    if train is None: raise HTTPException(404, "Train not found")
    await db.delete(train)
    try: await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "Train has historical bookings and cannot be deleted")
    return {"message": "Train deleted"}
@router.post("/{train_id}/classes", response_model=TrainClassRead, status_code=201)
async def add_class(train_id: int, payload: TrainClassCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Add a travel class and materialize inventory for the next 30 days."""
    if await db.get(Train, train_id) is None: raise HTTPException(404, "Train not found")
    cls = TrainClass(train_id=train_id, **payload.model_dump()); db.add(cls)
    try:
        await db.flush()
        for offset in range(30): db.add(SeatAvailability(train_id=train_id, class_id=cls.class_id, journey_date=date.today()+timedelta(days=offset), available_seats=cls.total_seats, version=0))
        await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "This train already has that class type")
    await db.refresh(cls); return cls
@router.post("/{train_id}/routes", response_model=RouteRead, status_code=201)
async def add_route(train_id: int, payload: RouteCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Add a stop to a train's route in order of stop_sequence."""
    if await db.get(Train, train_id) is None: raise HTTPException(404, "Train not found")
    if await db.get(Station, payload.station_id) is None: raise HTTPException(404, "Station not found")
    row = Route(train_id=train_id, **payload.model_dump()); db.add(row)
    try: await db.commit()
    except IntegrityError:
        await db.rollback(); raise HTTPException(409, "Route sequence conflicts with an existing stop")
    await db.refresh(row); return row
@router.get("/{train_id}/availability", response_model=AvailabilityRead)
async def availability(train_id: int, journey_date: date = Query(..., alias="date"), class_type: str = Query(..., alias="class"), db: AsyncSession = Depends(get_db)):
    """Return available seats for a given train class and date."""
    if journey_date < date.today(): raise HTTPException(400, "Journey date cannot be in the past")
    train = await db.get(Train, train_id)
    if train is None: raise HTTPException(404, "Train not found")
    cls = await db.scalar(select(TrainClass).where(TrainClass.train_id == train_id, TrainClass.class_type == class_type.upper()))
    if cls is None: raise HTTPException(404, "Class not found")
    row = await read_availability(db, train_id, cls.class_id, journey_date)
    await db.commit()
    return AvailabilityRead(train_id=train_id, class_id=cls.class_id, class_type=cls.class_type, journey_date=journey_date, available_seats=row.available_seats)
