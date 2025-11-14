"""
Service for managing passengers and passenger operations.
"""
import logging
import random
from typing import List, Optional
from sqlalchemy.orm import Session
from app.services.other.simulation.models import Passenger, Station, Train
from datetime import datetime

logger = logging.getLogger(__name__)


class PassengerService:
    """Service for passenger CRUD operations and management."""

    @staticmethod
    def create_passenger(
        db: Session,
        origin_station_id: int,
        destination_station_id: int,
        current_station_id: int
    ) -> Optional[Passenger]:
        """Create a new passenger waiting at a station."""
        try:
            # Verify stations exist
            origin = db.query(Station).filter(Station.station_id == origin_station_id).first()
            destination = db.query(Station).filter(Station.station_id == destination_station_id).first()
            current = db.query(Station).filter(Station.station_id == current_station_id).first()

            if not origin or not destination or not current:
                raise ValueError("One or more stations not found")

            if origin_station_id == destination_station_id:
                raise ValueError("Origin and destination stations must be different")

            passenger = Passenger(
                origin_station_id=origin_station_id,
                destination_station_id=destination_station_id,
                current_station_id=current_station_id,
                status="waiting"
            )

            db.add(passenger)
            db.commit()
            db.refresh(passenger)
            logger.info(f"Created passenger {passenger.passenger_id} at station {current_station_id}")
            return passenger
        except Exception as e:
            db.rollback()
            logger.error(f"Passenger creation failed: {str(e)}")
            raise

    @staticmethod
    def get_passenger(db: Session, passenger_id: int) -> Optional[Passenger]:
        """Get a passenger by ID."""
        return db.query(Passenger).filter(Passenger.passenger_id == passenger_id).first()

    @staticmethod
    def get_all_passengers(db: Session) -> List[Passenger]:
        """Get all passengers."""
        return db.query(Passenger).all()

    @staticmethod
    def get_waiting_passengers_at_station(db: Session, station_id: int) -> List[Passenger]:
        """Get all passengers waiting at a specific station."""
        return db.query(Passenger).filter(
            Passenger.current_station_id == station_id,
            Passenger.status == "waiting"
        ).all()

    @staticmethod
    def get_passengers_on_train(db: Session, train_id: int) -> List[Passenger]:
        """Get all passengers on a specific train."""
        return db.query(Passenger).filter(
            Passenger.boarded_train_id == train_id,
            Passenger.status == "boarded"
        ).all()

    @staticmethod
    def get_passengers_getting_off_at_station(db: Session, train_id: int, station_id: int) -> List[Passenger]:
        """Get all passengers on a train who need to get off at this station."""
        return db.query(Passenger).filter(
            Passenger.boarded_train_id == train_id,
            Passenger.destination_station_id == station_id,
            Passenger.status == "boarded"
        ).all()

    @staticmethod
    def board_passenger(db: Session, passenger_id: int, train_id: int, current_time: datetime) -> Optional[Passenger]:
        """Board a passenger onto a train."""
        passenger = PassengerService.get_passenger(db, passenger_id)
        if not passenger or passenger.status != "waiting":
            return None

        try:
            passenger.boarded_train_id = train_id
            passenger.status = "boarded"
            passenger.boarding_time = current_time
            db.commit()
            db.refresh(passenger)
            logger.info(f"Passenger {passenger_id} boarded train {train_id}")
            return passenger
        except Exception as e:
            db.rollback()
            logger.error(f"Boarding failed: {str(e)}")
            raise

    @staticmethod
    def deboard_passenger(db: Session, passenger_id: int, station_id: int, current_time: datetime) -> Optional[Passenger]:
        """Deboard a passenger from a train at their destination."""
        passenger = PassengerService.get_passenger(db, passenger_id)
        if not passenger or passenger.status != "boarded":
            return None

        try:
            passenger.boarded_train_id = None
            passenger.current_station_id = station_id
            passenger.status = "arrived"
            passenger.arrival_time = current_time
            db.commit()
            db.refresh(passenger)
            logger.info(f"Passenger {passenger_id} deboarded at station {station_id}")
            return passenger
        except Exception as e:
            db.rollback()
            logger.error(f"Deboarding failed: {str(e)}")
            raise

    @staticmethod
    def generate_passengers_at_station(
        db: Session,
        station_id: int,
        num_passengers: int,
        all_stations: List[Station]
    ) -> List[Passenger]:
        """Generate random passengers at a station with random destinations."""
        if not all_stations or len(all_stations) < 2:
            return []

        created_passengers = []
        try:
            for _ in range(num_passengers):
                # Pick a random destination station (different from origin)
                destination = random.choice([s for s in all_stations if s.station_id != station_id])

                passenger = Passenger(
                    origin_station_id=station_id,
                    destination_station_id=destination.station_id,
                    current_station_id=station_id,
                    status="waiting"
                )
                db.add(passenger)
                created_passengers.append(passenger)

            db.commit()
            logger.info(f"Generated {num_passengers} passengers at station {station_id}")
            return created_passengers
        except Exception as e:
            db.rollback()
            logger.error(f"Passenger generation failed: {str(e)}")
            raise

    @staticmethod
    def delete_passenger(db: Session, passenger_id: int) -> bool:
        """Delete a passenger."""
        passenger = PassengerService.get_passenger(db, passenger_id)
        if not passenger:
            return False

        try:
            db.delete(passenger)
            db.commit()
            logger.info(f"Deleted passenger {passenger_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Passenger deletion failed: {str(e)}")
            raise
