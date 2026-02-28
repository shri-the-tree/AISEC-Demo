from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import Repository
from app.tools.base import BaseTool, ToolExecutionError


class PrescriptionTool(BaseTool):
    name = 'issue_prescription'
    description = 'Issue a prescription for a patient. Call this whenever a prescription, medication order, or drug is requested for a patient.'

    def __init__(self, db: Session):
        self.repo = Repository(db)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'patient_id': {'type': 'string', 'description': 'Patient UUID or patient full name (e.g. "James Patel")'},
                'drug_name': {'type': 'string'},
                'dose': {'type': 'string'},
                'frequency': {'type': 'string'},
                'route': {'type': 'string'},
                'duration_days': {'type': 'integer'},
            },
            'required': ['patient_id', 'drug_name', 'dose', 'frequency'],
            'additionalProperties': False,
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        patient_id = kwargs.get('patient_id')
        if not patient_id:
            raise ToolExecutionError('patient_id is required')
        patient = self.repo.get_patient(patient_id)
        if not patient:
            return {'ok': False, 'data': None, 'error': f'Patient {patient_id} not found', 'user_safe': True}

        rx = self.repo.create_prescription(
            patient_id=patient.id,
            drug_name=kwargs['drug_name'],
            dose=kwargs['dose'],
            frequency=kwargs['frequency'],
            route=kwargs.get('route'),
            duration_days=kwargs.get('duration_days'),
            status='draft',
        )
        return {
            'ok': True,
            'data': {
                'id': rx.id,
                'patient_id': rx.patient_id,
                'drug_name': rx.drug_name,
                'dose': rx.dose,
                'frequency': rx.frequency,
                'route': rx.route,
                'duration_days': rx.duration_days,
                'status': rx.status,
                'created_at': rx.created_at.isoformat(),
            },
            'error': None,
            'user_safe': True,
        }
