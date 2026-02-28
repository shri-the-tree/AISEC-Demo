import json
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool, ToolExecutionError


class DrugInteractionTool(BaseTool):
    name = 'check_drug_interaction'
    description = 'Check interactions between two medications using local static data.'

    def __init__(self, data_path: str = 'app/rag/data/drug_interactions.json'):
        self.data_path = Path(data_path)
        self.interactions = self._load()

    def _load(self) -> dict[str, str]:
        if not self.data_path.exists():
            return {}
        raw = json.loads(self.data_path.read_text(encoding='utf-8-sig'))
        out = {}
        for item in raw:
            key = '|'.join(sorted([item['drug_a'].lower(), item['drug_b'].lower()]))
            out[key] = item['note']
        return out

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'drug_a': {'type': 'string'},
                'drug_b': {'type': 'string'},
            },
            'required': ['drug_a', 'drug_b'],
            'additionalProperties': False,
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        drug_a = kwargs.get('drug_a')
        drug_b = kwargs.get('drug_b')
        if not drug_a or not drug_b:
            raise ToolExecutionError('drug_a and drug_b are required')
        key = '|'.join(sorted([drug_a.lower(), drug_b.lower()]))
        note = self.interactions.get(key)
        if note:
            return {'ok': True, 'data': {'interaction': True, 'note': note}, 'error': None, 'user_safe': True}
        return {
            'ok': True,
            'data': {'interaction': False, 'note': f'No known interaction in local dataset for {drug_a} and {drug_b}.'},
            'error': None,
            'user_safe': True,
        }
