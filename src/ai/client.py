"""
LLM Provider Client interface and implementations for Gemini, OpenAI, and custom endpoints.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """
    Abstract interface for LLM completions.
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        """
        Send a prompt with system instructions and return raw text/JSON response.
        """
        pass


class OpenAICompatibleClient(BaseLLMClient):
    """
    Client for OpenAI, Groq, Ollama, OpenRouter, or any OpenAI-compatible chat API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        raw_base = base_url or os.getenv("LLM_API_BASE") or "https://api.openai.com/v1"
        self.base_url = raw_base.rstrip("/")
        self.model = os.getenv("LLM_MODEL", model)
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"])


class GeminiLLMClient(BaseLLMClient):
    """
    Client for Google Gemini API structured generation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-flash",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        self.model = os.getenv("GEMINI_MODEL", model)
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini API.")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("Empty response parts from Gemini API.")
            return str(parts[0].get("text", "{}"))


def get_llm_client() -> BaseLLMClient | None:
    """
    Factory function to retrieve configured LLM client.
    Returns GeminiLLMClient, OpenAICompatibleClient, or None if no keys configured.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        logger.info("Configured GeminiLLMClient for requirement extraction.")
        return GeminiLLMClient(api_key=gemini_key)

    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if openai_key:
        logger.info("Configured OpenAICompatibleClient for requirement extraction.")
        return OpenAICompatibleClient(api_key=openai_key)

    custom_base = os.getenv("LLM_API_BASE")
    if custom_base:
        logger.info("Configured Generic OpenAI-compatible client at %s", custom_base)
        return OpenAICompatibleClient(base_url=custom_base, api_key="dummy")

    logger.debug("No LLM API keys detected. Falling back to HeuristicExtractor.")
    return None
