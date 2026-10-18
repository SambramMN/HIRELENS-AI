import json
import logging
from typing import Any, Dict, Optional
import httpx
from config import config

logger = logging.getLogger(__name__)

class LLMService:
    """Configurable OpenAI-compatible LLM service with graceful fallback."""
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.base_url = config.OPENAI_BASE_URL.rstrip("/")
        self.model = config.OPENAI_MODEL
        self.timeout = config.LLM_TIMEOUT_SECONDS

    @property
    def is_configured(self) -> bool:
        """Returns True if an API key is provided and non-empty."""
        return bool(self.api_key and len(self.api_key) > 5)

    def call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2
    ) -> Optional[Dict[str, Any]]:
        """
        Sends request to OpenAI-compatible endpoint expecting a JSON object.
        Returns parsed dictionary if successful, or None if unavailable/failed.
        """
        if not self.is_configured:
            logger.info("LLM API key not configured. Using deterministic fallback.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt + "\nYou MUST reply with valid JSON only."},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.warning(f"LLM API returned status {response.status_code}: {response.text}")
                    return None

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.warning(f"LLM call failed or timed out: {e}. Falling back to rule-based engine.")
            return None

llm_service = LLMService()
