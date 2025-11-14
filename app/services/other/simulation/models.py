"""
SQLAlchemy ORM models for train simulation system.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.services.other.simulation.database import Base


class Track(Base):
    """Represents a railway track between two stations."""
    __tablename__ = "tracks"

    track_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    start_station_id = Column(Integer, ForeignKey("stations.station_id"), nullable=False)
    end_station_id = Column(Integer, ForeignKey("stations.station_id"), nullable=False)
    length_km = Column(Float, nullable=False)  # Distance in kilometers
    gauge = Column(String(50), nullable=False)  # Track width (e.g., "1435mm" standard gauge)
    max_speed_kmh = Column(Integer, nullable=False)  # Maximum allowed speed
    track_condition = Column(String(50), nullable=False)  # excellent/good/fair/poor
    track_type = Column(String(50), nullable=False)  # main/branch/yard
    bidirectional = Column(Boolean, default=True)  # Can trains go both directions?
    electrified = Column(Boolean, default=False)
    single_or_double_track = Column(String(20), nullable=False)  # single/double
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    start_station = relationship("Station", foreign_keys=[start_station_id], back_populates="outgoing_tracks")
    end_station = relationship("Station", foreign_keys=[end_station_id], back_populates="incoming_tracks")
    trains = relationship("Train", back_populates="current_track")


class Station(Base):
    """Represents a railway station."""
    __tablename__ = "stations"

    station_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_m = Column(Integer, nullable=False)  # Elevation in meters
    capacity = Column(Integer, nullable=False)  # Max trains that can be at station
    num_platforms = Column(Integer, nullable=False)
    station_type = Column(String(50), nullable=False)  # passenger/freight/marshaling
    has_signals = Column(Boolean, default=False)
    has_water_supply = Column(Boolean, default=False)  # For steam locomotives
    has_fuel_supply = Column(Boolean, default=False)  # For diesel locomotives
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    outgoing_tracks = relationship("Track", foreign_keys="Track.start_station_id", back_populates="start_station")
    incoming_tracks = relationship("Track", foreign_keys="Track.end_station_id", back_populates="end_station")
    trains = relationship("Train", back_populates="current_station")




class Route(Base):
    """Represents a train route (series of stations)."""
    __tablename__ = "routes"

    route_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    waypoints = Column(JSON, nullable=False)  # List of {station_id, order, planned_arrival_time, planned_departure_time}
    total_distance_km = Column(Float, nullable=False)
    estimated_duration_hours = Column(Float, nullable=False)
    frequency = Column(String(50), nullable=False)  # daily/weekly/monthly
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trains = relationship("Train", back_populates="route")


class Train(Base):
    """Represents a complete train with capacity properties."""
    __tablename__ = "trains"

    train_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False)
    current_station_id = Column(Integer, ForeignKey("stations.station_id"), nullable=True)
    current_track_id = Column(Integer, ForeignKey("tracks.track_id"), nullable=True)

    # Train properties
    train_type = Column(String(50), nullable=False)  # passenger/freight/mixed
    total_weight_kg = Column(Integer, nullable=False)  # Total weight of train
    max_speed_kmh = Column(Integer, nullable=False)  # Maximum speed capability
    gauge = Column(String(50), nullable=False)  # Track gauge compatibility

    # Capacity
    passenger_capacity = Column(Integer, default=0)  # Max passengers
    cargo_capacity_kg = Column(Integer, default=0)  # Max cargo weight

    # Current load
    current_passenger_count = Column(Integer, default=0)
    current_cargo_kg = Column(Integer, default=0)

    # Schedule and timing
    scheduled_departure = Column(DateTime, nullable=True)
    scheduled_arrival = Column(DateTime, nullable=True)
    actual_departure = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    delay_minutes = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="scheduled")  # scheduled/running/delayed/completed/cancelled
    current_location_status = Column(String(50), default="at_station")  # at_station/between_stations
    current_waypoint_index = Column(Integer, default=0)  # Current position in route

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    route = relationship("Route", back_populates="trains")
    current_station = relationship("Station", back_populates="trains")
    current_track = relationship("Track", back_populates="trains")


class SimulationState(Base):
    """Stores the persistent simulation state."""
    __tablename__ = "simulation_state"

    simulation_id = Column(Integer, primary_key=True, index=True)
    current_simulated_datetime = Column(DateTime, nullable=False)  # Current date/time in simulation
    time_scale = Column(Integer, default=60)  # 60 = 1 real second = 60 simulated seconds
    is_running = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Passenger(Base):
    """Represents a passenger waiting at or traveling on a train."""
    __tablename__ = "passengers"

    passenger_id = Column(Integer, primary_key=True, index=True)

    # Location tracking
    origin_station_id = Column(Integer, ForeignKey("stations.station_id"), nullable=False)
    destination_station_id = Column(Integer, ForeignKey("stations.station_id"), nullable=False)
    current_station_id = Column(Integer, ForeignKey("stations.station_id"), nullable=False)  # Where they are now
    boarded_train_id = Column(Integer, ForeignKey("trains.train_id"), nullable=True)  # NULL if waiting at station

    # Status tracking
    status = Column(String(50), default="waiting")  # waiting/boarded/arrived/exited
    boarding_time = Column(DateTime, nullable=True)  # When they boarded the train
    arrival_time = Column(DateTime, nullable=True)  # When they arrived at destination

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    origin_station = relationship("Station", foreign_keys=[origin_station_id])
    destination_station = relationship("Station", foreign_keys=[destination_station_id])
    current_station = relationship("Station", foreign_keys=[current_station_id])
    boarded_train = relationship("Train", foreign_keys=[boarded_train_id])
