# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MLOps Backend Service - A FastAPI middleware between frontend and Ollama LLM server. Designed for portfolio demonstration with clean modular architecture supporting future service expansion.

## Architecture & Design Patterns

### Modular Service Separation
The project is intentionally structured to separate **LLM services** from **other future services**:

- **LLM Services** (`app/services/llm/`)
  - `ollama_service.py`: Handles all Ollama HTTP communication, streaming, and error handling
  - Async/await pattern for concurrent request handling
  - Global singleton instance for connection reuse

- **Other Services** (`app/services/other/`)
  - Directory reserved for non-LLM services (database, cache, auth, etc.)
  - Completely isolated from LLM logic

- **Routers** (`app/routers/`)
  - `llm.py`: Contains all LLM endpoints (`/api/llm/*`)
  - `other.py`: Placeholder for future non-LLM endpoints (`/api/other/*`)
  - Routers are included in `app/main.py`

### Key Files
- **`app/config.py`**: Pydantic Settings for environment-based configuration. All config from `.env`
- **`app/middleware/auth.py`**: Simple X-API-Key header validation. Dependency injection via FastAPI
- **`app/schemas/`**: Pydantic models for request/response validation. Separate files per service domain
- **`app/main.py`**: FastAPI initialization, CORS, lifespan management, router inclusion
- **`app/utils/helpers.py`**: Logging setup and shared utilities

### Streaming Implementation
- LLM endpoint `/api/llm/stream` returns `StreamingResponse` with NDJSON format
- `OllamaService._stream_response()` uses httpx stream context manager
- Frontend consumes via EventSource or fetch with ReadableStream

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env from example
cp .env.example .env
# Edit .env and change API_KEY

# Ensure Ollama running on http://localhost:11434
```

### Running Locally
```bash
# Development with reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 3002

# Or run via main.py
python app/main.py
```

### Docker (Plain Docker - No Compose)
```bash
# Build image
docker build -t mlops-backend:latest .

# Run container (assumes Ollama on host)
docker run -d \
  -p 3002:3002 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e API_KEY=your-secret-key \
  --name mlops-backend \
  mlops-backend:latest

# View logs
docker logs -f mlops-backend

# Stop container
docker stop mlops-backend
```

### Testing & Validation
```bash
# Test health endpoint (no auth required)
curl http://localhost:3002/health

# Test LLM health with auth
curl -H "X-API-Key: your-secret-api-key-change-this" \
  http://localhost:3002/api/llm/health

# Test streaming generation
curl -X POST http://localhost:3002/api/llm/stream \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Hello","stream":true}'
```

## Adding New Services

### Pattern for Adding a Non-LLM Service (e.g., Database Service)

1. **Create service logic** in `app/services/other/database_service.py`:
   ```python
   class DatabaseService:
       async def save_conversation(self, messages: list) -> dict:
           # Implementation
   ```

2. **Create schema** in `app/schemas/other.py`:
   ```python
   class ConversationRequest(BaseModel):
       messages: List[str]
   ```

3. **Create router** in `app/routers/database.py`:
   ```python
   router = APIRouter(prefix="/api/database", tags=["Database"])

   @router.post("/conversations")
   async def save_conversation(request: ConversationRequest, api_key: str = Depends(verify_api_key)):
       # Use DatabaseService here
   ```

4. **Include router** in `app/main.py`:
   ```python
   from app.routers import database
   app.include_router(database.router)
   ```

## Configuration & Environment

All configuration from `pydantic_settings.BaseSettings` in `app/config.py`:

| Env Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server location |
| `API_KEY` | `your-secret-api-key-change-this` | X-API-Key header validation |
| `AUTH_ENABLED` | `true` | Toggle authentication |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Uvicorn reload on file changes |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost` | CORS origins |

## API Authentication & Validation

- **All endpoints** (except `/health`) require `X-API-Key` header
- Authentication via `verify_api_key()` dependency in `app/middleware/auth.py`
- Use as dependency: `api_key: str = Depends(verify_api_key)`
- Input validation via Pydantic schemas automatically

## Common Tasks

### Debugging Ollama Connection
- Check `OLLAMA_BASE_URL` in `.env` matches running Ollama
- Test directly: `curl http://your-ollama-url:11434/api/tags`
- Service logs errors with attempt URLs

### Extending Streaming
- Modify `stream_generator()` in `app/routers/llm.py` for response formatting
- Modify `OllamaService._stream_response()` for upstream Ollama behavior

### Adding Rate Limiting
- Install `slowapi`: `pip install slowapi`
- Create middleware in `app/middleware/rate_limit.py`
- Apply via `@limiter.limit("5/minute")` decorator

## Important Notes

- **Ollama Service** is a global singleton (`ollama_service` in `app/services/llm/ollama_service.py`) for connection pooling
- **Lifespan Management**: `ollama_service.close()` called on shutdown in `app/main.py`
- **Streaming Format**: NDJSON (newline-delimited JSON) - one JSON object per line
- **Error Handling**: Exceptions caught and converted to HTTP errors with appropriate status codes
- **Docker**: Multi-stage Dockerfile for slim final image. Uses Python 3.11-slim base.
- **Continuous Simulation**: Train simulation automatically starts on app launch and runs continuously with time_scale=60. Cannot be paused, reset, or restarted - only manually stepped forward via `/game/step` endpoint if needed.
- **Vehicle Endpoints**: Use `/simulation/train/vehicle` for managing any vehicle (locomotive, passenger carriage, freight carriage, etc)
- **Train Endpoints**: Use `/simulation/train/train` for creating trains and managing train composition with vehicles
- **Unified Vehicle Model**: All rolling stock is managed through the single `/vehicle` endpoint regardless of type
- **Simulation Database**: SQLite file (`simulation.db`) persists all train data and state across server restarts

## API Endpoints Quick Reference

### LLM Service
- `GET /health` - Basic health check (no auth)
- `GET /api/llm/health` - LLM service status
- `GET /api/llm/models` - List available Ollama models
- `POST /api/llm/generate` - Non-streaming text generation
- `POST /api/llm/stream` - Streaming text generation (NDJSON)
- `GET /` - API info endpoint

### Train Simulation System

**Infrastructure (Tracks)**
- `POST /simulation/train/infra` - Create track
- `GET /simulation/train/infra` - List all tracks
- `GET /simulation/train/infra/{track_id}` - Get track
- `PUT /simulation/train/infra/{track_id}` - Update track
- `DELETE /simulation/train/infra/{track_id}` - Delete track

**Stations**
- `POST /simulation/train/station` - Create station
- `GET /simulation/train/station` - List all stations
- `GET /simulation/train/station/{station_id}` - Get station
- `PUT /simulation/train/station/{station_id}` - Update station
- `DELETE /simulation/train/station/{station_id}` - Delete station

**Vehicles** (locomotives, passenger carriages, freight carriages, etc)
- `POST /simulation/train/vehicle` - Create vehicle
- `GET /simulation/train/vehicle` - List all vehicles
- `GET /simulation/train/vehicle/{vehicle_id}` - Get vehicle
- `PUT /simulation/train/vehicle/{vehicle_id}` - Update vehicle
- `DELETE /simulation/train/vehicle/{vehicle_id}` - Delete vehicle
- `POST /simulation/train/vehicle/{vehicle_id}/assign-train/{train_id}` - Assign vehicle to train

**Trains**
- `POST /simulation/train/train` - Create train with vehicle composition
- `GET /simulation/train/train` - List all trains
- `GET /simulation/train/train/{train_id}` - Get train with vehicles
- `PUT /simulation/train/train/{train_id}` - Update train
- `DELETE /simulation/train/train/{train_id}` - Delete train
- `POST /simulation/train/train/{train_id}/add-vehicle/{vehicle_id}` - Add vehicle to train
- `DELETE /simulation/train/train/{train_id}/remove-vehicle/{vehicle_id}` - Remove vehicle from train

**Simulation Control** (Simulation runs continuously from app startup)
- `GET /simulation/train/game/status` - Get current simulation status and time
- `GET /simulation/train/game/trains-status` - Get all trains with position, status, delays
- `GET /simulation/train/game/stations-status` - Get all stations with current train occupancy
- `POST /simulation/train/game/step?minutes=60` - Manually advance simulation by N minutes (optional)

Interactive API docs: http://localhost:3002/docs (Swagger UI)

## Train Simulation Architecture

### Database Schema
SQLite database with tables for:
- **tracks**: Railway infrastructure with realistic properties (gauge, max_speed, condition)
- **stations**: Stations with capacity, platforms, and service facilities
- **carriages**: Individual train cars with specifications (weight, capacity, brake_type)
- **trains**: Train compositions linking locomotive + carriages to routes
- **routes**: Route definitions with waypoints and schedules
- **simulation_state**: Persistent simulation state (current time, time_scale)

### Time-Accelerated Simulation
- Configurable time_scale (e.g., 60:1 means 1 real second = 60 simulated seconds)
- Trains progress through schedules based on simulation time
- Delays calculated and propagated through remaining route
- All state persists in database between server restarts

### Service Organization
- `app/services/other/simulation/` - All simulation services
  - `track_service.py` - Track CRUD
  - `station_service.py` - Station CRUD
  - `carriage_service.py` - Vehicle management (locomotives, carriages, etc) - exposed via `/vehicle` endpoints
  - `train_service.py` - Train composition management (groups vehicles together)
  - `route_service.py` - Route CRUD
  - `simulation_engine.py` - Schedule progression and state management
  - `database.py` - SQLite setup and connection
  - `models.py` - SQLAlchemy ORM models (Carriage model represents any vehicle)
