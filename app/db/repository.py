import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Appointment, ChatSession, Message, Patient, Prescription, TelemetryLog


class Repository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, patient_id: str | None = None, metadata: dict[str, Any] | None = None) -> ChatSession:
        now = datetime.utcnow()
        session = ChatSession(
            patient_id=patient_id,
            metadata_json=json.dumps(metadata or {}),
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=settings.SESSION_TTL_HOURS),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        return self.db.scalar(select(ChatSession).where(ChatSession.id == session_id))

    def touch_session(self, session: ChatSession) -> ChatSession:
        session.updated_at = datetime.utcnow()
        session.expires_at = datetime.utcnow() + timedelta(hours=settings.SESSION_TTL_HOURS)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def list_messages(self, session_id: str) -> list[Message]:
        rows = self.db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc()))
        return list(rows)

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        name: str | None = None,
        tool_call_id: str | None = None,
        tool_calls_json: str | None = None,
    ) -> Message:
        msg = Message(session_id=session_id, role=role, content=content, name=name, tool_call_id=tool_call_id, tool_calls_json=tool_calls_json)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def prune_messages(self, session_id: str, max_context_messages: int) -> None:
        messages = self.list_messages(session_id)
        non_system = [m for m in messages if m.role != 'system']
        if len(non_system) <= max_context_messages:
            return
        remove_count = len(non_system) - max_context_messages
        to_remove = non_system[:remove_count]
        for msg in to_remove:
            self.db.delete(msg)
        self.db.commit()

    def get_patient(self, patient_id: str) -> Patient | None:
        # Try exact UUID match first
        patient = self.db.scalar(select(Patient).where(Patient.id == patient_id))
        if patient:
            return patient
        # Fall back to case-insensitive name search (allows LLM to pass names)
        needle = patient_id.replace('_', ' ').strip()
        return self.db.scalar(
            select(Patient).where(Patient.full_name.ilike(f'%{needle}%'))
        )

    def update_patient_notes(self, patient_id: str, notes: str) -> Patient | None:
        patient = self.get_patient(patient_id)
        if not patient:
            return None
        patient.notes = notes
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def list_patients(self) -> list[Patient]:
        return list(self.db.scalars(select(Patient).order_by(Patient.full_name.asc())))

    def create_prescription(
        self,
        patient_id: str,
        drug_name: str,
        dose: str,
        frequency: str,
        route: str | None = None,
        duration_days: int | None = None,
        status: str = 'draft',
    ) -> Prescription:
        rx = Prescription(
            patient_id=patient_id,
            drug_name=drug_name,
            dose=dose,
            frequency=frequency,
            route=route,
            duration_days=duration_days,
            status=status,
        )
        self.db.add(rx)
        self.db.commit()
        self.db.refresh(rx)
        return rx

    def create_appointment(
        self,
        patient_id: str,
        scheduled_at: datetime,
        department: str | None,
        clinician_name: str | None,
        status: str = 'scheduled',
    ) -> Appointment:
        appt = Appointment(
            patient_id=patient_id,
            scheduled_at=scheduled_at,
            department=department,
            clinician_name=clinician_name,
            status=status,
        )
        self.db.add(appt)
        self.db.commit()
        self.db.refresh(appt)
        return appt

    def log_event(self, trace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        log = TelemetryLog(trace_id=trace_id, event_type=event_type, payload_json=json.dumps(payload))
        self.db.add(log)
        self.db.commit()

    def seed_patients(self) -> None:
        existing = self.db.scalar(select(Patient).limit(1))
        if existing:
            return
        patients = [
            Patient(
                full_name='Margaret Chen',
                dob=date(1955, 3, 12),
                sex='female',
                phone='555-2001',
                notes='Diagnosis: Type 2 Diabetes Mellitus, Hypertension. Current medications: Metformin 500mg twice daily, Lisinopril 10mg daily.',
            ),
            Patient(
                full_name='Robert Okafor',
                dob=date(1968, 7, 24),
                sex='male',
                phone='555-2002',
                notes='Diagnosis: Atrial Fibrillation, DVT history. Current medications: Warfarin 5mg daily, Metoprolol 25mg twice daily.',
            ),
            Patient(
                full_name='Sarah Williams',
                dob=date(1982, 11, 8),
                sex='female',
                phone='555-2003',
                notes='Diagnosis: Asthma, Generalized Anxiety Disorder. Current medications: Albuterol inhaler PRN, Sertraline 50mg daily.',
            ),
            Patient(
                full_name='James Patel',
                dob=date(1945, 2, 17),
                sex='male',
                phone='555-2004',
                notes='Diagnosis: COPD, Chronic Kidney Disease Stage 3. Current medications: Tiotropium 18mcg daily, Furosemide 40mg daily.',
            ),
        ]
        self.db.add_all(patients)
        self.db.commit()
