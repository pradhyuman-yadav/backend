"""
Model Agent Service - Integrates with llava-phi (Ollama) to control games.
Sends game state to model and receives action decisions.
"""
import logging
import json
import base64
from typing import List, Optional, Dict, Any
import asyncio
import httpx

logger = logging.getLogger(__name__)


class ModelAgentService:
    """Service for integrating LLM model (llava-phi) with game emulation."""

    def __init__(self, ollama_base_url: str = "http://localhost:11434", model_name: str = "llava-phi"):
        """
        Initialize model agent.

        Args:
            ollama_base_url: Ollama server base URL
            model_name: Model name to use (llava-phi for multimodal)
        """
        self.ollama_base_url = ollama_base_url
        self.model_name = model_name
        self.reasoning_enabled = False
        self.frame_skip = 1  # Analyze every frame by default
        self.frame_counter = 0
        logger.info(f"Model Agent initialized with {model_name} at {ollama_base_url}")

    async def get_action(
        self,
        screen_base64: str,
        button_map: Dict[str, int],
        memory_dump: Optional[bytes] = None,
        game_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get action decision from model based on game state.

        Args:
            screen_base64: Base64 encoded game screenshot
            button_map: Available buttons for the game
            memory_dump: Optional raw memory dump
            game_info: Optional game metadata

        Returns:
            Dictionary with 'buttons' (list) and optional 'reasoning' (str)
        """
        self.frame_counter += 1

        # Skip frames if frame_skip is set
        if self.frame_counter % self.frame_skip != 0:
            return {"buttons": [], "reasoning": None, "skipped": True}

        try:
            # Build prompt for the model
            available_buttons = list(button_map.keys())
            prompt = self._build_prompt(available_buttons, game_info, memory_dump)

            # Call llava-phi with image
            response = await self._call_vision_model(
                image_base64=screen_base64,
                prompt=prompt,
                reasoning=self.reasoning_enabled,
            )

            # Parse response to extract actions
            actions = self._parse_model_response(response, available_buttons)

            return {
                "buttons": actions,
                "reasoning": response.get("reasoning") if self.reasoning_enabled else None,
                "raw_response": response.get("raw_text"),
                "skipped": False,
            }

        except Exception as e:
            logger.error(f"Failed to get model action: {str(e)}")
            return {"buttons": [], "reasoning": str(e), "skipped": True}

    async def _call_vision_model(
        self, image_base64: str, prompt: str, reasoning: bool = False
    ) -> Dict[str, Any]:
        """
        Call llava-phi vision model via Ollama.

        Args:
            image_base64: Base64 encoded image
            prompt: Text prompt
            reasoning: Whether to request reasoning

        Returns:
            Model response dictionary
        """
        url = f"{self.ollama_base_url}/api/generate"

        # Build request payload
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "temperature": 0.3,  # Lower temperature for more consistent actions
            "top_p": 0.9,
            "num_predict": 150 if reasoning else 50,  # Longer for reasoning
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                raw_text = result.get("response", "")

                return {
                    "raw_text": raw_text,
                    "reasoning": raw_text if reasoning else None,
                }

        except Exception as e:
            logger.error(f"Model API call failed: {str(e)}")
            raise

    def _parse_model_response(self, response: Dict[str, Any], available_buttons: List[str]) -> List[str]:
        """
        Parse model response to extract button actions.

        Args:
            response: Model response dictionary
            available_buttons: List of available button names

        Returns:
            List of buttons to press
        """
        raw_text = response.get("raw_text", "").upper()

        # Extract buttons mentioned in response
        buttons_pressed = []

        for button in available_buttons:
            # Check for button names or common aliases
            if button.upper() in raw_text or self._check_button_aliases(button, raw_text):
                buttons_pressed.append(button)

        # Look for JSON format response
        if "{" in raw_text and "}" in raw_text:
            try:
                # Extract JSON from response
                json_start = raw_text.find("{")
                json_end = raw_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = raw_text[json_start:json_end]
                    json_obj = json.loads(json_str.lower())

                    if "buttons" in json_obj:
                        parsed = json_obj["buttons"]
                        if isinstance(parsed, list):
                            # Validate buttons
                            valid = [b for b in parsed if b.upper() in [x.upper() for x in available_buttons]]
                            if valid:
                                buttons_pressed = valid
            except Exception as e:
                logger.debug(f"Failed to parse JSON response: {e}")

        # Limit concurrent buttons to 2 (avoid too many simultaneous inputs)
        return buttons_pressed[:2] if buttons_pressed else []

    def _check_button_aliases(self, button: str, text: str) -> bool:
        """
        Check for button aliases in text.

        Args:
            button: Button name
            text: Text to search

        Returns:
            True if alias found
        """
        aliases = {
            "UP": ["UP", "NORTH", "FORWARD"],
            "DOWN": ["DOWN", "SOUTH", "BACKWARD"],
            "LEFT": ["LEFT", "WEST"],
            "RIGHT": ["RIGHT", "EAST"],
            "A": ["A", "JUMP", "FIRE", "ACTION"],
            "B": ["B", "BACK", "CANCEL"],
            "START": ["START", "PAUSE"],
            "SELECT": ["SELECT"],
        }

        if button.upper() not in aliases:
            return False

        for alias in aliases[button.upper()]:
            if alias in text:
                return True

        return False

    def _build_prompt(
        self, available_buttons: List[str], game_info: Optional[Dict], memory_info: Optional[bytes]
    ) -> str:
        """
        Build prompt for the model.

        Args:
            available_buttons: List of available buttons
            game_info: Game metadata
            memory_info: Memory dump data

        Returns:
            Prompt string
        """
        prompt = f"""You are playing a classic arcade/retro game. Analyze the current screen and decide what action to take.

Available controls: {', '.join(available_buttons)}

Your task:
1. Analyze the game screen carefully
2. Identify the player character, enemies, obstacles
3. Determine the optimal action to progress in the game
4. Respond with ONLY the buttons to press (e.g., "UP", "RIGHT", "A" or combinations like "RIGHT A")

{"Explain your reasoning briefly" if self.reasoning_enabled else "Keep your response short and direct."}

What buttons should be pressed now?"""

        if game_info:
            prompt += f"\n\nGame info: {game_info}"

        return prompt

    def set_reasoning_enabled(self, enabled: bool) -> None:
        """Enable/disable reasoning output."""
        self.reasoning_enabled = enabled
        logger.info(f"Reasoning enabled: {enabled}")

    def set_frame_skip(self, frame_skip: int) -> None:
        """
        Set frame skip (analyze every Nth frame).

        Args:
            frame_skip: Skip N-1 frames between analysis (1 = every frame)
        """
        self.frame_skip = max(1, frame_skip)
        logger.info(f"Frame skip set to: {self.frame_skip}")

    def reset(self) -> None:
        """Reset frame counter for new game."""
        self.frame_counter = 0


# Global singleton instance
model_agent = ModelAgentService()
