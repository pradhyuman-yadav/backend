"""
Pydantic schemas for train simulation endpoints.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TrackSchema(BaseModel):
    track_id: Optional[int] = None
    name: str
    start_station_id: int
    end_station_id: int
    length_km: float
    gauge: str
    max_speed_kmh: int
    track_condition: str
    track_type: str
    single_or_double_track: str
    bidirectional: bool = True
    electrified: bool = False

    class Config:
        from_attributes = True


class StationSchema(BaseModel):
    station_id: Optional[int] = None
    name: str
    latitude: float
    longitude: float
    elevation_m: int
    capacity: int
    num_platforms: int
    station_type: str
    has_signals: bool = False
    has_water_supply: bool = False
    has_fuel_supply: bool = False

    class Config:
        from_attributes = True




class RouteWaypointSchema(BaseModel):
    station_id: int
    order: int
    planned_arrival_time: Optional[str] = None
    planned_departure_time: Optional[str] = None


class RouteSchema(BaseModel):
    route_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    waypoints: List[RouteWaypointSchema]
    total_distance_km: float
    estimated_duration_hours: float
    frequency: str

    class Config:
        from_attributes = True


class TrainSchema(BaseModel):
    train_id: Optional[int] = None
    name: str
    route_id: int
    train_type: str  # passenger/freight/mixed
    total_weight_kg: int
    max_speed_kmh: int
    gauge: str
    passenger_capacity: int = 0
    cargo_capacity_kg: int = 0
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrainDetailSchema(TrainSchema):
    status: str
    delay_minutes: int
    current_passenger_count: int
    current_cargo_kg: int
    current_station_id: Optional[int] = None
    current_location_status: str = "at_station"

    class Config:
        from_attributes = True


class TrainStatusResponse(BaseModel):
    train_id: int
    name: str
    status: str
    current_station: Optional[str]
    current_station_id: Optional[int]
    current_location_status: str
    scheduled_departure: Optional[str]
    scheduled_arrival: Optional[str]
    actual_departure: Optional[str]
    actual_arrival: Optional[str]
    delay_minutes: int
    current_passenger_count: int
    current_cargo_kg: int
    total_weight_kg: int
    route_name: Optional[str]
    waypoint_index: int


class PassengerSchema(BaseModel):
    """Schema for passenger information."""
    passenger_id: int
    origin_station_id: int
    destination_station_id: int
    current_station_id: int
    boarded_train_id: Optional[int] = None
    status: str  # waiting/boarded/arrived/exited
    boarding_time: Optional[str] = None
    arrival_time: Optional[str] = None

    class Config:
        from_attributes = True


class StationStatusResponse(BaseModel):
    station_id: int
    name: str
    capacity: int
    num_platforms: int
    current_trains: List[str]
    num_trains_present: int
    waiting_passengers: int
    passengers_on_platforms: Optional[List[PassengerSchema]] = None


class SimulationStatusResponse(BaseModel):
    simulation_id: int
    current_simulated_datetime: str
    time_scale: int
    is_running: bool
    started_at: str
    last_updated: str


class StartSimulationRequest(BaseModel):
    start_datetime: Optional[datetime] = None
    time_scale: int = 60


# ==================== PATCH SCHEMAS (Partial Updates) ====================

class TrackPatchSchema(BaseModel):
    """Schema for partial track updates via PATCH."""
    name: Optional[str] = None
    start_station_id: Optional[int] = None
    end_station_id: Optional[int] = None
    length_km: Optional[float] = None
    gauge: Optional[str] = None
    max_speed_kmh: Optional[int] = None
    track_condition: Optional[str] = None
    track_type: Optional[str] = None
    single_or_double_track: Optional[str] = None
    bidirectional: Optional[bool] = None
    electrified: Optional[bool] = None

    class Config:
        from_attributes = True


class StationPatchSchema(BaseModel):
    """Schema for partial station updates via PATCH."""
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[int] = None
    capacity: Optional[int] = None
    num_platforms: Optional[int] = None
    station_type: Optional[str] = None
    has_signals: Optional[bool] = None
    has_water_supply: Optional[bool] = None
    has_fuel_supply: Optional[bool] = None

    class Config:
        from_attributes = True


class RoutePatchSchema(BaseModel):
    """Schema for partial route updates via PATCH."""
    name: Optional[str] = None
    description: Optional[str] = None
    waypoints: Optional[List[RouteWaypointSchema]] = None
    total_distance_km: Optional[float] = None
    estimated_duration_hours: Optional[float] = None
    frequency: Optional[str] = None

    class Config:
        from_attributes = True


class TrainPatchSchema(BaseModel):
    """Schema for partial train updates via PATCH."""
    name: Optional[str] = None
    route_id: Optional[int] = None
    train_type: Optional[str] = None
    total_weight_kg: Optional[int] = None
    max_speed_kmh: Optional[int] = None
    gauge: Optional[str] = None
    passenger_capacity: Optional[int] = None
    cargo_capacity_kg: Optional[int] = None
    current_passenger_count: Optional[int] = None
    current_cargo_kg: Optional[int] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True
