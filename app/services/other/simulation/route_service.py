"""
Service for managing train routes.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.services.other.simulation.models import Route

logger = logging.getLogger(__name__)


class RouteService:
    """Service for route CRUD operations."""

    @staticmethod
    def create_route(
        db: Session,
        name: str,
        waypoints: list,  # List of {station_id, order, planned_arrival_time, planned_departure_time}
        total_distance_km: float,
        estimated_duration_hours: float,
        frequency: str,
        description: Optional[str] = None
    ) -> Optional[Route]:
        """Create a new route."""
        try:
            route = Route(
                name=name,
                waypoints=waypoints,
                total_distance_km=total_distance_km,
                estimated_duration_hours=estimated_duration_hours,
                frequency=frequency,
                description=description
            )
            db.add(route)
            db.commit()
            db.refresh(route)
            logger.info(f"Created route: {name} (ID: {route.route_id})")
            return route
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Route creation failed (integrity error): {str(e)}")
            raise ValueError(f"Route with name '{name}' already exists")
        except Exception as e:
            db.rollback()
            logger.error(f"Route creation failed: {str(e)}")
            raise

    @staticmethod
    def get_route(db: Session, route_id: int) -> Optional[Route]:
        """Get a route by ID."""
        return db.query(Route).filter(Route.route_id == route_id).first()

    @staticmethod
    def get_route_by_name(db: Session, name: str) -> Optional[Route]:
        """Get a route by name."""
        return db.query(Route).filter(Route.name == name).first()

    @staticmethod
    def get_all_routes(db: Session) -> List[Route]:
        """Get all routes."""
        return db.query(Route).all()

    @staticmethod
    def get_routes_by_frequency(db: Session, frequency: str) -> List[Route]:
        """Get all routes with specific frequency."""
        return db.query(Route).filter(Route.frequency == frequency).all()

    @staticmethod
    def update_route(db: Session, route_id: int, **kwargs) -> Optional[Route]:
        """Update a route."""
        route = RouteService.get_route(db, route_id)
        if not route:
            return None

        try:
            for key, value in kwargs.items():
                if hasattr(route, key):
                    setattr(route, key, value)
            db.commit()
            db.refresh(route)
            logger.info(f"Updated route: {route.name}")
            return route
        except Exception as e:
            db.rollback()
            logger.error(f"Route update failed: {str(e)}")
            raise

    @staticmethod
    def delete_route(db: Session, route_id: int) -> bool:
        """Delete a route."""
        route = RouteService.get_route(db, route_id)
        if not route:
            return False

        try:
            db.delete(route)
            db.commit()
            logger.info(f"Deleted route: {route.name}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Route deletion failed: {str(e)}")
            raise
