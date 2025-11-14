"""
Service for managing train stations.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.services.other.simulation.models import Station

logger = logging.getLogger(__name__)


class StationService:
    """Service for station CRUD operations."""

    @staticmethod
    def create_station(
        db: Session,
        name: str,
        latitude: float,
        longitude: float,
        elevation_m: int,
        capacity: int,
        num_platforms: int,
        station_type: str,
        has_signals: bool = False,
        has_water_supply: bool = False,
        has_fuel_supply: bool = False
    ) -> Optional[Station]:
        """Create a new station."""
        try:
            station = Station(
                name=name,
                latitude=latitude,
                longitude=longitude,
                elevation_m=elevation_m,
                capacity=capacity,
                num_platforms=num_platforms,
                station_type=station_type,
                has_signals=has_signals,
                has_water_supply=has_water_supply,
                has_fuel_supply=has_fuel_supply
            )
            db.add(station)
            db.commit()
            db.refresh(station)
            logger.info(f"Created station: {name} (ID: {station.station_id})")
            return station
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Station creation failed (integrity error): {str(e)}")
            raise ValueError(f"Station with name '{name}' already exists")
        except Exception as e:
            db.rollback()
            logger.error(f"Station creation failed: {str(e)}")
            raise

    @staticmethod
    def get_station(db: Session, station_id: int) -> Optional[Station]:
        """Get a station by ID."""
        return db.query(Station).filter(Station.station_id == station_id).first()

    @staticmethod
    def get_station_by_name(db: Session, name: str) -> Optional[Station]:
        """Get a station by name."""
        return db.query(Station).filter(Station.name == name).first()

    @staticmethod
    def get_all_stations(db: Session) -> List[Station]:
        """Get all stations."""
        return db.query(Station).all()

    @staticmethod
    def get_stations_by_type(db: Session, station_type: str) -> List[Station]:
        """Get all stations of a specific type."""
        return db.query(Station).filter(Station.station_type == station_type).all()

    @staticmethod
    def update_station(db: Session, station_id: int, **kwargs) -> Optional[Station]:
        """Update a station."""
        station = StationService.get_station(db, station_id)
        if not station:
            return None

        try:
            for key, value in kwargs.items():
                if hasattr(station, key):
                    setattr(station, key, value)
            db.commit()
            db.refresh(station)
            logger.info(f"Updated station: {station.name}")
            return station
        except Exception as e:
            db.rollback()
            logger.error(f"Station update failed: {str(e)}")
            raise

    @staticmethod
    def delete_station(db: Session, station_id: int) -> bool:
        """Delete a station."""
        station = StationService.get_station(db, station_id)
        if not station:
            return False

        try:
            db.delete(station)
            db.commit()
            logger.info(f"Deleted station: {station.name}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Station deletion failed: {str(e)}")
            raise
