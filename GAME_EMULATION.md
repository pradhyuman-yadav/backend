# Arcade Game Emulation System

Autonomous arcade game playing with AI-powered decision making using llava-phi multimodal LLM.

## Overview

This system enables a backend service to autonomously play classic arcade games (NES, Game Boy, Game Boy Color) with game states and controls sent to the llava-phi language model for intelligent decision-making. The model analyzes game screens and generates optimal button inputs to progress and win games.

**Key Features:**
- 🎮 Multi-system emulation support (NES via nes-py, Game Boy/GBC via PyBoy)
- 🤖 LLM-powered AI agent (llava-phi via Ollama)
- 📡 Real-time WebSocket streaming of gameplay to frontend
- 🎬 Frame-by-frame visual and model decision streaming
- 🔄 Independent of frontend - game continues playing even if frontend is inactive
- ⚡ Per-frame AI decision making (analyzable actions)
- 🔧 Async/await architecture for high performance
- 📦 Modern, actively-maintained emulation libraries (no deprecated gym-retro)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (app/main.py)           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Game Emulation Router (/api/game)                   │   │
│  │  - Upload ROM                                        │   │
│  │  - Get Status                                        │   │
│  │  - Control Settings                                 │   │
│  │  - WebSocket Stream                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ▲                                │
│                              │                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │       Game Loop Engine (Singleton)                   │   │
│  │  - Runs continuously in background                  │   │
│  │  - ~60 FPS frame processing                         │   │
│  │  - Coordinates all services                         │   │
│  └──────────────────────────────────────────────────────┘   │
│   │           │           │              │                   │
│   ▼           ▼           ▼              ▼                   │
│  ┌────────┐┌────────┐┌──────────┐┌─────────────┐            │
│  │Emulator││  ROM   ││  Model   ││ WebSocket   │            │
│  │Service ││Manager ││  Agent   ││  Broadcast  │            │
│  │        ││        ││          ││             │            │
│  │- Load  ││- Upload││- Analyze ││- Send       │            │
│  │  ROM   ││- Switch││  frames  ││  frames     │            │
│  │- Step  ││- Store ││- LLM API ││- Broadcast │            │
│  │- Reset ││- Clean ││- Decide  ││  decisions  │            │
│  └────────┘└────────┘└──────────┘└─────────────┘            │
│      │                    │                                   │
└──────┼────────────────────┼───────────────────────────────────┘
       │                    │
   Emulator            Ollama Server
   (gym-retro)         (llava-phi)
```

## Service Components

### 1. ROM Manager Service (`app/services/other/game_emulation/rom_manager_service.py`)

Handles ROM file uploads, validation, and switching.

**Features:**
- Multi-format ROM detection (NES, SNES, GB, Genesis, SMS)
- File validation and safety checks
- Automatic system detection via signature and extension
- In-memory ROM storage (no persistence)
- Automatic cleanup of old ROMs

**Key Methods:**
```python
rom_manager.upload_rom(rom_data, filename)        # Returns (system, path, size)
rom_manager.switch_rom(rom_path, system)          # Activate new ROM
rom_manager.get_active_rom()                      # Returns (path, system, name)
rom_manager.validate_rom(rom_path)                # Verify ROM accessibility
```

### 2. Emulator Service (`app/services/other/game_emulation/emulator_service.py`)

Wraps game emulation using PyBoy (Game Boy/GBC) and nes-py (NES).

**Features:**
- Load and manage game ROMs for NES, GB, GBC
- Frame-by-frame emulation stepping
- Screen capture and encoding (base64 JPEG)
- Memory dump extraction (optional)
- Button/control mapping per system
- Automatic frame tracking
- Unified API for multiple emulator backends

**Key Methods:**
```python
emulator_service.load_game(rom_path, system)      # Load ROM
emulator_service.reset()                          # Reset to start
emulator_service.step(actions)                    # Advance 1 frame with inputs
emulator_service.get_screen_base64()              # Get current screen as JPEG
emulator_service.get_memory_dump()                # Get raw memory
emulator_service.get_button_map()                 # Available buttons for system
emulator_service.get_state()                      # Current emulator state
```

### 3. Model Agent Service (`app/services/other/game_emulation/model_agent_service.py`)

Integrates with llava-phi (Ollama) for AI decision-making.

**Features:**
- Vision-based game analysis (multimodal LLM)
- Button action parsing from model response
- Optional reasoning output
- Frame skipping for performance optimization
- Async API calls to Ollama

**Key Methods:**
```python
await model_agent.get_action(screen_base64, button_map, ...)  # Get next action
model_agent.set_reasoning_enabled(bool)                       # Toggle reasoning
model_agent.set_frame_skip(n)                                # Analyze every Nth frame
model_agent.reset()                                          # Reset for new game
```

### 4. Game Loop Engine (`app/services/other/game_emulation/game_loop_engine.py`)

Main orchestrator - runs continuously and coordinates all services.

**Features:**
- Continuous background game loop
- Per-frame coordination: screen → AI → action → emulator
- Configurable FPS and frame skipping
- WebSocket frame broadcast
- Game lifecycle management
- Async/await for non-blocking operation

**Key Methods:**
```python
await game_loop_engine.start_game(rom_path, system)  # Start new game
await game_loop_engine.stop_game()                   # Stop current game
game_loop_engine.register_frame_listener(callback)   # Receive frames
game_loop_engine.set_fps(fps)                        # Set frame rate
game_loop_engine.set_reasoning(enabled)              # Toggle reasoning
game_loop_engine.set_frame_skip(n)                   # Skip frames
```

## API Endpoints

### REST Endpoints (`/api/game`)

#### POST `/api/game/upload` - Upload ROM
Upload a game ROM file and start playing.

**Request:**
```bash
curl -X POST http://localhost:3002/api/game/upload \
  -H "X-API-Key: your-api-key" \
  -F "file=@mario.nes"
```

**Response:**
```json
{
  "filename": "mario.nes",
  "system": "NES",
  "size_bytes": 40960,
  "status": "Game started successfully",
  "game_started": true
}
```

#### GET `/api/game/status` - Get Game Status
Get current game status and statistics.

**Request:**
```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:3002/api/game/status
```

**Response:**
```json
{
  "active_rom": "mario.nes",
  "rom_system": "NES",
  "is_running": true,
  "steps": 15234,
  "reasoning_enabled": false,
  "fps": 60.0
}
```

#### POST `/api/game/reset` - Reset Game
Reset current game to initial state.

**Request:**
```bash
curl -X POST -H "X-API-Key: your-api-key" \
  http://localhost:3002/api/game/reset
```

#### POST `/api/game/stop` - Stop Game
Stop the currently running game.

**Request:**
```bash
curl -X POST -H "X-API-Key: your-api-key" \
  http://localhost:3002/api/game/stop
```

#### PUT `/api/game/settings` - Update Settings
Update game emulation settings.

**Request:**
```bash
curl -X PUT -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "reasoning_enabled": true,
    "frame_skip": 2,
    "fps": 30.0
  }' \
  http://localhost:3002/api/game/settings
```

#### GET `/api/game/info` - API Information
Get API capabilities and available endpoints.

**Request:**
```bash
curl http://localhost:3002/api/game/info
```

### WebSocket Endpoint (`/api/game/stream`)

Real-time gameplay streaming with model decisions and visual feedback.

**Connect:**
```javascript
const ws = new WebSocket("ws://localhost:3002/api/game/stream");

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === "frame") {
    // Display game frame
    document.getElementById("gameCanvas").src =
      `data:image/jpeg;base64,${message.image}`;

    // Show model actions
    console.log("Model actions:", message.actions);
    console.log("Model reasoning:", message.reasoning);
    console.log("Reward:", message.reward);
    console.log("Frame:", message.step);
  } else if (message.type === "status") {
    console.log("Game:", message.game);
    console.log("Running:", message.is_running);
  }
};
```

**Message Format (NDJSON):**
```json
{
  "type": "frame",
  "step": 1234,
  "image": "base64_encoded_jpeg_string",
  "actions": ["RIGHT", "A"],
  "reasoning": "Model can see enemies approaching from left, moving right and jumping",
  "reward": 10,
  "done": false,
  "timestamp": "2025-11-18T10:30:45.123456"
}
```

## Setup & Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**New dependencies added:**
- `pyboy>=1.6.0` - Game Boy / Game Boy Color emulation
- `nes-py>=0.0.1` - NES emulation
- `pillow` - Image processing for screen captures
- `numpy` - Numerical operations
- `python-multipart` - File upload support

### 2. Ensure Ollama is Running

```bash
# Terminal 1: Start Ollama server
ollama serve

# Terminal 2: Pull llava-phi model (first time)
ollama pull llava-phi
```

### 3. Configure Environment

Update `.env` if needed:

```env
# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434

# API Authentication
API_KEY=your-secret-api-key-change-this
AUTH_ENABLED=true

# Server
HOST=0.0.0.0
PORT=3002
DEBUG=false

# CORS
ALLOWED_ORIGINS=http://localhost:*
```

### 4. Run Backend

```bash
# Development with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 3002

# Or using main.py
python app/main.py
```

### 5. Test Endpoints

```bash
# Check API is running
curl http://localhost:3002/health

# Upload a ROM and start game
curl -X POST http://localhost:3002/api/game/upload \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -F "file=@games/mario.nes"

# Check game status
curl -H "X-API-Key: your-secret-api-key-change-this" \
  http://localhost:3002/api/game/status
```

## Frontend Integration

### React/Vue Example

```javascript
// Connect WebSocket
const ws = new WebSocket("ws://localhost:3002/api/game/stream");

ws.onmessage = (event) => {
  const frame = JSON.parse(event.data);

  if (frame.type === "frame") {
    // Update game display
    const img = new Image();
    img.src = `data:image/jpeg;base64,${frame.image}`;

    // Display on canvas or img element
    document.getElementById("gameScreen").appendChild(img);

    // Show model decision
    if (frame.actions && frame.actions.length > 0) {
      document.getElementById("actions").textContent =
        `Actions: ${frame.actions.join(", ")}`;
    }

    // Show reasoning if enabled
    if (frame.reasoning) {
      document.getElementById("reasoning").textContent = frame.reasoning;
    }
  }
};

// Upload ROM
async function uploadROM(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    "http://localhost:3002/api/game/upload",
    {
      method: "POST",
      headers: {
        "X-API-Key": "your-secret-api-key-change-this"
      },
      body: formData
    }
  );

  const result = await response.json();
  console.log("Game started:", result);
}

// Get status
async function getStatus() {
  const response = await fetch(
    "http://localhost:3002/api/game/status",
    {
      headers: {
        "X-API-Key": "your-secret-api-key-change-this"
      }
    }
  );

  const status = await response.json();
  console.log(status);
}
```

## System Behavior

### Game Loop Cycle

Each frame (default ~60 FPS):

1. **Capture** - Get current screen from emulator
2. **Analyze** - Send to llava-phi for decision-making
3. **Decide** - Model returns button actions
4. **Execute** - Apply buttons to emulator
5. **Broadcast** - Send frame to WebSocket clients
6. **Sleep** - Frame rate regulation

### Frame Rate Control

- Default: 60 FPS
- Configurable via API: `PUT /api/game/settings`
- Frame time: `1.0 / fps` seconds
- Adaptive sleep to maintain target FPS

### Model Decision Flow

```
Game Screen (RGB array)
       ↓
Convert to JPEG → Base64 encode
       ↓
Send to llava-phi with prompt:
  "Analyze game screen. What buttons should be pressed?"
       ↓
Model analyzes image, returns text response
       ↓
Parse response for button mentions:
  - Direct mentions: "A", "RIGHT", "UP"
  - Action aliases: "JUMP" → "A", "MOVE LEFT" → "LEFT"
  - JSON parsing if model returns JSON format
       ↓
Validate buttons against available controls
       ↓
Return action list: ["RIGHT", "A"]
       ↓
Apply to emulator
```

### Memory and Resource Usage

- **ROM storage**: In-memory only (cleaned up when new ROM loaded)
- **Screen buffers**: ~1-2 MB per frame (kept in memory, not stored)
- **Model inference**: Async with Ollama (no blocking)
- **CPU usage**: Depends on emulator + Ollama inference time
- **Network**: Frame rate × JPEG size = bandwidth

## Performance Optimization

### For Faster Gameplay

1. **Reduce FPS**: `PUT /api/game/settings {"fps": 30.0}`
2. **Enable frame skipping**: `PUT /api/game/settings {"frame_skip": 2}`
   - Analyzes every 2nd frame (halves model calls)
3. **Disable reasoning**: `PUT /api/game/settings {"reasoning_enabled": false}`
   - Reduces model output tokens
4. **Reduce JPEG quality**: Edit `emulator_service.py` line with `quality=85` → lower

### For Better AI Decisions

1. **Enable reasoning**: `PUT /api/game/settings {"reasoning_enabled": true}`
   - Model explains its decisions
   - Slightly slower but better actions
2. **Disable frame skipping**: `PUT /api/game/settings {"frame_skip": 1}`
3. **Increase model temperature**: Edit `model_agent_service.py` (more creative)

## File Structure

```
app/services/other/game_emulation/
├── __init__.py                    # Package exports
├── rom_manager_service.py         # ROM upload/switching
├── emulator_service.py            # Game emulation wrapper
├── model_agent_service.py         # llava-phi integration
└── game_loop_engine.py            # Main game loop orchestrator

app/routers/
└── game_emulation.py              # REST + WebSocket endpoints

app/schemas/
└── game_emulation.py              # Pydantic models
```

## Supported Systems

| System | Extension | Library | Status |
|--------|-----------|---------|--------|
| NES | .nes | nes-py | ✅ Supported |
| Game Boy | .gb | PyBoy | ✅ Supported |
| Game Boy Color | .gbc | PyBoy | ✅ Supported |

## Example Game ROMs

Test with these publicly available ROM files:
- **NES**: Super Mario Bros, Pac-Man, Donkey Kong
- **SNES**: Super Mario World, Castlevania IV
- **Game Boy**: Tetris, Mario Land
- **Genesis**: Sonic the Hedgehog

## Troubleshooting

### Game Won't Load
```
Error: Failed to load game in emulator
```
- Verify ROM file format is correct (.nes for NES, .gb/.gbc for Game Boy)
- Check emulator system detection
- Ensure pyboy and nes-py are installed: `pip install pyboy nes-py`
- For NES: Ensure ROM is in standard iNES format
- For Game Boy: ROM should be in standard Game Boy format

### Model Not Responding
```
Error: Model API call failed
```
- Check Ollama server is running: `ollama serve`
- Verify model is pulled: `ollama pull llava-phi`
- Check `OLLAMA_BASE_URL` in .env

### WebSocket Not Streaming
```
No frames in WebSocket connection
```
- Ensure game is running: `GET /api/game/status` → `is_running: true`
- Check browser console for connection errors
- Verify WebSocket is connecting to correct URL

### High CPU/Latency
- Reduce FPS: `PUT /api/game/settings {"fps": 30}`
- Enable frame skip: `PUT /api/game/settings {"frame_skip": 3}`
- Check Ollama server performance

## Future Enhancements

- [ ] Real-time game state extraction (HP, score, level) from memory
- [ ] Reward-based learning for better action selection
- [ ] Multi-game simultaneous emulation (queue system)
- [ ] Save/load game state snapshots
- [ ] Replay recording with decision timeline
- [ ] Custom prompts per game type
- [ ] Game-specific memory address mappings
- [ ] Vision-based game objective detection

## Architecture Decisions

### Why Async/Await?
- Non-blocking emulation loop
- Multiple WebSocket clients can connect simultaneously
- Model API calls don't stall game loop
- Scales better for future multi-game support

### Why gym-retro?
- Multi-system support in single library
- Stable API
- Good community
- Easy screen extraction

### Why llava-phi?
- Multimodal LLM (understands images)
- Lightweight compared to larger models
- Good performance on game screens
- Runs locally via Ollama

### Why No Game Persistence?
- Simpler architecture
- Matches requirement for live frontend streaming
- Can be added later with database integration
- Reduces complexity for MVP

## References

- [gym-retro Documentation](https://github.com/openai/retro)
- [Ollama Models](https://ollama.ai/library)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Pydantic Validation](https://docs.pydantic.dev/)

---

**Created**: 2025-11-18
**System**: Arcade Game Emulation with AI Control
**Status**: Ready for Integration Testing
