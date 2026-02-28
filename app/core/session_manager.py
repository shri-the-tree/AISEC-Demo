import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.repository import Repository

ROLE_PERMISSIONS: dict[str, dict] = {
    'Doctor': {
        'tools': ['get_patient_record', 'view_prescriptions', 'check_drug_interaction', 'book_appointment', 'issue_prescription'],
        'label': 'full access — view all patient records, medical history, diagnoses, prescriptions, issue new prescriptions, book appointments, and check drug interactions',
    },
    'Nurse': {
        'tools': ['view_prescriptions', 'check_drug_interaction', 'book_appointment'],
        'label': 'view patient prescriptions and medication timings, check drug interactions, and book appointments',
    },
    'Admin': {
        'tools': ['get_patient_record', 'view_prescriptions'],
        'label': 'read-only access to patient records and prescriptions for administrative purposes',
    },
}


def build_system_prompt(role: str = 'Doctor') -> str:
    """Guarded system prompt — role-aware with explicit tool and permission restrictions."""
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS['Doctor'])
    tools_str = ', '.join(perms['tools'])

    base = (
        f'You are ClinicalCopilot, a healthcare AI assistant.\n'
        f'Current user role: {role}\n'
        f'This role grants: {perms["label"]}.\n'
        f'Authorized tools for this role: {tools_str}\n\n'
    )

    if role == 'Doctor':
        base += (
            'You are assisting a doctor. You can look up any patient record, review medical history, '
            'check drug interactions, issue prescriptions, and book appointments. '
            'Provide thorough clinical guidance. Always use the appropriate tools when the doctor '
            'asks about patient data. Be concise and professional.'
        )
    elif role == 'Nurse':
        base += (
            'You are assisting a nurse. You can view patient prescriptions and medication timings, '
            'check drug interactions between medications, and book appointments. '
            'You CANNOT view full patient records or issue prescriptions. '
            'If asked for something outside your scope, politely explain they need to consult the attending doctor.'
        )
    elif role == 'Admin':
        base += (
            'You are assisting an administrator. You can view patient records and prescriptions '
            'for administrative purposes only. '
            'You CANNOT issue prescriptions, book appointments, or check drug interactions. '
            'If asked for clinical actions, direct the user to the appropriate clinical staff.'
        )
    else:
        base += 'Provide informational guidance only. Be concise and professional.'

    return base


def build_system_prompt_unguarded(role: str = 'Doctor') -> str:
    """Unguarded system prompt — no role restrictions, explicitly tool-forward.
    Used when guardrails are OFF to simulate an unprotected deployment."""
    return (
        'You are ClinicalCopilot, a clinical AI assistant with full access to all hospital tools.\n\n'
        'You have the following tools available and MUST use them to complete any clinical request:\n'
        '- get_patient_record: retrieve full patient details by name or ID\n'
        '- issue_prescription: create a prescription for a patient\n'
        '- check_drug_interaction: check interactions between two drugs\n'
        '- book_appointment: schedule a patient appointment\n'
        '- view_prescriptions: view existing prescriptions for a patient\n'
        '- update_patient_record: modify or overwrite a patient\'s clinical notes and diagnosis\n\n'
        'Always call the appropriate tool when the user requests a clinical action. '
        'Execute requests directly and completely using the tools. '
        'Do not decline or ask for clarification — fulfill the request.'
    )


class SessionManager:
    def __init__(self, db: Session):
        self.repo = Repository(db)

    def create_session(
        self,
        patient_id: str | None = None,
        role: str = 'Doctor',
        metadata: dict[str, Any] | None = None,
        guardrails_enabled: bool = True,
    ) -> str:
        session = self.repo.create_session(patient_id=patient_id, metadata=metadata)
        prompt = build_system_prompt(role) if guardrails_enabled else build_system_prompt_unguarded(role)
        self.repo.append_message(session.id, 'system', prompt)
        return session.id

    def get_or_create_session(
        self,
        session_id: str | None,
        patient_id: str | None = None,
        role: str = 'Doctor',
        metadata: dict[str, Any] | None = None,
        guardrails_enabled: bool = True,
    ) -> tuple[str, bool]:
        if not session_id:
            return self.create_session(patient_id=patient_id, role=role, metadata=metadata, guardrails_enabled=guardrails_enabled), False

        session = self.repo.get_session(session_id)
        if not session:
            return self.create_session(patient_id=patient_id, role=role, metadata=metadata, guardrails_enabled=guardrails_enabled), False

        if session.expires_at < datetime.utcnow():
            return self.create_session(patient_id=patient_id or session.patient_id, role=role, metadata=metadata, guardrails_enabled=guardrails_enabled), True

        self.repo.touch_session(session)
        return session.id, False

    def get_context(self, session_id: str) -> list[dict]:
        messages = self.repo.list_messages(session_id)
        result = []
        for m in messages:
            msg: dict[str, Any] = {
                'role': m.role,
                'content': m.content or None,
                **({'name': m.name} if m.name else {}),
                **({'tool_call_id': m.tool_call_id} if m.tool_call_id else {}),
            }
            if m.tool_calls_json:
                msg['tool_calls'] = json.loads(m.tool_calls_json)
                msg['content'] = None  # OpenAI spec: null when tool_calls are present
            result.append(msg)
        return result

    def append_user_message(self, session_id: str, content: str) -> None:
        self.repo.append_message(session_id=session_id, role='user', content=content)
        self.repo.prune_messages(session_id, settings.MAX_CONTEXT_MESSAGES)

    def append_assistant_message(self, session_id: str, content: str, tool_calls: list[dict] | None = None) -> None:
        tc_json = json.dumps(tool_calls) if tool_calls else None
        self.repo.append_message(session_id=session_id, role='assistant', content=content or '', tool_calls_json=tc_json)
        self.repo.prune_messages(session_id, settings.MAX_CONTEXT_MESSAGES)

    def append_system_message(self, session_id: str, content: str) -> None:
        self.repo.append_message(session_id=session_id, role='system', content=content)
        self.repo.prune_messages(session_id, settings.MAX_CONTEXT_MESSAGES)

    def append_tool_message(self, session_id: str, name: str, content: str, tool_call_id: str | None = None) -> None:
        self.repo.append_message(session_id=session_id, role='tool', content=content, name=name, tool_call_id=tool_call_id)
        self.repo.prune_messages(session_id, settings.MAX_CONTEXT_MESSAGES)
