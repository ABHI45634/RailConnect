from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.route import Route
from app.models.train_class import TrainClass

async def calculate_fare(db: AsyncSession, train_id: int, class_id: int, source_station_id: int, destination_station_id: int, passenger_count: int) -> Decimal:
    """Calculate fare using the route-distance difference and class rate per kilometre."""
    result = await db.execute(select(Route).where(Route.train_id == train_id, Route.station_id.in_([source_station_id, destination_station_id])))
    routes = {r.station_id: r for r in result.scalars().all()}
    if source_station_id not in routes or destination_station_id not in routes:
        raise HTTPException(400, "The selected journey endpoints are not both on this train's route")
    source, destination = routes[source_station_id], routes[destination_station_id]
    if source.stop_sequence >= destination.stop_sequence:
        raise HTTPException(400, "Destination must occur after source on this train's route")
    distance = destination.distance_from_source - source.distance_from_source
    cls = await db.get(TrainClass, class_id)
    if cls is None or cls.train_id != train_id:
        raise HTTPException(400, "Class does not belong to the selected train")
    return (Decimal(distance) * Decimal(cls.fare_per_km) * passenger_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
