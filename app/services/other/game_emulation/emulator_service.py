"""
Emulator Service - Wraps game emulation using PyBoy (Game Boy) and nes-py (NES).
Handles game loading, state management, and rendering.
"""
import logging
import numpy as np
from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)

try:
    from pyboy import PyBoy
    PYBOY_AVAILABLE = True
except ImportError:
    PYBOY_AVAILABLE = False
    logger.warning("pyboy not available - install with: pip install pyboy")

try:
    from nes_py.nes_environment import NESEnv
    NESPY_AVAILABLE = True
except ImportError:
    NESPY_AVAILABLE = False
    logger.warning("nes-py not available - install with: pip install nes-py")


class EmulatorService:
    """Service for managing game emulation with PyBoy (Game Boy) and nes-py (NES)."""

    # Button mappings for different systems
    BUTTON_MAPPING = {
        'NES': ['A', 'B', 'START', 'SELECT', 'UP', 'DOWN', 'LEFT', 'RIGHT'],
        'GB': ['A', 'B', 'START', 'SELECT', 'UP', 'DOWN', 'LEFT', 'RIGHT'],
        'GBC': ['A', 'B', 'START', 'SELECT', 'UP', 'DOWN', 'LEFT', 'RIGHT'],
    }

    # NES action index mapping (nes-py uses 0-17 action space)
    NES_ACTION_MAP = {
        'RIGHT': 6,
        'LEFT': 7,
        'DOWN': 8,
        'UP': 9,
        'START': 3,
        'SELECT': 2,
        'A': 0,
        'B': 1,
    }

    def __init__(self):
        """Initialize emulator service."""
        self.emulator: Union[PyBoy, NESEnv, None] = None
        self.emulator_type: Optional[str] = None  # 'pyboy' or 'nespy'
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
            system: Gaming system (NES, GB, GBC)

        Returns:
            True if game loaded successfully
        """
        try:
            # Close previous emulator
            self.close()

            rom_file = Path(rom_path)
            game_name = rom_file.stem

            logger.info(f"Loading game: {game_name} (system: {system})")

            # Load based on system type
            if system == 'NES':
                if not NESPY_AVAILABLE:
                    logger.error("nes-py is not installed")
                    return False
                self.emulator = NESEnv(rom_path)
                self.emulator_type = 'nespy'
                logger.info(f"Loaded NES game with nes-py")

            elif system in ['GB', 'GBC']:
                if not PYBOY_AVAILABLE:
                    logger.error("pyboy is not installed")
                    return False
                cgb_mode = (system == 'GBC')
                self.emulator = PyBoy(rom_path, cgb=cgb_mode)
                self.emulator_type = 'pyboy'
                logger.info(f"Loaded Game Boy game with PyBoy (CGB: {cgb_mode})")

            else:
                logger.error(f"Unsupported system: {system}")
                return False

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
            self.emulator = None
            self.is_running = False
            return False

    def reset(self) -> Optional[np.ndarray]:
        """
        Reset game to initial state.

        Returns:
            Initial screen as numpy array, or None if failed
        """
        if self.emulator is None:
            logger.warning("Cannot reset: no game loaded")
            return None

        try:
            if self.emulator_type == 'nespy':
                screen, _ = self.emulator.reset()
                self.last_screen = screen
            elif self.emulator_type == 'pyboy':
                self.emulator.reset_game()
                screen = self._get_pyboy_screen()
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
        if self.emulator is None:
            logger.warning("Cannot step: no game loaded")
            return None, {}

        try:
            if self.emulator_type == 'nespy':
                # nes-py step
                action = self._build_nes_action(actions or [])
                screen, reward, terminated, truncated, info = self.emulator.step(action)
                self.last_screen = screen
                self.frame_count += 1
                done = terminated or truncated

                return screen, {
                    'reward': reward,
                    'done': done,
                    'terminated': terminated,
                    'truncated': truncated,
                    'frame_count': self.frame_count,
                    **info
                }

            elif self.emulator_type == 'pyboy':
                # PyBoy step
                self._apply_pyboy_buttons(actions or [])
                self.emulator.tick()
                screen = self._get_pyboy_screen()
                self.last_screen = screen
                self.frame_count += 1

                return screen, {
                    'frame_count': self.frame_count,
                    'done': False,
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
        if self.emulator is not None:
            try:
                if self.emulator_type == 'pyboy':
                    self.emulator.stop()
                elif self.emulator_type == 'nespy':
                    self.emulator.close()
            except Exception as e:
                logger.warning(f"Error closing emulator: {e}")
        self.emulator = None
        self.is_running = False
        logger.info("Emulator closed")

    def _get_pyboy_screen(self) -> np.ndarray:
        """Get screen from PyBoy as numpy array."""
        if self.emulator is None or self.emulator_type != 'pyboy':
            return np.zeros((144, 160, 3), dtype=np.uint8)

        try:
            # PyBoy returns screen as (144, 160, 3) RGB
            return np.array(self.emulator.screen.ndarray, dtype=np.uint8)
        except Exception as e:
            logger.error(f"Failed to get PyBoy screen: {e}")
            return np.zeros((144, 160, 3), dtype=np.uint8)

    def _apply_pyboy_buttons(self, button_names: list) -> None:
        """Apply button presses to PyBoy."""
        if self.emulator is None or self.emulator_type != 'pyboy':
            return

        try:
            # Release all buttons first
            self.emulator.button_release('a')
            self.emulator.button_release('b')
            self.emulator.button_release('start')
            self.emulator.button_release('select')
            self.emulator.button_release('up')
            self.emulator.button_release('down')
            self.emulator.button_release('left')
            self.emulator.button_release('right')

            # Press requested buttons
            for btn in button_names:
                btn_lower = btn.lower()
                if btn_lower in ['a', 'b', 'start', 'select', 'up', 'down', 'left', 'right']:
                    self.emulator.button_press(btn_lower)
        except Exception as e:
            logger.warning(f"Error applying PyBoy buttons: {e}")

    def _build_nes_action(self, button_names: list) -> int:
        """
        Convert button names to nes-py action index.

        Args:
            button_names: List of button names (e.g., ['A', 'RIGHT'])

        Returns:
            Action index (0-17 for nes-py)
        """
        # nes-py action space is 0-17
        # For simplicity, map first button to action
        if not button_names:
            return 0

        first_btn = button_names[0].upper()
        if first_btn in self.NES_ACTION_MAP:
            return self.NES_ACTION_MAP[first_btn]

        return 0


# Global singleton instance
emulator_service = EmulatorService()
