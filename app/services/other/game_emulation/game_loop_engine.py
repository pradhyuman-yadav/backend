"""
Game Loop Engine - Main game loop that runs continuously.
Coordinates emulator, model agent, and WebSocket streaming.
"""
import logging
import asyncio
from typing import Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, asdict

from app.services.other.game_emulation.emulator_service import emulator_service
from app.services.other.game_emulation.model_agent_service import model_agent
from app.services.other.game_emulation.rom_manager_service import rom_manager

logger = logging.getLogger(__name__)


@dataclass
class GameLoopFrame:
    """A frame from the game loop."""
    step_count: int
    image_base64: str
    memory_snapshot: Optional[bytes]
    model_action: Optional[List[str]]
    reasoning: Optional[str]
    timestamp: str
    raw_model_response: Optional[str] = None
    reward: Optional[float] = None
    done: bool = False


class GameLoopEngine:
    """Main game loop engine that runs continuously."""

    def __init__(self, fps: float = 60.0):
        """
        Initialize game loop engine.

        Args:
            fps: Target frames per second
        """
        self.fps = fps
        self.frame_time = 1.0 / fps  # Time per frame in seconds
        self.is_running = False
        self.current_frame: Optional[GameLoopFrame] = None
        self.frame_listeners: List[Callable[[GameLoopFrame], None]] = []
        self.loop_task: Optional[asyncio.Task] = None
        logger.info(f"Game Loop Engine initialized (FPS: {fps})")

    def register_frame_listener(self, callback: Callable[[GameLoopFrame], None]) -> None:
        """
        Register a callback to receive frames.

        Args:
            callback: Function that receives GameLoopFrame
        """
        self.frame_listeners.append(callback)
        logger.info(f"Frame listener registered ({len(self.frame_listeners)} total)")

    def unregister_frame_listener(self, callback: Callable[[GameLoopFrame], None]) -> None:
        """Unregister a frame listener."""
        if callback in self.frame_listeners:
            self.frame_listeners.remove(callback)
            logger.info(f"Frame listener unregistered ({len(self.frame_listeners)} remaining)")

    async def start_game(self, rom_path: str, system: str) -> bool:
        """
        Start a new game.

        Args:
            rom_path: Path to ROM file
            system: Gaming system

        Returns:
            True if game started successfully
        """
        # Stop current game if running
        if self.is_running:
            await self.stop_game()

        # Load game with emulator
        if not emulator_service.load_game(rom_path, system):
            logger.error(f"Failed to load game: {rom_path}")
            return False

        # Configure model agent
        model_agent.reset()

        # Start game loop
        self.is_running = True
        self.loop_task = asyncio.create_task(self._game_loop())
        logger.info(f"Game started: {rom_path}")
        return True

    async def stop_game(self) -> None:
        """Stop the current game."""
        self.is_running = False

        if self.loop_task:
            try:
                await asyncio.wait_for(self.loop_task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Game loop did not stop within timeout")
                self.loop_task.cancel()

        emulator_service.close()
        logger.info("Game stopped")

    async def _game_loop(self) -> None:
        """
        Main game loop - runs continuously while a game is active.
        """
        logger.info("Game loop started")

        try:
            while self.is_running:
                loop_start = datetime.utcnow()

                # Get current screen
                screen = emulator_service.last_screen
                if screen is None:
                    logger.warning("No screen available")
                    await asyncio.sleep(self.frame_time)
                    continue

                # Get model decision
                action_result = await model_agent.get_action(
                    screen_base64=emulator_service.get_screen_base64(screen),
                    button_map=emulator_service.get_button_map(),
                    memory_dump=emulator_service.get_memory_dump(),
                    game_info={
                        "game": emulator_service.current_game,
                        "system": emulator_service.current_system,
                        "frame": emulator_service.frame_count,
                    },
                )

                # Apply action to emulator
                buttons = action_result.get("buttons", [])
                next_screen, info = emulator_service.step(buttons)

                # Create frame data
                if next_screen is not None:
                    frame = GameLoopFrame(
                        step_count=emulator_service.frame_count,
                        image_base64=emulator_service.get_screen_base64(next_screen),
                        memory_snapshot=emulator_service.get_memory_dump(),
                        model_action=buttons if not action_result.get("skipped") else None,
                        reasoning=action_result.get("reasoning"),
                        timestamp=datetime.utcnow().isoformat(),
                        raw_model_response=action_result.get("raw_response"),
                        reward=info.get("reward") if isinstance(info, dict) else None,
                        done=info.get("done", False) if isinstance(info, dict) else False,
                    )

                    self.current_frame = frame

                    # Notify listeners
                    for listener in self.frame_listeners:
                        try:
                            listener(frame)
                        except Exception as e:
                            logger.error(f"Error in frame listener: {e}")

                # Frame rate control
                elapsed = (datetime.utcnow() - loop_start).total_seconds()
                sleep_time = max(0, self.frame_time - elapsed)

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                elif elapsed > self.frame_time * 1.5:
                    logger.debug(f"Frame processing slow: {elapsed:.3f}s (target: {self.frame_time:.3f}s)")

        except asyncio.CancelledError:
            logger.info("Game loop cancelled")
        except Exception as e:
            logger.error(f"Game loop error: {str(e)}", exc_info=True)
        finally:
            self.is_running = False
            logger.info("Game loop ended")

    def get_status(self) -> dict:
        """Get current game loop status."""
        return {
            "is_running": self.is_running,
            "current_game": emulator_service.current_game,
            "current_system": emulator_service.current_system,
            "frame_count": emulator_service.frame_count,
            "fps": self.fps,
            "reasoning_enabled": model_agent.reasoning_enabled,
            "frame_skip": model_agent.frame_skip,
        }

    def set_fps(self, fps: float) -> None:
        """Set target frames per second."""
        self.fps = max(1, fps)
        self.frame_time = 1.0 / self.fps
        logger.info(f"FPS set to: {self.fps}")

    def set_reasoning(self, enabled: bool) -> None:
        """Enable/disable model reasoning."""
        model_agent.set_reasoning_enabled(enabled)
        logger.info(f"Reasoning set to: {enabled}")

    def set_frame_skip(self, frame_skip: int) -> None:
        """Set frame skip for model decisions."""
        model_agent.set_frame_skip(frame_skip)
        logger.info(f"Frame skip set to: {frame_skip}")

    async def reset_game(self) -> bool:
        """Reset current game to initial state."""
        if emulator_service.env is None:
            logger.warning("No game loaded to reset")
            return False

        try:
            emulator_service.reset()
            model_agent.reset()
            logger.info("Game reset successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reset game: {e}")
            return False

    async def manual_step(self, steps: int = 1) -> bool:
        """
        Manually advance game by N frames (for debugging/paused state).

        Args:
            steps: Number of frames to advance

        Returns:
            True if successful
        """
        if emulator_service.env is None:
            return False

        try:
            for _ in range(steps):
                emulator_service.step([])  # No action
            return True
        except Exception as e:
            logger.error(f"Failed to manual step: {e}")
            return False


# Global singleton instance
game_loop_engine = GameLoopEngine()
