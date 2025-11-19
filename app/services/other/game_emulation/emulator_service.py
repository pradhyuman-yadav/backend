"""
Emulator Service - Wraps game emulation using gym-retro.
Handles game loading, state management, and rendering.
"""
import logging
import numpy as np
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)

try:
    import retro
    RETRO_AVAILABLE = True
except ImportError:
    RETRO_AVAILABLE = False
    logger.warning("gym-retro not available - install with: pip install gym-retro")


class EmulatorService:
    """Service for managing game emulation."""

    # Button mappings for different systems
    BUTTON_MAPPING = {
        'NES': ['A', 'B', 'START', 'SELECT', 'UP', 'DOWN', 'LEFT', 'RIGHT'],
        'SNES': ['A', 'B', 'X', 'Y', 'START', 'SELECT', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'L', 'R'],
        'GB': ['A', 'B', 'START', 'SELECT', 'UP', 'DOWN', 'LEFT', 'RIGHT'],
        'Genesis': ['A', 'B', 'C', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'Z', 'Y', 'X', 'MODE'],
    }

    def __init__(self):
        """Initialize emulator service."""
        self.env = None
        self.current_game: Optional[str] = None
        self.current_system: Optional[str] = None
        self.last_screen: Optional[np.ndarray] = None
        self.frame_count: int = 0
        self.is_running: bool = False
        logger.info("Emulator service initialized")

    def load_game(self, rom_path: str, system: str) -> bool:
        """
        Load a game ROM.

        Args:
            rom_path: Full path to ROM file
            system: Gaming system (NES, SNES, GB, etc)

        Returns:
            True if game loaded successfully
        """
        if not RETRO_AVAILABLE:
            logger.error("gym-retro is not installed")
            return False

        try:
            # Close previous environment
            if self.env is not None:
                self.env.close()

            # Get game name from ROM path (without extension)
            rom_file = Path(rom_path)
            game_name = rom_file.stem

            # Load environment using retro
            # The game parameter should be the ROM filename without extension
            logger.info(f"Loading game: {game_name} (system: {system})")

            # Try to load with retro
            self.env = retro.make(game_name, inttype=retro.Integrator.SUM)

            self.current_game = rom_path
            self.current_system = system
            self.frame_count = 0
            self.is_running = True

            # Get initial screen
            self.reset()

            logger.info(f"Game loaded successfully: {game_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load game {rom_path}: {str(e)}")
            self.env = None
            self.is_running = False
            return False

    def reset(self) -> Optional[np.ndarray]:
        """
        Reset game to initial state.

        Returns:
            Initial screen as numpy array, or None if failed
        """
        if self.env is None:
            logger.warning("Cannot reset: no game loaded")
            return None

        try:
            screen, _ = self.env.reset()
            self.last_screen = screen
            self.frame_count = 0
            logger.info("Game reset successfully")
            return screen
        except Exception as e:
            logger.error(f"Failed to reset game: {str(e)}")
            self.is_running = False
            return None

    def get_button_map(self) -> Dict[str, int]:
        """
        Get available buttons for current game.

        Returns:
            Dictionary of button names to indices
        """
        if self.current_system not in self.BUTTON_MAPPING:
            logger.warning(f"Unknown system {self.current_system}, using NES buttons")
            buttons = self.BUTTON_MAPPING['NES']
        else:
            buttons = self.BUTTON_MAPPING[self.current_system]

        return {btn: idx for idx, btn in enumerate(buttons)}

    def step(self, actions: Optional[list] = None) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        """
        Advance game by one frame with given action.

        Args:
            actions: List of button names to press (e.g., ['A', 'RIGHT'])

        Returns:
            Tuple of (screen, info_dict)
        """
        if self.env is None:
            logger.warning("Cannot step: no game loaded")
            return None, {}

        try:
            # Convert button names to action vector
            action = self._build_action_vector(actions or [])

            # Step environment
            screen, reward, terminated, truncated, info = self.env.step(action)
            self.last_screen = screen
            self.frame_count += 1

            # For gym API compatibility
            done = terminated or truncated

            # Log periodically
            if self.frame_count % 300 == 0:
                logger.debug(f"Frame {self.frame_count}: reward={reward}, done={done}")

            return screen, {
                'reward': reward,
                'done': done,
                'terminated': terminated,
                'truncated': truncated,
                'frame_count': self.frame_count,
                **info
            }

        except Exception as e:
            logger.error(f"Failed to step game: {str(e)}")
            self.is_running = False
            return None, {}

    def get_screen_base64(self, screen: Optional[np.ndarray] = None) -> str:
        """
        Convert screen to base64 JPEG for transmission.

        Args:
            screen: Screen array (uses last_screen if None)

        Returns:
            Base64 encoded JPEG string
        """
        if screen is None:
            screen = self.last_screen

        if screen is None:
            logger.warning("No screen available")
            return ""

        try:
            # Convert numpy array to PIL Image
            # Screen is typically (height, width, 3) with values 0-255
            if len(screen.shape) == 3 and screen.shape[2] == 3:
                image = Image.fromarray(screen.astype('uint8'), 'RGB')
            else:
                # Grayscale - convert to RGB
                screen_uint8 = (screen.astype('uint8') if screen.dtype != 'uint8' else screen)
                image = Image.new('RGB', (screen_uint8.shape[1], screen_uint8.shape[0]))
                logger.warning(f"Unexpected screen format: {screen.shape}")
                return ""

            # Encode to JPEG
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            jpeg_bytes = buffer.getvalue()

            # Convert to base64
            b64_string = base64.b64encode(jpeg_bytes).decode('utf-8')
            return b64_string

        except Exception as e:
            logger.error(f"Failed to encode screen: {str(e)}")
            return ""

    def get_memory_dump(self) -> Optional[bytes]:
        """
        Get raw memory dump from emulator.

        Returns:
            Memory bytes or None
        """
        if self.env is None:
            return None

        try:
            # gym-retro environments have memory accessible via env.data
            if hasattr(self.env, 'data'):
                return bytes(self.env.data.memory)
            return None
        except Exception as e:
            logger.error(f"Failed to get memory dump: {str(e)}")
            return None

    def get_state(self) -> Dict[str, Any]:
        """
        Get current game state.

        Returns:
            Dictionary with game state info
        """
        return {
            'game': self.current_game,
            'system': self.current_system,
            'frame_count': self.frame_count,
            'is_running': self.is_running and self.env is not None,
            'last_screen_shape': self.last_screen.shape if self.last_screen is not None else None,
            'button_map': self.get_button_map(),
        }

    def close(self) -> None:
        """Close the emulator."""
        if self.env is not None:
            try:
                self.env.close()
            except Exception as e:
                logger.warning(f"Error closing emulator: {e}")
        self.env = None
        self.is_running = False
        logger.info("Emulator closed")

    def _build_action_vector(self, button_names: list) -> np.ndarray:
        """
        Convert button names to action vector for emulator.

        Args:
            button_names: List of button names (e.g., ['A', 'RIGHT'])

        Returns:
            Action vector as numpy array
        """
        if self.env is None:
            return np.array([])

        button_map = self.get_button_map()
        action = np.zeros(len(button_map), dtype=np.int32)

        for btn in button_names:
            if btn in button_map:
                action[button_map[btn]] = 1
            else:
                logger.warning(f"Unknown button: {btn}")

        return action


# Global singleton instance
emulator_service = EmulatorService()
