from abc import ABC, abstractmethod
from typing import Any


class ToolExecutionError(Exception):
    pass


class TransientToolError(ToolExecutionError):
    pass


class BaseTool(ABC):
    name: str = ''
    description: str = ''
    optional: bool = False

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        raise NotImplementedError

    def schema(self) -> dict[str, Any]:
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self.parameters,
            },
        }

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError
