"""
Service for managing trains.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.services.other.simulation.models import Train
from datetime import datetime

logger = logging.getLogger(__name__)


class TrainService:
    """Service for train CRUD operations."""

    @staticmethod
    def create_train(
        db: Session,
        name: str,
        route_id: int,
        train_type: str,
        total_weight_kg: int,
        max_speed_kmh: int,
        gauge: str,
        passenger_capacity: int = 0,
        cargo_capacity_kg: int = 0,
        scheduled_departure: Optional[datetime] = None,
        scheduled_arrival: Optional[datetime] = None
    ) -> Optional[Train]:
        """Create a new train with capacity properties."""
        try:
            train = Train(
                name=name,
                route_id=route_id,
                train_type=train_type,
                total_weight_kg=total_weight_kg,
                max_speed_kmh=max_speed_kmh,
                gauge=gauge,
                passenger_capacity=passenger_capacity,
                cargo_capacity_kg=cargo_capacity_kg,
                scheduled_departure=scheduled_departure,
                scheduled_arrival=scheduled_arrival,
                status="scheduled"
            )

            db.add(train)
            db.commit()
            db.refresh(train)
            logger.info(f"Created train: {name} (ID: {train.train_id})")
            return train
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Train creation failed (integrity error): {str(e)}")
            raise ValueError(f"Train with name '{name}' already exists")
        except Exception as e:
            db.rollback()
            logger.error(f"Train creation failed: {str(e)}")
            raise

    @staticmethod
    def get_train(db: Session, train_id: int) -> Optional[Train]:
        """Get a train by ID."""
        return db.query(Train).filter(Train.train_id == train_id).first()

    @staticmethod
    def get_train_by_name(db: Session, name: str) -> Optional[Train]:
        """Get a train by name."""
        return db.query(Train).filter(Train.name == name).first()

    @staticmethod
    def get_all_trains(db: Session) -> List[Train]:
        """Get all trains."""
        return db.query(Train).all()

    @staticmethod
    def get_trains_by_route(db: Session, route_id: int) -> List[Train]:
        """Get all trains on a specific route."""
        return db.query(Train).filter(Train.route_id == route_id).all()

    @staticmethod
    def get_trains_by_status(db: Session, status: str) -> List[Train]:
        """Get all trains with specific status."""
        return db.query(Train).filter(Train.status == status).all()

    @staticmethod
    def update_train(db: Session, train_id: int, **kwargs) -> Optional[Train]:
        """Update a train."""
        train = TrainService.get_train(db, train_id)
        if not train:
            return None

        try:
            for key, value in kwargs.items():
                if hasattr(train, key):
                    setattr(train, key, value)
            db.commit()
            db.refresh(train)
            logger.info(f"Updated train: {train.name}")
            return train
        except Exception as e:
            db.rollback()
            logger.error(f"Train update failed: {str(e)}")
            raise

    @staticmethod
    def delete_train(db: Session, train_id: int) -> bool:
        """Delete a train."""
        train = TrainService.get_train(db, train_id)
        if not train:
            return False

        try:
            db.delete(train)
            db.commit()
            logger.info(f"Deleted train: {train.name}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Train deletion failed: {str(e)}")
            raise
