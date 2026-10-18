import logging
import secrets
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.passenger import Passenger, PassengerStatus
from app.models.payment import Payment, PaymentStatus
from app.models.seat_availability import SeatAvailability
from app.models.train import Train
from app.models.train_class import TrainClass
from app.models.route import Route
from app.models.user import User
from app.schemas.booking import BookingCreate
from app.services.availability_service import get_or_create_availability
from app.services.fare_service import calculate_fare
from app.services.pnr_service import generate_unique_pnr

logger = logging.getLogger(__name__)

async def create_booking(db: AsyncSession, user: User, payload: BookingCreate) -> Booking:
    """Atomically lock inventory, validate it, allocate seats, and persist booking, passengers, and payment."""
    if payload.journey_date < date.today():
        raise HTTPException(400, "Journey date cannot be in the past")
    # The request-scoped session is normally idle here. Explicit transaction scope keeps every write atomic.
    async with db.begin():
        train = await db.get(Train, payload.train_id)
        cls = await db.get(TrainClass, payload.class_id)
        if train is None:
            raise HTTPException(404, "Train not found")
        if cls is None or cls.train_id != train.train_id:
            raise HTTPException(400, "Class does not belong to the selected train")
        # Lock the parent class first to serialize first-time inventory row creation, then lock the inventory row.
        await db.execute(select(TrainClass.class_id).where(TrainClass.class_id == cls.class_id).with_for_update())
        inventory = await get_or_create_availability(db, train.train_id, cls.class_id, payload.journey_date, lock=True)
        count = len(payload.passengers)
        confirmed_count = min(inventory.available_seats, count)
        waiting_count = count - confirmed_count
        if waiting_count and not settings.allow_waiting_list:
            logger.warning("Booking rejected for insufficient inventory train=%s date=%s requested=%s available=%s", train.train_id, payload.journey_date, count, inventory.available_seats)
            raise HTTPException(409, f"Only {inventory.available_seats} seat(s) available; requested {count}")
        # Fare is for the actual train's source-to-destination endpoints as specified by this project schema.
        fare = await calculate_fare(db, train.train_id, cls.class_id, train.source_station_id, train.destination_station_id, count)
        pnr = await generate_unique_pnr(db)
        status_value = BookingStatus.WAITING if confirmed_count == 0 else BookingStatus.CONFIRMED
        booking = Booking(pnr=pnr, user_id=user.user_id, train_id=train.train_id, class_id=cls.class_id, journey_date=payload.journey_date, total_fare=fare, status=status_value)
        db.add(booking)
        await db.flush()
        remaining_confirmed = confirmed_count
        for i, item in enumerate(payload.passengers, start=1):
            if remaining_confirmed > 0:
                passenger_status = PassengerStatus.CONFIRMED
                seat_number = f"{cls.class_type.value}-{cls.total_seats - inventory.available_seats + i:04d}"
                remaining_confirmed -= 1
            else:
                passenger_status = PassengerStatus.WAITING
                seat_number = None
            db.add(Passenger(booking_id=booking.booking_id, name=item.name, age=item.age, gender=item.gender, seat_number=seat_number, status=passenger_status))
        inventory.available_seats -= confirmed_count
        inventory.version += 1
        if inventory.available_seats < 0:
            raise HTTPException(409, "Seat inventory changed; please retry")
        db.add(Payment(booking_id=booking.booking_id, amount=fare, payment_method=payload.payment_method, transaction_id=f"DEMO-{secrets.token_hex(8).upper()}", status=PaymentStatus.SUCCESS))
        await db.flush()
        await db.refresh(booking)
        await db.refresh(booking, attribute_names=["passengers"])
        logger.info("Booking created booking_id=%s pnr=%s user_id=%s status=%s", booking.booking_id, booking.pnr, user.user_id, booking.status.value)
        return booking

async def cancel_booking(db: AsyncSession, booking_id: int, user: User) -> Booking:
    """Cancel a booking under a row lock, restore confirmed seats, and promote earliest waiting booking."""
    async with db.begin():
        result = await db.execute(select(Booking).where(Booking.booking_id == booking_id).with_for_update())
        booking = result.scalar_one_or_none()
        if booking is None:
            raise HTTPException(404, "Booking not found")
        from app.models.user import UserRole
        if booking.user_id != user.user_id and user.role != UserRole.ADMIN:
            raise HTTPException(403, "You may cancel only your own bookings")
        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(409, "Booking is already cancelled")
        p_result = await db.execute(select(Passenger).where(Passenger.booking_id == booking.booking_id).with_for_update())
        passengers = list(p_result.scalars().all())
        inventory_result = await db.execute(select(SeatAvailability).where(SeatAvailability.train_id == booking.train_id, SeatAvailability.class_id == booking.class_id, SeatAvailability.journey_date == booking.journey_date).with_for_update())
        inventory = inventory_result.scalar_one_or_none()
        confirmed = sum(p.status == PassengerStatus.CONFIRMED for p in passengers)
        for p in passengers:
            p.status = PassengerStatus.CANCELLED
            p.seat_number = None
        booking.status = BookingStatus.CANCELLED
        if inventory is not None and confirmed:
            cls = await db.get(TrainClass, booking.class_id)
            capacity = cls.total_seats if cls else inventory.available_seats + confirmed
            inventory.available_seats = min(capacity, inventory.available_seats + confirmed)
            inventory.version += 1
        waiting_result = await db.execute(select(Booking).where(Booking.train_id == booking.train_id, Booking.class_id == booking.class_id, Booking.journey_date == booking.journey_date, Booking.status == BookingStatus.WAITING, Booking.booking_id != booking.booking_id).order_by(Booking.booking_date, Booking.booking_id).with_for_update())
        waiting_bookings = list(waiting_result.scalars().all())
        available = inventory.available_seats if inventory else 0
        for waiting_booking in waiting_bookings:
            wait_result = await db.execute(select(Passenger).where(Passenger.booking_id == waiting_booking.booking_id).with_for_update())
            waiters = [p for p in wait_result.scalars().all() if p.status == PassengerStatus.WAITING]
            if not waiters:
                waiting_booking.status = BookingStatus.CONFIRMED
                continue
            if len(waiters) <= available:
                for p in waiters:
                    p.status = PassengerStatus.CONFIRMED
                    p.seat_number = f"PROM-{p.passenger_id:04d}"
                available -= len(waiters)
                waiting_booking.status = BookingStatus.CONFIRMED
            else:
                break
        if inventory is not None:
            inventory.available_seats = available
            inventory.version += 1
        await db.flush()
        await db.refresh(booking)
        await db.refresh(booking, attribute_names=["passengers"])
        logger.info("Booking cancelled booking_id=%s pnr=%s", booking.booking_id, booking.pnr)
        return booking

async def get_user_booking(db: AsyncSession, booking_id: int, user: User) -> Booking:
    """Fetch a booking if the requesting user owns it or is an administrator."""
    from app.models.user import UserRole
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    if booking.user_id != user.user_id and user.role != UserRole.ADMIN:
        raise HTTPException(403, "You may view only your own bookings")
    await db.refresh(booking, attribute_names=["passengers"])
    return booking
