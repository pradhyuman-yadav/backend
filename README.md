# MLOps Backend Service

A FastAPI-based backend service that acts as a middleware between your frontend and an Ollama LLM server. This service demonstrates MLOps best practices with proper architecture, authentication, and containerization.

## Features

- **FastAPI Framework**: Modern, fast, and easy to use
- **Ollama Integration**: Connect to local Ollama LLM server
- **Streaming Responses**: Real-time text generation using Server-Sent Events (SSE)
- **Simple Authentication**: API key-based security
- **Docker Support**: Ready for containerization and deployment
- **Modular Architecture**: Clean separation of concerns for easy future expansion
- **Auto API Documentation**: Swagger UI and ReDoc

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── middleware/
│   │   └── auth.py            # API key authentication
│   ├── services/
│   │   ├── llm/
│   │   │   ├── ollama_service.py    # Ollama integration
│   │   │   └── streaming_utils.py   # Streaming helpers
│   │   └── other/             # Future services
│   ├── routers/
│   │   └── llm.py             # LLM API endpoints
│   ├── schemas/               # Pydantic models
│   │   └── llm.py
│   └── utils/
│       └── helpers.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.10+
- Ollama server running (locally or accessible via network)
- Docker (for containerized deployment)

## Setup

### 1. Clone and Install

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
# Important: Change API_KEY to a secure value
```

### 3. Ensure Ollama is Running

```bash
# Start Ollama container
docker run -d \
  -p 11434:11434 \
  -e OLLAMA_HOST=0.0.0.0:11434 \
  -v ollama_data:/root/.ollama \
  --name ollama-llm \
  ollama/ollama:latest

# Pull a model
docker exec ollama-llm ollama pull mistral
# or
# docker exec ollama-llm ollama pull llama2
```

### 4. Run the Application

#### Option A: Local Development

```bash
# Run FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 3002
```

#### Option B: Docker

```bash
# Build image
docker build -t mlops-backend:latest .

# Run container (assumes Ollama is running on localhost:11434)
docker run -d \
  -p 3002:3002 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e API_KEY=your-secret-api-key-change-this \
  -e AUTH_ENABLED=true \
  -e DEBUG=false \
  -e ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173 \
  --name mlops-backend \
  mlops-backend:latest

# View logs
docker logs -f mlops-backend

# Stop container
docker stop mlops-backend

# Remove container
docker rm mlops-backend
```

## API Endpoints

### Health Check
```
GET /health
```
Quick health check of the application.

### LLM Service Health
```
GET /api/llm/health
```
Check if LLM service is available and Ollama is responding.

### List Available Models
```
GET /api/llm/models
Headers: X-API-Key: your-api-key
```

**Response:**
```json
{
  "models": [
    {
      "name": "mistral:latest",
      "modified_at": "2024-01-10T12:00:00Z",
      "size": 3900000000,
      "digest": "abc123..."
    }
  ]
}
```

### Generate Text (Non-Streaming)
```
POST /api/llm/generate
Headers: X-API-Key: your-api-key
Content-Type: application/json

{
  "model": "mistral",
  "prompt": "What is machine learning?",
  "stream": false
}
```

**Response:**
```json
{
  "model": "mistral",
  "response": "Machine learning is a subset of artificial intelligence...",
  "done": true,
  "total_duration": 1234567890,
  "load_duration": 123456789,
  "prompt_eval_count": 5,
  "eval_count": 50
}
```

### Generate Text (Streaming)
```
POST /api/llm/stream
Headers: X-API-Key: your-api-key
Content-Type: application/json

{
  "model": "mistral",
  "prompt": "Explain quantum computing",
  "stream": true
}
```

**Response:** Server-Sent Events stream
```
data: {"text": "Quantum"}

data: {"text": " computing"}

data: {"text": " is"}

data: {"done": true}
```

## Usage Examples

### Python
```python
import httpx
import json

API_KEY = "your-api-key"
BACKEND_URL = "http://localhost:8000"
headers = {"X-API-Key": API_KEY}

# Non-streaming
response = httpx.post(
    f"{BACKEND_URL}/api/llm/generate",
    json={
        "model": "mistral",
        "prompt": "Hello!",
        "stream": False
    },
    headers=headers
)
print(response.json()["response"])

# Streaming
with httpx.stream(
    "POST",
    f"{BACKEND_URL}/api/llm/stream",
    json={
        "model": "mistral",
        "prompt": "Hello!",
        "stream": True
    },
    headers=headers
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            if "text" in data:
                print(data["text"], end="", flush=True)
```

### JavaScript/TypeScript
```javascript
const API_KEY = "your-api-key";
const BACKEND_URL = "http://localhost:8000";

// Streaming
async function streamGenerate(prompt) {
  const response = await fetch(`${BACKEND_URL}/api/llm/stream`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: "mistral",
      prompt: prompt,
      stream: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split("\n");

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.text) {
            console.log(data.text);
          }
        } catch (e) {
          // Skip parsing errors
        }
      }
    }
  }
}

streamGenerate("What is AI?");
```

## Configuration

Edit `.env` file to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `API_KEY` | `your-secret-api-key-change-this` | API authentication key |
| `AUTH_ENABLED` | `true` | Enable API key authentication |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins |

## Available Models in Ollama

Pull models using:
```bash
docker exec ollama-llm ollama pull <model-name>
```

Popular models:
- `mistral` - Fast and efficient
- `llama2` - Larger context window
- `neural-chat` - Chat optimized
- `orca-mini` - Lightweight

See [Ollama Models Library](https://ollama.ai/library) for more options.

## Docker Commands

```bash
# Build image
docker build -t mlops-backend:latest .

# Run container in background
docker run -d -p 3002:3002 -e OLLAMA_BASE_URL=http://127.0.0.1:11434 -e API_KEY=your-secure-api-key-change-this-in-production --name mlops-backend mlops-backend:latest

# View logs in real-time
docker logs -f mlops-backend

# Stop container
docker stop mlops-backend

# Start stopped container
docker start mlops-backend

# Remove container
docker rm mlops-backend

# Execute command in running container
docker exec mlops-backend bash

# Remove image
docker rmi mlops-backend:latest

# For Ollama container, pull a model
docker exec ollama-llm ollama pull mistral
```

## API Documentation

Once running, access interactive documentation:
- **Swagger UI**: http://localhost:3002/docs
- **ReDoc**: http://localhost:3002/redoc

## Future Enhancements

The modular architecture supports easy addition of new services:

1. **Authentication Service** - Advanced user management
2. **Database Service** - Store conversation history
3. **Cache Service** - Redis for prompt caching
4. **Analytics Service** - Track usage metrics
5. **File Processing** - Document upload and processing

Each new service follows the same pattern:
- Add service logic in `app/services/<service_name>/`
- Create API router in `app/routers/<service_name>.py`
- Define schemas in `app/schemas/<service_name>.py`
- Include router in `app/main.py`

## Security Considerations

- **Change API Key**: Update `API_KEY` in `.env` before production
- **CORS Configuration**: Restrict `ALLOWED_ORIGINS` to your frontend domain
- **Rate Limiting**: Consider adding rate limiting for production (future enhancement)
- **Input Validation**: All inputs are validated using Pydantic
- **Error Handling**: Sensitive errors are not exposed in API responses

## Troubleshooting

### Ollama Connection Error
```
Error: Cannot connect to Ollama server
```
- Ensure Ollama is running
- Check `OLLAMA_BASE_URL` in `.env`
- If using Docker, verify both containers are on same network

### Authentication Failure
```
401 Unauthorized - Invalid API key
```
- Verify `X-API-Key` header is sent with requests
- Check API key matches `API_KEY` in `.env`

### No Models Available
```
Retrieved 0 available models from Ollama
```
- Pull a model: `docker exec ollama-llm ollama pull mistral`
- Wait for model download to complete

## License

MIT

## Support

For issues or questions, please refer to:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Ollama Documentation](https://ollama.ai/)
- Project Issues (if applicable)
