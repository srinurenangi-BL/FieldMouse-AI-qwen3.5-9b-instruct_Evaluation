from __future__ import annotations

import asyncio
import httpx
from config import LLM_ENDPOINT_URL, LLM_MODEL, LLM_TIMEOUT_SECONDS, LLM_TEMPERATURE


class LLMClientError(Exception):
    """Custom exception raised when HTTP client fails to get response from LLM."""
    pass


async def send_prompt(prompt_text: str, is_json_format: bool = False) -> str:
    """Sends a prompt string to the LLM endpoint with timeout and up to 1 retry.
    
    Returns the raw text string returned by the LLM.
    """
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a fair, precise code evaluator. Return strictly what was requested."
            },
            {
                "role": "user",
                "content": prompt_text
            }
        ],
        "stream": False,
        "keep_alive": 0,
        "options": {
            "temperature": LLM_TEMPERATURE
        }
    }

    if is_json_format:
        payload["format"] = "json"

    max_attempts = 2
    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(LLM_ENDPOINT_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if content:
                    return str(content)
                raise LLMClientError("LLM response contained empty content.")

        except (httpx.HTTPError, httpx.TimeoutException, LLMClientError) as exc:
            last_exception = exc
            if attempt < max_attempts:
                await asyncio.sleep(1.0)
                continue

    raise LLMClientError(f"Failed to communicate with LLM after {max_attempts} attempts: {last_exception}")
