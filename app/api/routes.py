import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.agent_controller import AgentController
from app.core.session_manager import SessionManager
from app.db.repository import Repository
from app.db.session import get_db


router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)
    patient_id: str | None = None
    role: str = 'Doctor'
    guardrails_enabled: bool = True
    metadata: dict[str, Any] | None = None


class SessionCreateRequest(BaseModel):
    patient_id: str | None = None
    role: str = 'Doctor'
    metadata: dict[str, Any] | None = None


@router.get('/')
def root():
    return {'status': 'ok', 'message': 'ClinicalCopilot API', 'docs': '/docs', 'health': '/health'}


@router.post('/chat')
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    trace_id = str(uuid.uuid4())
    controller = AgentController(db)
    try:
        return await controller.handle_chat(
            trace_id=trace_id,
            session_id=payload.session_id,
            message=payload.message,
            patient_id=payload.patient_id,
            role=payload.role,
            metadata=payload.metadata,
            guardrails_enabled=payload.guardrails_enabled,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f'chat_failed: {exc}') from exc


@router.post('/sessions')
def create_session(payload: SessionCreateRequest, db: Session = Depends(get_db)):
    manager = SessionManager(db)
    session_id = manager.create_session(
        patient_id=payload.patient_id,
        role=payload.role,
        metadata=payload.metadata,
    )
    return {'session_id': session_id}


@router.get('/sessions/{session_id}')
def get_session(session_id: str, verbose: bool = Query(default=True), db: Session = Depends(get_db)):
    repo = Repository(db)
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session_not_found')

    response = {
        'id': session.id,
        'patient_id': session.patient_id,
        'metadata': json.loads(session.metadata_json or '{}'),
        'created_at': session.created_at.isoformat(),
        'updated_at': session.updated_at.isoformat(),
        'expires_at': session.expires_at.isoformat(),
    }
    if verbose:
        response['messages'] = [
            {
                'id': m.id,
                'role': m.role,
                'content': m.content,
                'name': m.name,
                'tool_call_id': m.tool_call_id,
                'created_at': m.created_at.isoformat(),
            }
            for m in repo.list_messages(session_id)
        ]
    return response


@router.get('/patients')
def list_patients(db: Session = Depends(get_db)):
    repo = Repository(db)
    patients = repo.list_patients()
    return [
        {
            'id': p.id,
            'full_name': p.full_name,
            'dob': str(p.dob),
            'sex': p.sex,
            'phone': p.phone,
            'notes': p.notes,
        }
        for p in patients
    ]


@router.get('/health')
def health():
    return {'status': 'ok', 'app': settings.APP_NAME}
