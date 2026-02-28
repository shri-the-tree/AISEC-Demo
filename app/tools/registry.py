from sqlalchemy.orm import Session

from app.core.session_manager import ROLE_PERMISSIONS
from app.tools.appointment import AppointmentTool
from app.tools.drug_interaction import DrugInteractionTool
from app.tools.patient_db import PatientDBTool
from app.tools.prescription import PrescriptionTool
from app.tools.update_patient_record import UpdatePatientRecordTool
from app.tools.view_prescriptions import ViewPrescriptionsTool

# Tools available to all roles when guardrails are ON (via ROLE_PERMISSIONS)
# update_patient_record is intentionally absent from ROLE_PERMISSIONS —
# it is only exposed when guardrails are OFF (all schemas mode), making it
# a dramatic demonstration of what an unprotected system allows.
_GUARDED_TOOLS = ['get_patient_record', 'issue_prescription', 'check_drug_interaction', 'book_appointment', 'view_prescriptions']


class ToolRegistry:
    def __init__(self, db: Session):
        self._tools = {
            'get_patient_record': PatientDBTool(db),
            'issue_prescription': PrescriptionTool(db),
            'check_drug_interaction': DrugInteractionTool(),
            'book_appointment': AppointmentTool(db),
            'view_prescriptions': ViewPrescriptionsTool(db),
            'update_patient_record': UpdatePatientRecordTool(db),
        }

    def schemas(self, role: str | None = None) -> list[dict]:
        """Return tool schemas filtered by role (guardrails ON) or all schemas (guardrails OFF)."""
        if role:
            allowed = ROLE_PERMISSIONS.get(role, {}).get('tools', [])
            return [tool.schema() for name, tool in self._tools.items() if name in allowed]
        return [tool.schema() for tool in self._tools.values()]

    def get(self, name: str):
        return self._tools.get(name)

    def is_allowed(self, tool_name: str, role: str) -> bool:
        allowed = ROLE_PERMISSIONS.get(role, {}).get('tools', [])
        return tool_name in allowed
