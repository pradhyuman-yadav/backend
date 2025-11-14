"""
Train simulation engine for schedule progression and state management.
"""
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.services.other.simulation.models import Train, SimulationState, Route, Station
from app.services.other.simulation.train_service import TrainService
from app.services.other.simulation.passenger_service import PassengerService

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Core simulation engine for managing train movement and scheduling."""

    @staticmethod
    def init_simulation(db: Session, start_datetime: datetime, time_scale: int = 60) -> Optional[SimulationState]:
        """Initialize a new simulation."""
        try:
            # Check if simulation already exists
            existing = db.query(SimulationState).first()
            if existing:
                db.delete(existing)
                db.commit()

            sim_state = SimulationState(
                current_simulated_datetime=start_datetime,
                time_scale=time_scale,
                is_running=False
            )
            db.add(sim_state)
            db.commit()
            db.refresh(sim_state)
            logger.info(f"Initialized simulation at {start_datetime} with time_scale {time_scale}")
            return sim_state
        except Exception as e:
            db.rollback()
            logger.error(f"Simulation initialization failed: {str(e)}")
            raise

    @staticmethod
    def start_simulation(db: Session) -> Optional[SimulationState]:
        """Start the simulation."""
        try:
            sim_state = db.query(SimulationState).first()
            if not sim_state:
                raise ValueError("Simulation not initialized")

            sim_state.is_running = True
            db.commit()
            db.refresh(sim_state)
            logger.info("Simulation started")
            return sim_state
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to start simulation: {str(e)}")
            raise

    @staticmethod
    def pause_simulation(db: Session) -> Optional[SimulationState]:
        """Pause the simulation."""
        try:
            sim_state = db.query(SimulationState).first()
            if not sim_state:
                raise ValueError("Simulation not initialized")

            sim_state.is_running = False
            db.commit()
            db.refresh(sim_state)
            logger.info("Simulation paused")
            return sim_state
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to pause simulation: {str(e)}")
            raise

    @staticmethod
    def reset_simulation(db: Session) -> bool:
        """Reset simulation to initial state."""
        try:
            # Reset all trains to scheduled status
            trains = db.query(Train).all()
            for train in trains:
                train.status = "scheduled"
                train.current_station_id = None
                train.current_track_id = None
                train.actual_departure = None
                train.actual_arrival = None
                train.delay_minutes = 0
                train.current_waypoint_index = 0
                train.current_location_status = "at_station"
                train.current_passenger_count = 0
                train.current_cargo_kg = 0

            # Reset simulation state
            sim_state = db.query(SimulationState).first()
            if sim_state:
                sim_state.is_running = False
                sim_state.current_simulated_datetime = datetime.utcnow()
                sim_state.last_updated = datetime.utcnow()

            db.commit()
            logger.info("Simulation reset")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to reset simulation: {str(e)}")
            raise

    @staticmethod
    def step_simulation(db: Session, minutes_to_advance: int = 60) -> Optional[SimulationState]:
        """Advance simulation by specified simulated time."""
        try:
            sim_state = db.query(SimulationState).first()
            if not sim_state:
                raise ValueError("Simulation not initialized")

            # Calculate time advance
            time_advance = timedelta(minutes=minutes_to_advance)
            sim_state.current_simulated_datetime += time_advance
            sim_state.last_updated = datetime.utcnow()

            # Update all trains
            trains = db.query(Train).filter(Train.status.in_(["scheduled", "running", "delayed"])).all()
            for train in trains:
                SimulationEngine._update_train_state(db, train, sim_state.current_simulated_datetime)

            db.commit()
            db.refresh(sim_state)
            logger.info(f"Simulation advanced to {sim_state.current_simulated_datetime}")
            return sim_state
        except Exception as e:
            db.rollback()
            logger.error(f"Simulation step failed: {str(e)}")
            raise

    @staticmethod
    def _update_train_state(db: Session, train: Train, current_datetime: datetime) -> None:
        """Update train state based on current simulation time."""
        if train.status == "completed" or train.status == "cancelled":
            return

        route = db.query(Route).filter(Route.route_id == train.route_id).first()
        if not route or not route.waypoints:
            return

        waypoints = route.waypoints

        # Check if train should depart
        if train.status == "scheduled" and train.scheduled_departure:
            if current_datetime >= train.scheduled_departure:
                train.status = "running"
                train.actual_departure = current_datetime
                if waypoints:
                    first_waypoint = waypoints[0]
                    train.current_station_id = first_waypoint.get("station_id")
                    train.current_waypoint_index = 0
                logger.info(f"Train {train.name} departed")

        # Update progress if train is running
        elif train.status == "running" or train.status == "delayed":
            if train.current_waypoint_index < len(waypoints):
                current_waypoint = waypoints[train.current_waypoint_index]
                planned_arrival = current_waypoint.get("planned_arrival_time")

                if planned_arrival and isinstance(planned_arrival, str):
                    # Parse ISO format datetime
                    planned_arrival = datetime.fromisoformat(planned_arrival)

                # Check if train should arrive at next station
                if planned_arrival and current_datetime >= planned_arrival:
                    station_id = current_waypoint.get("station_id")
                    train.current_station_id = station_id
                    train.current_track_id = None
                    train.current_location_status = "at_station"

                    # Calculate delay
                    if train.actual_departure:
                        elapsed = (current_datetime - train.actual_departure).total_seconds() / 60
                        planned_duration = (planned_arrival - train.actual_departure).total_seconds() / 60
                        train.delay_minutes = max(0, int(elapsed - planned_duration))

                    logger.info(f"Train {train.name} arrived at station {station_id}")

                    # Handle boarding/deboarding
                    SimulationEngine._handle_passenger_exchange(db, train, station_id, current_datetime)

                    # Check if this is the final destination
                    if train.current_waypoint_index == len(waypoints) - 1:
                        train.status = "completed"
                        train.actual_arrival = current_datetime
                        logger.info(f"Train {train.name} completed journey")
                    else:
                        # Move to next waypoint
                        train.current_waypoint_index += 1
                else:
                    # Train is between stations
                    train.current_location_status = "between_stations"

    @staticmethod
    def _handle_passenger_exchange(db: Session, train: Train, station_id: int, current_datetime: datetime) -> None:
        """Handle passengers deboarding and boarding at a station."""
        # First: Deboard passengers who reached their destination
        passengers_to_deboard = PassengerService.get_passengers_getting_off_at_station(
            db, train.train_id, station_id
        )
        for passenger in passengers_to_deboard:
            PassengerService.deboard_passenger(db, passenger.passenger_id, station_id, current_datetime)
            train.current_passenger_count -= 1

        # Then: Board waiting passengers (up to capacity)
        waiting_passengers = PassengerService.get_waiting_passengers_at_station(db, station_id)
        available_seats = train.passenger_capacity - train.current_passenger_count

        passengers_to_board = waiting_passengers[:available_seats]
        for passenger in passengers_to_board:
            PassengerService.board_passenger(db, passenger.passenger_id, train.train_id, current_datetime)
            train.current_passenger_count += 1

        if passengers_to_deboard or passengers_to_board:
            logger.info(
                f"Station {station_id}: {len(passengers_to_deboard)} deboarded, "
                f"{len(passengers_to_board)} boarded on train {train.train_id}"
            )

    @staticmethod
    def generate_passengers_for_simulation(db: Session, passengers_per_station: int = 5) -> int:
        """Generate initial passengers at all stations for the simulation."""
        try:
            stations = db.query(Station).all()
            total_generated = 0

            for station in stations:
                created = PassengerService.generate_passengers_at_station(
                    db, station.station_id, passengers_per_station, stations
                )
                total_generated += len(created)

            logger.info(f"Generated {total_generated} passengers across {len(stations)} stations")
            return total_generated
        except Exception as e:
            logger.error(f"Failed to generate passengers: {str(e)}")
            raise

    @staticmethod
    def get_simulation_status(db: Session) -> Optional[Dict[str, Any]]:
        """Get current simulation status."""
        try:
            sim_state = db.query(SimulationState).first()
            if not sim_state:
                return None

            return {
                "simulation_id": sim_state.simulation_id,
                "current_simulated_datetime": sim_state.current_simulated_datetime.isoformat(),
                "time_scale": sim_state.time_scale,
                "is_running": sim_state.is_running,
                "started_at": sim_state.started_at.isoformat(),
                "last_updated": sim_state.last_updated.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get simulation status: {str(e)}")
            raise

    @staticmethod
    def get_trains_status(db: Session) -> List[Dict[str, Any]]:
        """Get status of all trains."""
        try:
            trains = db.query(Train).all()
            status_list = []

            for train in trains:
                route = db.query(Route).filter(Route.route_id == train.route_id).first()
                station = db.query(Station).filter(Station.station_id == train.current_station_id).first() if train.current_station_id else None

                train_status = {
                    "train_id": train.train_id,
                    "name": train.name,
                    "status": train.status,
                    "current_station": station.name if station else None,
                    "current_station_id": train.current_station_id,
                    "current_location_status": train.current_location_status,
                    "scheduled_departure": train.scheduled_departure.isoformat() if train.scheduled_departure else None,
                    "scheduled_arrival": train.scheduled_arrival.isoformat() if train.scheduled_arrival else None,
                    "actual_departure": train.actual_departure.isoformat() if train.actual_departure else None,
                    "actual_arrival": train.actual_arrival.isoformat() if train.actual_arrival else None,
                    "delay_minutes": train.delay_minutes,
                    "current_passenger_count": train.current_passenger_count,
                    "current_cargo_kg": train.current_cargo_kg,
                    "total_weight_kg": train.total_weight_kg,
                    "route_name": route.name if route else None,
                    "waypoint_index": train.current_waypoint_index
                }
                status_list.append(train_status)

            return status_list
        except Exception as e:
            logger.error(f"Failed to get trains status: {str(e)}")
            raise

    @staticmethod
    def get_stations_status(db: Session, hours_ahead: int = 2) -> List[Dict[str, Any]]:
        """Get status of all stations with arrivals/departures and waiting passengers."""
        try:
            stations = db.query(Station).all()
            status_list = []

            for station in stations:
                arrivals = db.query(Train).filter(Train.current_station_id == station.station_id).all()
                waiting_passengers = PassengerService.get_waiting_passengers_at_station(db, station.station_id)

                station_status = {
                    "station_id": station.station_id,
                    "name": station.name,
                    "capacity": station.capacity,
                    "num_platforms": station.num_platforms,
                    "current_trains": [train.name for train in arrivals],
                    "num_trains_present": len(arrivals),
                    "waiting_passengers": len(waiting_passengers),
                    "passengers_on_platforms": [
                        {
                            "passenger_id": p.passenger_id,
                            "origin_station_id": p.origin_station_id,
                            "destination_station_id": p.destination_station_id,
                            "current_station_id": p.current_station_id,
                            "boarded_train_id": p.boarded_train_id,
                            "status": p.status,
                            "boarding_time": p.boarding_time.isoformat() if p.boarding_time else None,
                            "arrival_time": p.arrival_time.isoformat() if p.arrival_time else None
                        }
                        for p in waiting_passengers
                    ]
                }
                status_list.append(station_status)

            return status_list
        except Exception as e:
            logger.error(f"Failed to get stations status: {str(e)}")
            raise
