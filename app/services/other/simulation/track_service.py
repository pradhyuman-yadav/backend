"""
Service for managing train tracks.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.services.other.simulation.models import Track

logger = logging.getLogger(__name__)


class TrackService:
    """Service for track CRUD operations."""

    @staticmethod
    def create_track(
        db: Session,
        name: str,
        start_station_id: int,
        end_station_id: int,
        length_km: float,
        gauge: str,
        max_speed_kmh: int,
        track_condition: str,
        track_type: str,
        single_or_double_track: str,
        bidirectional: bool = True,
        electrified: bool = False
    ) -> Optional[Track]:
        """Create a new track."""
        try:
            track = Track(
                name=name,
                start_station_id=start_station_id,
                end_station_id=end_station_id,
                length_km=length_km,
                gauge=gauge,
                max_speed_kmh=max_speed_kmh,
                track_condition=track_condition,
                track_type=track_type,
                single_or_double_track=single_or_double_track,
                bidirectional=bidirectional,
                electrified=electrified
            )
            db.add(track)
            db.commit()
            db.refresh(track)
            logger.info(f"Created track: {name} (ID: {track.track_id})")
            return track
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Track creation failed (integrity error): {str(e)}")
            raise ValueError(f"Track with name '{name}' already exists or invalid station IDs")
        except Exception as e:
            db.rollback()
            logger.error(f"Track creation failed: {str(e)}")
            raise

    @staticmethod
    def get_track(db: Session, track_id: int) -> Optional[Track]:
        """Get a track by ID."""
        return db.query(Track).filter(Track.track_id == track_id).first()

    @staticmethod
    def get_all_tracks(db: Session) -> List[Track]:
        """Get all tracks."""
        return db.query(Track).all()

    @staticmethod
    def get_tracks_by_station(db: Session, station_id: int) -> List[Track]:
        """Get all tracks connected to a station."""
        return db.query(Track).filter(
            (Track.start_station_id == station_id) | (Track.end_station_id == station_id)
        ).all()

    @staticmethod
    def update_track(db: Session, track_id: int, **kwargs) -> Optional[Track]:
        """Update a track."""
        track = TrackService.get_track(db, track_id)
        if not track:
            return None

        try:
            for key, value in kwargs.items():
                if hasattr(track, key):
                    setattr(track, key, value)
            db.commit()
            db.refresh(track)
            logger.info(f"Updated track: {track.name}")
            return track
        except Exception as e:
            db.rollback()
            logger.error(f"Track update failed: {str(e)}")
            raise

    @staticmethod
    def delete_track(db: Session, track_id: int) -> bool:
        """Delete a track."""
        track = TrackService.get_track(db, track_id)
        if not track:
            return False

        try:
            db.delete(track)
            db.commit()
            logger.info(f"Deleted track: {track.name}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Track deletion failed: {str(e)}")
            raise
