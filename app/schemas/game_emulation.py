"""
Pydantic schemas for game emulation service.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class GameAction(BaseModel):
    """Model action for game controls."""
    buttons: List[str] = Field(..., description="List of button presses [A, B, START, SELECT, UP, DOWN, LEFT, RIGHT]")
    reasoning: Optional[str] = Field(None, description="Model reasoning for the action (if enabled)")


class GameFrame(BaseModel):
    """A single game frame with model decision."""
    step_count: int = Field(..., description="Frame/step counter")
    image_base64: str = Field(..., description="Base64 encoded JPEG image of game screen")
    memory_snapshot: Optional[bytes] = Field(None, description="Raw memory dump (optional)")
    model_action: Optional[List[str]] = Field(None, description="Action taken by model")
    reasoning: Optional[str] = Field(None, description="Model reasoning (if enabled)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GameStatus(BaseModel):
    """Current game status."""
    active_rom: Optional[str] = Field(None, description="Currently loaded ROM filename")
    rom_system: Optional[str] = Field(None, description="Detected system (NES, SNES, GB, etc)")
    is_running: bool = Field(False, description="Whether game loop is running")
    steps: int = Field(0, description="Current step/frame count")
    reasoning_enabled: bool = Field(False, description="Whether model reasoning is enabled")
    fps: float = Field(60.0, description="Target frames per second")


class ROMUploadResponse(BaseModel):
    """Response after ROM upload."""
    filename: str = Field(..., description="Uploaded ROM filename")
    system: str = Field(..., description="Detected gaming system")
    size_bytes: int = Field(..., description="ROM file size in bytes")
    status: str = Field(..., description="Status message")
    game_started: bool = Field(..., description="Whether game auto-started")


class GameSettingsUpdate(BaseModel):
    """Settings to update for game emulation."""
    reasoning_enabled: Optional[bool] = Field(None, description="Toggle model reasoning output")
    frame_skip: Optional[int] = Field(None, description="Number of frames to skip between model decisions")
    fps: Optional[float] = Field(None, description="Target frames per second")


class GameMemoryRegion(BaseModel):
    """Extracted memory region data (game-specific)."""
    score: Optional[int] = Field(None)
    lives: Optional[int] = Field(None)
    level: Optional[int] = Field(None)
    health: Optional[int] = Field(None)
    position_x: Optional[float] = Field(None)
    position_y: Optional[float] = Field(None)
    raw_data: Optional[bytes] = Field(None, description="Raw memory bytes if address mapping fails")
