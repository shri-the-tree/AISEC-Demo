from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Prescription
from app.db.repository import Repository
from app.tools.base import BaseTool, ToolExecutionError


class ViewPrescriptionsTool(BaseTool):
    name = 'view_prescriptions'
    description = (
        'View current prescriptions and medication timings for a patient. '
        'Returns drug name, dose, route, frequency, duration, and status.'
    )

    def __init__(self, db: Session):
        self.db = db
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

        rows = list(
            self.db.scalars(
                select(Prescription)
                .where(Prescription.patient_id == patient.id)
                .order_by(Prescription.created_at.desc())
            )
        )

        prescriptions = [
            {
                'drug_name': rx.drug_name,
                'dose': rx.dose,
                'route': rx.route,
                'frequency': rx.frequency,
                'duration_days': rx.duration_days,
                'status': rx.status,
                'created_at': rx.created_at.isoformat(),
            }
            for rx in rows
        ]

        # Also include medications from patient notes
        return {
            'ok': True,
            'data': {
                'patient_name': patient.full_name,
                'prescriptions': prescriptions,
                'medication_notes': patient.notes or '',
            },
            'error': None,
            'user_safe': True,
        }
