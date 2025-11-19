"""
ROM Manager Service - Handles ROM file uploads, validation, and switching.
"""
import logging
import os
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported ROM formats and their corresponding systems
ROM_SIGNATURES = {
    b'NES\x1a': 'NES',           # NES ROM header (iNES format)
}

# File extension to system mapping (fallback)
# Game Boy/GBC detection by extension since signature matching is unreliable
EXTENSION_MAPPING = {
    '.nes': 'NES',
    '.gb': 'GB',
    '.gbc': 'GBC',               # Game Boy Color
    '.gbl': 'GB',                # Game Boy Link
}

# Supported systems (PyBoy for GB/GBC, nes-py for NES)
SUPPORTED_SYSTEMS = ['NES', 'GB', 'GBC']


class ROMManagerService:
    """Service for managing ROM files and game loading."""

    def __init__(self, roms_directory: str = "/tmp/game_roms"):
        """
        Initialize ROM manager.

        Args:
            roms_directory: Directory to store uploaded ROMs
        """
        self.roms_directory = Path(roms_directory)
        self.roms_directory.mkdir(parents=True, exist_ok=True)
        self.active_rom_path: Optional[Path] = None
        self.active_rom_system: Optional[str] = None
        self.active_rom_name: Optional[str] = None
        logger.info(f"ROM Manager initialized with directory: {self.roms_directory}")

    def detect_system(self, rom_data: bytes, filename: str) -> str:
        """
        Detect gaming system from ROM data and filename.

        Args:
            rom_data: ROM file bytes
            filename: ROM filename

        Returns:
            System name (NES, GB, GBC)
        """
        # Try signature matching first
        for signature, system in ROM_SIGNATURES.items():
            if rom_data.startswith(signature):
                logger.info(f"Detected {system} by signature")
                return system

        # Try extension matching (more reliable for Game Boy)
        ext = Path(filename).suffix.lower()
        if ext in EXTENSION_MAPPING:
            system = EXTENSION_MAPPING[ext]
            logger.info(f"Detected {system} by extension {ext}")
            return system

        # Default to NES if no match
        logger.info(f"Unknown ROM format {filename}, defaulting to NES")
        return "NES"

    def upload_rom(self, rom_data: bytes, filename: str) -> Tuple[str, str, int]:
        """
        Upload and store a ROM file.

        Args:
            rom_data: ROM file bytes
            filename: Original ROM filename

        Returns:
            Tuple of (system, filepath, file_size_bytes)

        Raises:
            ValueError: If ROM is invalid or too large
        """
        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024
        if len(rom_data) > max_size:
            raise ValueError(f"ROM too large ({len(rom_data)} bytes, max {max_size})")

        if len(rom_data) == 0:
            raise ValueError("ROM file is empty")

        # Detect system
        system = self.detect_system(rom_data, filename)

        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        rom_path = self.roms_directory / safe_filename

        # Write ROM file
        rom_path.write_bytes(rom_data)
        logger.info(f"ROM uploaded: {filename} -> {rom_path} ({system})")

        return system, str(rom_path), len(rom_data)

    def switch_rom(self, rom_path: str, system: str) -> bool:
        """
        Switch to a different ROM (called after upload).

        Args:
            rom_path: Full path to ROM file
            system: Gaming system

        Returns:
            True if switch successful
        """
        rom_file = Path(rom_path)

        if not rom_file.exists():
            logger.error(f"ROM file not found: {rom_path}")
            return False

        self.active_rom_path = rom_file
        self.active_rom_system = system
        self.active_rom_name = rom_file.name

        logger.info(f"Switched to ROM: {self.active_rom_name} ({system})")
        return True

    def get_active_rom(self) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
        """
        Get currently active ROM.

        Returns:
            Tuple of (rom_path, system, rom_name)
        """
        return self.active_rom_path, self.active_rom_system, self.active_rom_name

    def validate_rom(self, rom_path: str) -> bool:
        """
        Validate that ROM file is accessible and valid.

        Args:
            rom_path: Path to ROM file

        Returns:
            True if ROM is valid
        """
        rom_file = Path(rom_path)

        if not rom_file.exists():
            logger.warning(f"ROM file does not exist: {rom_path}")
            return False

        if not rom_file.is_file():
            logger.warning(f"ROM path is not a file: {rom_path}")
            return False

        if rom_file.stat().st_size == 0:
            logger.warning(f"ROM file is empty: {rom_path}")
            return False

        return True

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize ROM filename to prevent directory traversal.

        Args:
            filename: Original filename

        Returns:
            Safe filename
        """
        # Remove path separators and parent directory references
        safe = filename.replace('\\', '_').replace('/', '_').replace('..', '_')
        # Keep only alphanumeric, dots, dashes, underscores
        safe = "".join(c if c.isalnum() or c in '._-' else '_' for c in safe)
        return safe or "rom.bin"

    def cleanup_old_roms(self) -> None:
        """Remove old ROM files when a new one is active."""
        if not self.active_rom_path:
            return

        for rom_file in self.roms_directory.glob('*'):
            if rom_file.is_file() and rom_file != self.active_rom_path:
                try:
                    rom_file.unlink()
                    logger.info(f"Cleaned up old ROM: {rom_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete old ROM {rom_file.name}: {e}")


# Global singleton instance
rom_manager = ROMManagerService()
