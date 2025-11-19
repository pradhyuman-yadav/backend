"""
Game Emulation Router - API endpoints for arcade game emulation.
Handles ROM uploads, game control, and WebSocket streaming.
"""
import logging
import json
from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.middleware.auth import verify_api_key
from app.schemas.game_emulation import (
    GameStatus,
    ROMUploadResponse,
    GameSettingsUpdate,
)
from app.services.other.game_emulation.rom_manager_service import rom_manager
from app.services.other.game_emulation.emulator_service import emulator_service
from app.services.other.game_emulation.game_loop_engine import game_loop_engine, GameLoopFrame

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/game", tags=["Game Emulation"])

# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: list = []

    async def connect(self, websocket: WebSocket):
        """Accept and track connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                self.disconnect(connection)


manager = ConnectionManager()


# Frame listener for WebSocket broadcasting
def websocket_frame_listener(frame: GameLoopFrame):
    """Listener callback that sends frames to WebSocket clients."""
    import asyncio
    from datetime import datetime

    message = {
        "type": "frame",
        "step": frame.step_count,
        "image": frame.image_base64,
        "actions": frame.model_action or [],
        "reasoning": frame.reasoning,
        "reward": frame.reward,
        "done": frame.done,
        "timestamp": frame.timestamp,
    }

    # Broadcast to WebSocket clients
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        asyncio.create_task(manager.broadcast(message))
    except Exception as e:
        logger.error(f"Error broadcasting frame: {e}")


# REST Endpoints


@router.post("/upload", response_model=ROMUploadResponse, summary="Upload and start game ROM")
async def upload_rom(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """
    Upload a game ROM and start playing it.

    The system will automatically detect the game system (NES, SNES, Game Boy, etc.)
    and load the game with the model taking control.

    Args:
        file: ROM file to upload
        api_key: API authentication key

    Returns:
        Information about uploaded ROM and game startup status
    """
    try:
        # Read uploaded file
        rom_data = await file.read()

        if not rom_data:
            raise HTTPException(status_code=400, detail="Empty ROM file")

        # Upload ROM
        system, rom_path, size = rom_manager.upload_rom(rom_data, file.filename)

        # Switch to new ROM
        if not rom_manager.switch_rom(rom_path, system):
            raise HTTPException(status_code=500, detail="Failed to switch ROM")

        # Start game
        success = await game_loop_engine.start_game(rom_path, system)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to load game in emulator")

        logger.info(f"ROM uploaded and game started: {file.filename} ({system})")

        return ROMUploadResponse(
            filename=file.filename,
            system=system,
            size_bytes=size,
            status="Game started successfully",
            game_started=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ROM upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/status", response_model=GameStatus, summary="Get current game status")
async def get_status(api_key: str = Depends(verify_api_key)):
    """
    Get current game status and statistics.

    Returns:
        Current game status including active ROM, frame count, and settings
    """
    rom_path, system, rom_name = rom_manager.get_active_rom()

    return GameStatus(
        active_rom=rom_name,
        rom_system=system,
        is_running=game_loop_engine.is_running,
        steps=emulator_service.frame_count,
        reasoning_enabled=game_loop_engine.get_status()["reasoning_enabled"],
        fps=game_loop_engine.get_status()["fps"],
    )


@router.post("/reset", summary="Reset current game")
async def reset_game(api_key: str = Depends(verify_api_key)):
    """
    Reset the current game to initial state.

    Returns:
        Status of reset operation
    """
    if emulator_service.emulator is None:
        raise HTTPException(status_code=400, detail="No game currently loaded")

    success = await game_loop_engine.reset_game()

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset game")

    logger.info("Game reset via API")

    return {"status": "success", "message": "Game reset to initial state"}


@router.post("/stop", summary="Stop current game")
async def stop_game(api_key: str = Depends(verify_api_key)):
    """
    Stop the currently running game.

    Returns:
        Status of stop operation
    """
    await game_loop_engine.stop_game()
    logger.info("Game stopped via API")

    return {"status": "success", "message": "Game stopped"}


@router.put("/settings", summary="Update game settings")
async def update_settings(
    settings: GameSettingsUpdate, api_key: str = Depends(verify_api_key)
):
    """
    Update game emulation settings.

    Args:
        settings: Settings to update
        api_key: API authentication key

    Returns:
        Updated settings
    """
    if settings.reasoning_enabled is not None:
        game_loop_engine.set_reasoning(settings.reasoning_enabled)

    if settings.frame_skip is not None:
        game_loop_engine.set_frame_skip(settings.frame_skip)

    if settings.fps is not None:
        game_loop_engine.set_fps(settings.fps)

    status = game_loop_engine.get_status()
    logger.info(f"Game settings updated: {settings}")

    return {
        "status": "success",
        "settings": {
            "reasoning_enabled": status["reasoning_enabled"],
            "frame_skip": status["frame_skip"],
            "fps": status["fps"],
        },
    }


@router.post("/step", summary="Manually advance game (debugging)")
async def manual_step(minutes: int = 1, api_key: str = Depends(verify_api_key)):
    """
    Manually advance game by N frames (for debugging/paused state).

    Args:
        minutes: Number of frames to advance (default 1)
        api_key: API authentication key

    Returns:
        Status of manual step
    """
    if emulator_service.emulator is None:
        raise HTTPException(status_code=400, detail="No game loaded")

    success = await game_loop_engine.manual_step(minutes)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to step game")

    return {"status": "success", "frames_advanced": minutes}


# WebSocket Endpoint


@router.websocket("/stream")
async def websocket_gameplay(websocket: WebSocket):
    """
    WebSocket endpoint for live gameplay streaming.

    Sends game frames, model decisions, and state updates to connected clients.
    Multiple clients can connect and receive the same stream.

    Message format (NDJSON):
    - {"type": "frame", "step": N, "image": "base64_jpeg", "actions": [...], ...}
    - {"type": "status", "game": "...", "is_running": true, ...}
    """
    await manager.connect(websocket)

    try:
        # Register frame listener
        game_loop_engine.register_frame_listener(websocket_frame_listener)

        # Send initial status
        await websocket.send_json(
            {
                "type": "status",
                "game": emulator_service.current_game,
                "system": emulator_service.current_system,
                "is_running": game_loop_engine.is_running,
            }
        )

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Could implement control messages here (pause, reset, etc)
            logger.debug(f"WebSocket message received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/info", summary="Get API information")
async def get_info():
    """Get information about the game emulation API."""
    return {
        "service": "Arcade Game Emulation",
        "version": "1.0.0",
        "supported_systems": ["NES", "SNES", "GB", "Genesis", "SMS"],
        "endpoints": {
            "POST /upload": "Upload and start game ROM",
            "GET /status": "Get current game status",
            "POST /reset": "Reset game to initial state",
            "POST /stop": "Stop current game",
            "PUT /settings": "Update game settings",
            "WS /stream": "WebSocket for live gameplay stream",
        },
        "documentation": "/docs",
    }
