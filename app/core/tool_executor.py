import asyncio
from typing import Any

from app.config import settings
from app.tools.base import ToolExecutionError, TransientToolError
from app.tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.registry.get(tool_name)
        if not tool:
            return {'ok': False, 'data': None, 'error': f'Unknown tool: {tool_name}', 'user_safe': True}

        attempts = max(1, settings.RETRY_COUNT)
        for attempt in range(1, attempts + 1):
            try:
                return await tool.execute(**arguments)
            except TransientToolError as exc:
                if attempt == attempts:
                    return {'ok': False, 'data': None, 'error': str(exc), 'user_safe': True}
                await asyncio.sleep(settings.RETRY_BACKOFF_S * attempt)
            except ToolExecutionError as exc:
                return {'ok': False, 'data': None, 'error': str(exc), 'user_safe': True}
            except Exception as exc:  # noqa: BLE001
                return {'ok': False, 'data': None, 'error': f'Unexpected tool error: {exc}', 'user_safe': False}

        return {'ok': False, 'data': None, 'error': 'Tool failed after retries', 'user_safe': True}
