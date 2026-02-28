import asyncio
from typing import Any

import httpx

from app.config import settings


class LLMClient:
    def __init__(self):
        self.base_url = settings.GROQ_BASE_URL.rstrip('/')

    async def _chat_once(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, tool_choice: str | None = None) -> dict[str, Any]:
        if not settings.GROQ_API_KEY:
            return {
                'text': 'LLM API key is missing. Set GROQ_API_KEY to enable model responses.',
                'tool_calls': [],
                'raw': {},
                'model': model,
            }

        payload: dict[str, Any] = {
            'model': model,
            'messages': messages,
            'temperature': settings.TEMPERATURE,
            'max_tokens': settings.MAX_TOKENS,
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = tool_choice or settings.TOOL_CHOICE

        headers = {
            'Authorization': f'Bearer {settings.GROQ_API_KEY}',
            'Content-Type': 'application/json',
        }

        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_S)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f'{self.base_url}/chat/completions', headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()

        message = (raw.get('choices') or [{}])[0].get('message', {})
        tool_calls = message.get('tool_calls', []) or []
        text = message.get('content') or ''
        return {'text': text, 'tool_calls': tool_calls, 'raw': raw, 'model': model}

    async def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, tool_choice: str | None = None) -> dict[str, Any]:
        errors = []
        models = [settings.PRIMARY_MODEL]
        if settings.FALLBACK_MODEL and settings.FALLBACK_MODEL != settings.PRIMARY_MODEL:
            models.append(settings.FALLBACK_MODEL)

        for model in models:
            for attempt in range(1, settings.RETRY_COUNT + 1):
                try:
                    return await self._chat_once(model=model, messages=messages, tools=tools, tool_choice=tool_choice)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f'{model} attempt {attempt}: {exc}')
                    if attempt < settings.RETRY_COUNT:
                        await asyncio.sleep(settings.RETRY_BACKOFF_S * attempt)

        if settings.FAIL_OPEN:
            return {
                'text': 'The language model is unavailable right now. Please try again shortly.',
                'tool_calls': [],
                'raw': {'errors': errors},
                'model': 'none',
            }
        raise RuntimeError('LLM request failed: ' + '; '.join(errors))
