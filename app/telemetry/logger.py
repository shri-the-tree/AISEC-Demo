from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.repository import Repository


class TelemetryLogger:
    def __init__(self, db: Session):
        self.repo = Repository(db)

    def log(self, trace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        data = payload.copy()
        if settings.REDACT_LOGS:
            data = {'redacted': True, 'keys': sorted(payload.keys())}
        print(f'[{trace_id}] {event_type}: {data}')
        self.repo.log_event(trace_id=trace_id, event_type=event_type, payload=data)
