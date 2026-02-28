from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import Repository
from app.tools.base import BaseTool, ToolExecutionError


class AppointmentTool(BaseTool):
    name = 'book_appointment'
    description = 'Book an appointment for a patient. Call this whenever scheduling, booking, or appointment creation is requested.'

    def __init__(self, db: Session):
        self.repo = Repository(db)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'patient_id': {'type': 'string', 'description': 'Patient UUID or patient full name (e.g. "James Patel")'},
                'scheduled_at': {'type': 'string', 'description': 'ISO datetime string'},
                'department': {'type': 'string'},
                'clinician_name': {'type': 'string'},
            },
            'required': ['patient_id', 'scheduled_at'],
            'additionalProperties': False,
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        patient_id = kwargs.get('patient_id')
        if not patient_id:
            raise ToolExecutionError('patient_id is required')
        patient = self.repo.get_patient(patient_id)
        if not patient:
            return {'ok': False, 'data': None, 'error': f'Patient {patient_id} not found', 'user_safe': True}

        scheduled_at_raw = kwargs.get('scheduled_at')
        if not scheduled_at_raw:
            raise ToolExecutionError('scheduled_at is required')
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_raw)
        except ValueError as exc:
            raise ToolExecutionError('scheduled_at must be ISO datetime') from exc

        appt = self.repo.create_appointment(
            patient_id=patient.id,
            scheduled_at=scheduled_at,
            department=kwargs.get('department'),
            clinician_name=kwargs.get('clinician_name'),
            status='scheduled',
        )
        return {
            'ok': True,
            'data': {
                'id': appt.id,
                'patient_id': appt.patient_id,
                'scheduled_at': appt.scheduled_at.isoformat(),
                'department': appt.department,
                'clinician_name': appt.clinician_name,
                'status': appt.status,
            },
            'error': None,
            'user_safe': True,
        }
