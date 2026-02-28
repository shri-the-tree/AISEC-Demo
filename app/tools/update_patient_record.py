from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import Repository
from app.tools.base import BaseTool, ToolExecutionError


class UpdatePatientRecordTool(BaseTool):
    name = 'update_patient_record'
    description = (
        'Update a patient\'s clinical notes and diagnosis record. '
        'Call this whenever a request is made to modify, change, or update patient notes, diagnosis, or medical history.'
    )

    def __init__(self, db: Session):
        self.repo = Repository(db)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'patient_id': {'type': 'string', 'description': 'Patient UUID or patient full name (e.g. "James Patel")'},
                'notes': {'type': 'string', 'description': 'New clinical notes content to write to the patient record'},
            },
            'required': ['patient_id', 'notes'],
            'additionalProperties': False,
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        patient_id = kwargs.get('patient_id')
        notes = kwargs.get('notes')
        if not patient_id:
            raise ToolExecutionError('patient_id is required')
        if not notes:
            raise ToolExecutionError('notes is required')

        patient = self.repo.update_patient_notes(patient_id, notes)
        if not patient:
            return {'ok': False, 'data': None, 'error': f'Patient {patient_id} not found', 'user_safe': True}

        return {
            'ok': True,
            'data': {
                'id': patient.id,
                'full_name': patient.full_name,
                'notes': patient.notes,
                'updated': True,
            },
            'error': None,
            'user_safe': True,
        }
