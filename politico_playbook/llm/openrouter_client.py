"""OpenRouter client wrapper — model-agnostic LLM access.

Uses the OpenAI Python SDK pointed at OpenRouter's OpenAI-compatible base URL.
Why OpenAI SDK and not openrouter-py: the OpenAI SDK is the de-facto standard,
better maintained, and OpenRouter mirrors its schema. Less abstraction = fewer
surprises.

Provider-specific features (Anthropic prompt caching, etc.) are handled via
`extra_body`. The caller doesn't have to know which provider is behind the
model_id; this module routes the appropriate hints.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from openai import OpenAI


logger = logging.getLogger("llm.openrouter")


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class LLMResponse:
    """Provider-agnostic response shape."""
    content: str                    # Raw response text.
    parsed: Optional[Any] = None    # Parsed JSON when structured-output mode used.
    model_id: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: Optional[str] = None


def _is_anthropic_model(model_id: str) -> bool:
    return model_id.startswith("anthropic/")


class OpenRouterClient:
    """Thin wrapper. Reads model + auth from env by default."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
        app_name: Optional[str] = None,
        app_url: Optional[str] = None,
    ):
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not set. Get a key from https://openrouter.ai/keys."
            )

        self.model_id = model_id or os.getenv("MODEL_ID")
        if not self.model_id:
            raise ValueError(
                "MODEL_ID not set. Pick one from https://openrouter.ai/models "
                "(e.g., 'deepseek/deepseek-v4-flash-20260423', "
                "'~anthropic/claude-haiku-latest', '~google/gemini-flash-latest')."
            )

        # OpenRouter likes attribution headers for analytics; not required.
        default_headers = {}
        app_name = app_name or os.getenv("OPENROUTER_APP_NAME")
        app_url = app_url or os.getenv("OPENROUTER_APP_URL")
        if app_url:
            default_headers["HTTP-Referer"] = app_url
        if app_name:
            default_headers["X-Title"] = app_name

        self.client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            default_headers=default_headers or None,
        )

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: Optional[dict] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        cache_system: bool = True,
    ) -> LLMResponse:
        """Single completion request. Returns provider-agnostic LLMResponse.

        Args:
            system:        System message — cached when routing to Anthropic
                           if cache_system=True.
            user:          User message — the task input.
            json_schema:   If provided, requests structured JSON output and
                           parses the response.
            temperature:   Sampling temperature.
            max_tokens:    Cap on response length.
            cache_system:  Whether to apply prompt caching to the system message
                           (only effective for Anthropic-routed models).
        """
        messages = [
            {"role": "system", "content": self._system_with_cache(system, cache_system)},
            {"role": "user", "content": user},
        ]

        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction",
                    "strict": True,
                    "schema": json_schema,
                },
            }

        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error("OpenRouter request failed: %s", e)
            raise

        choice = resp.choices[0]
        content = choice.message.content or ""

        parsed: Optional[Any] = None
        if json_schema is not None and content:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON response: %s", e)
                parsed = None

        usage = getattr(resp, "usage", None)
        return LLMResponse(
            content=content,
            parsed=parsed,
            model_id=self.model_id,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            finish_reason=choice.finish_reason,
        )

    def _system_with_cache(self, system_text: str, cache_system: bool) -> Any:
        """Wrap system text in the appropriate cache_control marker for Anthropic.

        For non-Anthropic models, return plain string. OpenRouter ignores cache
        markers for non-supporting providers.
        """
        if not cache_system or not _is_anthropic_model(self.model_id):
            return system_text

        # Anthropic style: a list of content blocks with cache_control marker.
        return [
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ]
