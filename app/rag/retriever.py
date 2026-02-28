import json
from pathlib import Path

from app.config import settings
from app.rag.embeddings import SimpleEmbeddings


class Retriever:
    def __init__(self):
        self.embeddings = SimpleEmbeddings()
        self.entries = self._load_entries()
        self.vectors = self.embeddings.embed_many([e['text'] for e in self.entries])

    def _load_entries(self) -> list[dict]:
        data_dir = Path(settings.RAG_DATA_DIR)
        out = []
        if not data_dir.exists():
            return out
        for file in data_dir.glob('*.json'):
            if file.name == 'drug_interactions.json':
                continue
            items = json.loads(file.read_text(encoding='utf-8-sig'))
            for item in items:
                out.append({'source': file.name, 'title': item.get('title', ''), 'text': item['text']})
        return out

    def retrieve(self, query: str, top_k: int | None = None, threshold: float | None = None) -> list[dict]:
        if not self.entries:
            return []
        top_k = top_k or settings.RAG_TOP_K
        threshold = threshold if threshold is not None else settings.RAG_SCORE_THRESHOLD

        q = self.embeddings.embed(query)
        scored = []
        for i, vec in enumerate(self.vectors):
            score = sum(a * b for a, b in zip(q, vec))
            if score >= threshold:
                scored.append((score, self.entries[i]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{'score': round(score, 4), **entry} for score, entry in scored[:top_k]]

    @staticmethod
    def format_as_tool_message(results: list[dict]) -> str:
        if not results:
            return 'No retrieval context found.'
        lines = []
        for r in results:
            lines.append(f"[{r['source']} | {r['title']} | score={r['score']}] {r['text']}")
        return '\n'.join(lines)
