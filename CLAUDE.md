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
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or run via main.py
python app/main.py
```

### Docker (Plain Docker - No Compose)
```bash
# Build image
docker build -t mlops-backend:latest .

# Run container (assumes Ollama on host)
docker run -d \
  -p 8000:8000 \
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
curl http://localhost:8000/health

# Test LLM health with auth
curl -H "X-API-Key: your-secret-api-key-change-this" \
  http://localhost:8000/api/llm/health

# Test streaming generation
curl -X POST http://localhost:8000/api/llm/stream \
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

## API Endpoints Quick Reference

- `GET /health` - Basic health check (no auth)
- `GET /api/llm/health` - LLM service status
- `GET /api/llm/models` - List available Ollama models
- `POST /api/llm/generate` - Non-streaming text generation
- `POST /api/llm/stream` - Streaming text generation (NDJSON)
- `GET /` - API info endpoint

Interactive API docs: http://localhost:8000/docs (Swagger UI)
