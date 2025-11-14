"""
API routers for train simulation system.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.middleware.auth import verify_api_key
from app.services.other.simulation.database import get_db_session
from app.services.other.simulation.track_service import TrackService
from app.services.other.simulation.station_service import StationService
from app.services.other.simulation.train_service import TrainService
from app.services.other.simulation.route_service import RouteService
from app.services.other.simulation.simulation_engine import SimulationEngine
from app.services.other.simulation.passenger_service import PassengerService
from app.schemas.simulation import (
    TrackSchema, StationSchema, RouteSchema, TrainSchema,
    TrainDetailSchema, TrainStatusResponse, StationStatusResponse,
    SimulationStatusResponse, TrackPatchSchema, StationPatchSchema,
    RoutePatchSchema, TrainPatchSchema, PassengerSchema
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation/train", tags=["Train Simulation"])


# ==================== INFRASTRUCTURE (TRACKS) ====================

@router.post("/infra", response_model=TrackSchema)
async def create_track(request: TrackSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Create a new track."""
    try:
        track = TrackService.create_track(
            db, request.name, request.start_station_id, request.end_station_id,
            request.length_km, request.gauge, request.max_speed_kmh,
            request.track_condition, request.track_type, request.single_or_double_track,
            request.bidirectional, request.electrified
        )
        return track
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating track: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create track")


@router.get("/infra", response_model=list[TrackSchema])
async def get_all_tracks(api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get all tracks."""
    return TrackService.get_all_tracks(db)


@router.get("/infra/{track_id}", response_model=TrackSchema)
async def get_track(track_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get a specific track."""
    track = TrackService.get_track(db, track_id)
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return track


@router.put("/infra/{track_id}", response_model=TrackSchema)
async def update_track(track_id: int, request: TrackSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Update a track."""
    track = TrackService.update_track(db, track_id, **request.dict(exclude_unset=True))
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return track


@router.patch("/infra/{track_id}", response_model=TrackSchema)
async def patch_track(track_id: int, request: TrackPatchSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Partially update a track."""
    track = TrackService.update_track(db, track_id, **request.dict(exclude_unset=True))
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return track


@router.delete("/infra/{track_id}")
async def delete_track(track_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Delete a track."""
    if not TrackService.delete_track(db, track_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return {"message": "Track deleted"}


# ==================== STATIONS ====================

@router.post("/station", response_model=StationSchema)
async def create_station(request: StationSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Create a new station."""
    try:
        station = StationService.create_station(
            db, request.name, request.latitude, request.longitude, request.elevation_m,
            request.capacity, request.num_platforms, request.station_type,
            request.has_signals, request.has_water_supply, request.has_fuel_supply
        )
        return station
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating station: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create station")


@router.get("/station", response_model=list[StationSchema])
async def get_all_stations(api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get all stations."""
    return StationService.get_all_stations(db)


@router.get("/station/{station_id}", response_model=StationSchema)
async def get_station(station_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get a specific station."""
    station = StationService.get_station(db, station_id)
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Station not found")
    return station


@router.put("/station/{station_id}", response_model=StationSchema)
async def update_station(station_id: int, request: StationSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Update a station."""
    station = StationService.update_station(db, station_id, **request.dict(exclude_unset=True))
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Station not found")
    return station


@router.patch("/station/{station_id}", response_model=StationSchema)
async def patch_station(station_id: int, request: StationPatchSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Partially update a station."""
    station = StationService.update_station(db, station_id, **request.dict(exclude_unset=True))
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Station not found")
    return station


@router.delete("/station/{station_id}")
async def delete_station(station_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Delete a station."""
    if not StationService.delete_station(db, station_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Station not found")
    return {"message": "Station deleted"}


@router.get("/station/{station_id}/passengers", response_model=list[PassengerSchema])
async def get_station_passengers(station_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get all waiting passengers at a station."""
    passengers = PassengerService.get_waiting_passengers_at_station(db, station_id)
    return passengers


# ==================== ROUTES ====================

@router.post("/route", response_model=RouteSchema)
async def create_route(request: RouteSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Create a new route."""
    try:
        route = RouteService.create_route(
            db, request.name, request.waypoints, request.total_distance_km,
            request.estimated_duration_hours, request.frequency, request.description
        )
        return route
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating route: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create route")


@router.get("/route", response_model=list[RouteSchema])
async def get_all_routes(api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get all routes."""
    return RouteService.get_all_routes(db)


@router.get("/route/{route_id}", response_model=RouteSchema)
async def get_route(route_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get a specific route."""
    route = RouteService.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return route


@router.put("/route/{route_id}", response_model=RouteSchema)
async def update_route(route_id: int, request: RouteSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Update a route."""
    route = RouteService.update_route(db, route_id, **request.dict(exclude_unset=True))
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return route


@router.patch("/route/{route_id}", response_model=RouteSchema)
async def patch_route(route_id: int, request: RoutePatchSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Partially update a route."""
    route = RouteService.update_route(db, route_id, **request.dict(exclude_unset=True))
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return route


@router.delete("/route/{route_id}")
async def delete_route(route_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Delete a route."""
    if not RouteService.delete_route(db, route_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return {"message": "Route deleted"}


# ==================== TRAINS ====================

@router.post("/train", response_model=TrainDetailSchema)
async def create_train(request: TrainSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Create a new train."""
    try:
        train = TrainService.create_train(
            db, request.name, request.route_id, request.train_type, request.total_weight_kg,
            request.max_speed_kmh, request.gauge, request.passenger_capacity, request.cargo_capacity_kg,
            request.scheduled_departure, request.scheduled_arrival
        )
        return train
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating train: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create train")


@router.get("/train", response_model=list[TrainDetailSchema])
async def get_all_trains(api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get all trains."""
    return TrainService.get_all_trains(db)


@router.get("/train/{train_id}", response_model=TrainDetailSchema)
async def get_train(train_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get a specific train with vehicles."""
    train = TrainService.get_train(db, train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    return train


@router.put("/train/{train_id}", response_model=TrainDetailSchema)
async def update_train(train_id: int, request: TrainSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Update a train."""
    train = TrainService.update_train(db, train_id, **request.dict(exclude_unset=True))
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    return train


@router.patch("/train/{train_id}", response_model=TrainDetailSchema)
async def patch_train(train_id: int, request: TrainPatchSchema, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Partially update a train."""
    train = TrainService.update_train(db, train_id, **request.dict(exclude_unset=True))
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    return train


@router.delete("/train/{train_id}")
async def delete_train(train_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Delete a train."""
    if not TrainService.delete_train(db, train_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    return {"message": "Train deleted"}




# ==================== SIMULATION CONTROL ====================
# Simulation runs continuously from app startup - no start/pause/reset endpoints

@router.get("/game/status", response_model=SimulationStatusResponse)
async def get_simulation_status(api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get simulation status."""
    status = SimulationEngine.get_simulation_status(db)
    if not status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not initialized")
    return status


@router.get("/game/trains-status", response_model=list[TrainStatusResponse])
async def get_trains_status(api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get all trains status."""
    return SimulationEngine.get_trains_status(db)


@router.get("/game/stations-status", response_model=list[StationStatusResponse])
async def get_stations_status(api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Get all stations status."""
    return SimulationEngine.get_stations_status(db)


@router.post("/game/step")
async def step_simulation(minutes: int = 60, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db_session)):
    """Advance simulation by specified minutes."""
    try:
        sim_state = SimulationEngine.step_simulation(db, minutes)
        return {"message": f"Simulation advanced by {minutes} minutes", "current_time": sim_state.current_simulated_datetime}
    except Exception as e:
        logger.error(f"Error stepping simulation: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
