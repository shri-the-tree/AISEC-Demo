from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import Repository
from app.tools.base import BaseTool, ToolExecutionError


class PatientDBTool(BaseTool):
    name = 'get_patient_record'
    description = 'Get a patient record by patient UUID or patient name.'

    def __init__(self, db: Session):
        self.repo = Repository(db)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'patient_id': {'type': 'string', 'description': 'Patient UUID or patient full name (e.g. "James Patel")'},
            },
            'required': ['patient_id'],
            'additionalProperties': False,
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        patient_id = kwargs.get('patient_id')
        if not patient_id:
            raise ToolExecutionError('patient_id is required')
        patient = self.repo.get_patient(patient_id)
        if not patient:
            return {'ok': False, 'data': None, 'error': f'Patient {patient_id} not found', 'user_safe': True}
        return {
            'ok': True,
            'data': {
                'id': patient.id,
                'full_name': patient.full_name,
                'dob': str(patient.dob),
                'sex': patient.sex,
                'phone': patient.phone,
                'email': patient.email,
                'notes': patient.notes,
            },
            'error': None,
            'user_safe': True,
        }
