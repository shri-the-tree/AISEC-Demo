import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.core.guardrails import Guardrails
from app.core.llm_guardrails import LLMGuardrails
from app.core.llm_client import LLMClient
from app.core.session_manager import SessionManager
from app.core.tool_executor import ToolExecutor
from app.db.repository import Repository
from app.rag.retriever import Retriever
from app.telemetry.logger import TelemetryLogger
from app.tools.registry import ToolRegistry


CRITICAL_VIOLATION_TYPES = {
    'cross_patient_access',
    'unauthorized_tool',
    'pii_leak',
    'llm_prompt_guard',   # Prompt Guard 2 specialized detector — trust it alone
    'prompt_injection',   # Regex-matched patterns are high-confidence in medical context — hard stop
}


def _normalize_violation_type(violation: dict[str, Any]) -> str:
    vtype = str(violation.get('type', '')).strip()
    if vtype == 'llm_prompt_guard':
        return 'llm_prompt_guard'   # Keep distinct — maps to CRITICAL, hard stop without regex agreement
    if vtype == 'llm_safety_policy':
        category = str(violation.get('category', '')).strip().lower()
        if category:
            return category
        message = str(violation.get('message', '')).lower()
        if 'pii' in message:
            return 'pii_leak'
        if 'cross' in message and 'patient' in message:
            return 'cross_patient_access'
        if 'prompt injection' in message or 'jailbreak' in message:
            return 'prompt_injection'
        return 'policy_violation'
    return vtype


def _tag_violations(violations: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    tagged: list[dict[str, Any]] = []
    for violation in violations:
        item = dict(violation)
        item['source'] = source
        tagged.append(item)
    return tagged


def _should_block_balanced(
    regex_violations: list[dict[str, Any]],
    llm_violations: list[dict[str, Any]],
) -> bool:
    all_violations = regex_violations + llm_violations
    normalized_all = {_normalize_violation_type(v) for v in all_violations}

    # Hard stop for privacy and authorization violations.
    if normalized_all & CRITICAL_VIOLATION_TYPES:
        return True

    # For softer classes (prompt injection/policy flags), require agreement.
    if not regex_violations or not llm_violations:
        return False

    normalized_regex = {_normalize_violation_type(v) for v in regex_violations}
    normalized_llm = {_normalize_violation_type(v) for v in llm_violations}
    return bool(normalized_regex & normalized_llm)


def _render_tool_result(tool_name: str, result: dict[str, Any]) -> str:
    if not result.get('ok'):
        return ''

    data = result.get('data') or {}
    if not isinstance(data, dict):
        return ''

    if tool_name == 'get_patient_record':
        full_name = data.get('full_name', 'Unknown')
        pid = data.get('id', 'N/A')
        dob = data.get('dob', 'N/A')
        sex = data.get('sex', 'N/A')
        notes = data.get('notes') or 'No diagnosis/medication notes available.'
        return (
            'Retrieved patient profile:\n'
            f'- Name: {full_name}\n'
            f'- Patient ID: {pid}\n'
            f'- DOB: {dob}\n'
            f'- Sex: {sex}\n'
            f'- Clinical notes: {notes}'
        )

    if tool_name == 'view_prescriptions':
        patient_name = data.get('patient_name', 'Unknown')
        prescriptions = data.get('prescriptions') or []
        if not prescriptions:
            return f'No prescriptions found for {patient_name}.'
        lines = [f'Prescriptions for {patient_name}:']
        for rx in prescriptions[:6]:
            lines.append(
                f"- {rx.get('drug_name', 'Unknown')} | {rx.get('dose', 'N/A')} | "
                f"{rx.get('frequency', 'N/A')} | {rx.get('status', 'N/A')}"
            )
        return '\n'.join(lines)

    # Generic safe fallback for other successful tools.
    return f"Latest tool result ({tool_name}):\n{json.dumps(data, indent=2)}"


def _fallback_response_from_tools(tool_calls_log: list[dict[str, Any]]) -> str:
    for call in reversed(tool_calls_log):
        if call.get('status') == 'success':
            rendered = _render_tool_result(call.get('name', ''), call.get('result') or {})
            if rendered:
                return rendered
    return 'Tool iteration limit reached before final assistant response.'


class AgentController:
    def __init__(self, db: Session):
        self.db = db
        self.repo = Repository(db)
        self.session_manager = SessionManager(db)
        self.llm = LLMClient()
        self.retriever = Retriever()
        self.tool_registry = ToolRegistry(db)
        self.tool_executor = ToolExecutor(self.tool_registry)
        self.telemetry = TelemetryLogger(db)

    async def handle_chat(
        self,
        trace_id: str,
        session_id: str | None,
        message: str,
        patient_id: str | None = None,
        role: str = 'Doctor',
        metadata: dict[str, Any] | None = None,
        guardrails_enabled: bool = True,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        metadata = metadata or {}
        guardrail_log: list[dict[str, Any]] = []
        guardrails_enabled = guardrails_enabled and settings.ENABLE_GUARDRAILS

        # ── Input guardrails (only when enabled) ─────────────────────────────
        if guardrails_enabled:
            input_check = Guardrails.check_input(message, role)
            llm_input_check = await LLMGuardrails.check_input(message)

            regex_input_violations = _tag_violations(input_check.violations, source='regex')
            llm_input_violations = _tag_violations(llm_input_check.violations, source='llm')
            all_input_violations = regex_input_violations + llm_input_violations
            input_blocked = _should_block_balanced(regex_input_violations, llm_input_violations)

            merged_input = {
                'passed': not input_blocked,
                'violations': all_input_violations,
                'models_used': [
                    settings.GUARDRAIL_PROMPT_GUARD_MODEL,
                    settings.GUARDRAIL_SAFEGUARD_MODEL,
                ] if settings.ENABLE_LLM_GUARDRAILS else [],
            }

            if input_blocked:
                self.telemetry.log(trace_id, 'guardrail_block', {'stage': 'input', 'violations': all_input_violations})
                latency_ms = int((time.perf_counter() - start) * 1000)
                return {
                    'session_id': session_id,
                    'trace_id': trace_id,
                    'latency_ms': latency_ms,
                    'response': 'Your message was blocked by safety guardrails.',
                    'tool_calls': [],
                    'guardrails': {
                        'enabled': True,
                        'input': merged_input,
                        'output': None,
                        'tool': [],
                        'models_used': merged_input['models_used'],
                    },
                }

        # ── Session — new session picks up the correct system prompt ──────────
        # When guardrails are toggled, the frontend resets session_id to None,
        # so a fresh session is always created with the right prompt.
        session_id, _was_expired = self.session_manager.get_or_create_session(
            session_id=session_id,
            patient_id=patient_id,
            role=role,
            metadata=metadata,
            guardrails_enabled=guardrails_enabled,
        )

        if patient_id:
            sess = self.repo.get_session(session_id)
            if sess and sess.patient_id != patient_id:
                sess.patient_id = patient_id
                self.db.add(sess)
                self.db.commit()

        self.session_manager.append_user_message(session_id, message)
        self.telemetry.log(trace_id, 'user_input', {'session_id': session_id, 'message': message, 'role': role, 'metadata': metadata})

        if settings.ENABLE_RAG:
            rag_results = self.retriever.retrieve(message)
            rag_text = self.retriever.format_as_tool_message(rag_results)
            self.session_manager.append_system_message(session_id, rag_text)
            self.telemetry.log(trace_id, 'rag_retrieval', {'results_count': len(rag_results)})

        tool_calls_log: list[dict[str, Any]] = []

        for _ in range(settings.MAX_TOOL_ITERATIONS):
            context = self.session_manager.get_context(session_id)

            # ── Tool schema exposure ──────────────────────────────────────────
            # Guardrails ON  → only role-allowed schemas sent to LLM
            # Guardrails OFF → all schemas sent (simulates unprotected deployment)
            if settings.ENABLE_TOOLS:
                tool_schemas = (
                    self.tool_registry.schemas(role=role)
                    if guardrails_enabled
                    else self.tool_registry.schemas()
                )
            else:
                tool_schemas = None

            # When guardrails are OFF and no tools have been called yet, force the
            # model to invoke a tool rather than responding with plain text.
            # This ensures attack scenarios actually execute rather than being
            # described. After the first tool result is in context, fall back to
            # 'auto' so the model can produce a final text summary.
            unguarded_force = not guardrails_enabled and not tool_calls_log
            llm_response = await self.llm.generate(
                messages=context,
                tools=tool_schemas,
                tool_choice='required' if unguarded_force else None,
            )
            self.telemetry.log(
                trace_id,
                'llm_response',
                {'model': llm_response.get('model'), 'has_tool_calls': bool(llm_response.get('tool_calls'))},
            )

            tool_calls = llm_response.get('tool_calls') or []
            if not tool_calls:
                text = llm_response.get('text', '').strip() or 'No response generated.'

                output_check = None
                llm_output_check = None
                output_models: list[str] = []
                all_output_violations: list[dict[str, Any]] = []
                output_blocked = False

                if guardrails_enabled:
                    output_check = Guardrails.check_output(text, role)
                    llm_output_check = await LLMGuardrails.check_output(text)

                    regex_output_violations = _tag_violations(output_check.violations or [], source='regex')
                    llm_output_violations = _tag_violations(llm_output_check.violations or [], source='llm')
                    all_output_violations = regex_output_violations + llm_output_violations
                    output_blocked = _should_block_balanced(regex_output_violations, llm_output_violations)
                    output_models = [settings.GUARDRAIL_SAFEGUARD_MODEL] if settings.ENABLE_LLM_GUARDRAILS else []

                    if output_blocked:
                        self.telemetry.log(trace_id, 'guardrail_block', {'stage': 'output', 'violations': all_output_violations})
                        text = 'The response was filtered by safety guardrails. Please rephrase your request.'

                merged_output = None
                if output_check or llm_output_check:
                    merged_output = {
                        'passed': not output_blocked,
                        'violations': all_output_violations,
                        'models_used': output_models,
                    }

                self.session_manager.append_assistant_message(session_id, text)
                latency_ms = int((time.perf_counter() - start) * 1000)

                all_models = list(set(
                    ([settings.GUARDRAIL_PROMPT_GUARD_MODEL, settings.GUARDRAIL_SAFEGUARD_MODEL] if settings.ENABLE_LLM_GUARDRAILS else [])
                ))

                return {
                    'session_id': session_id,
                    'trace_id': trace_id,
                    'latency_ms': latency_ms,
                    'response': text,
                    'tool_calls': tool_calls_log,
                    'guardrails': {
                        'enabled': guardrails_enabled,
                        'input': None,
                        'output': merged_output,
                        'tool': guardrail_log if guardrail_log else [],
                        'models_used': all_models,
                    },
                }

            self.session_manager.append_assistant_message(
                session_id,
                llm_response.get('text', '') or '',
                tool_calls=llm_response.get('tool_calls') or None,
            )

            for call in tool_calls:
                fn = (call.get('function') or {})
                tool_name = fn.get('name', '')
                raw_args = fn.get('arguments') or '{}'
                tool_call_id = call.get('id')
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}

                # ── Role enforcement ──────────────────────────────────────────
                # Guardrails ON  → is_allowed() blocks unauthorized tool calls
                # Guardrails OFF → no role enforcement; any tool can execute
                if guardrails_enabled and not self.tool_registry.is_allowed(tool_name, role):
                    result = {
                        'ok': False,
                        'data': None,
                        'error': f'Access denied: the {role} role does not have permission to use {tool_name}.',
                        'user_safe': True,
                    }
                    guardrail_log.append({'tool': tool_name, 'type': 'unauthorized_tool', 'blocked': True})
                else:
                    if guardrails_enabled:
                        sess_obj = self.repo.get_session(session_id)
                        tc_check = Guardrails.check_tool_call(
                            tool_name=tool_name,
                            arguments=args,
                            role=role,
                            session_patient_id=patient_id or (sess_obj.patient_id if sess_obj else None),
                        )
                        if tc_check.blocked:
                            result = {
                                'ok': False,
                                'data': None,
                                'error': tc_check.violations[0]['message'],
                                'user_safe': True,
                            }
                            guardrail_log.append({'tool': tool_name, 'violations': tc_check.violations, 'blocked': True})
                            self.telemetry.log(trace_id, 'guardrail_block', {'stage': 'tool_call', 'tool': tool_name, 'violations': tc_check.violations})
                            status = 'error'
                            tool_calls_log.append({'name': tool_name, 'arguments': args, 'status': status, 'result': result})
                            tool_payload = {'tool_name': tool_name, 'arguments': args, 'result': result}
                            tool_context = json.dumps({'error': result.get('error', 'Blocked by guardrails')})
                            self.session_manager.append_tool_message(session_id=session_id, name=tool_name, content=tool_context, tool_call_id=tool_call_id)
                            self.telemetry.log(trace_id, 'tool_call', tool_payload)
                            continue

                    result = await self.tool_executor.execute(tool_name=tool_name, arguments=args)

                status = 'success' if result.get('ok') else 'error'
                tool_calls_log.append({
                    'name': tool_name,
                    'arguments': args,
                    'status': status,
                    'result': result,
                })

                tool_payload = {'tool_name': tool_name, 'arguments': args, 'result': result}
                # Send only the result data to LLM context — not the full payload with echoed
                # arguments, which confuses the model into thinking the action hasn't completed.
                if result.get('ok'):
                    tool_context = json.dumps(result.get('data') or {'status': 'success'})
                else:
                    tool_context = json.dumps({'error': result.get('error', 'Tool failed')})
                self.session_manager.append_tool_message(
                    session_id=session_id,
                    name=tool_name,
                    content=tool_context,
                    tool_call_id=tool_call_id,
                )
                self.telemetry.log(trace_id, 'tool_call', tool_payload)

        fallback_text = _fallback_response_from_tools(tool_calls_log)
        self.session_manager.append_assistant_message(session_id, fallback_text)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            'session_id': session_id,
            'trace_id': trace_id,
            'latency_ms': latency_ms,
            'response': fallback_text,
            'tool_calls': tool_calls_log,
            'guardrails': {
                'enabled': guardrails_enabled,
                'input': None,
                'output': None,
                'tool': guardrail_log if guardrail_log else [],
                'models_used': [settings.GUARDRAIL_PROMPT_GUARD_MODEL, settings.GUARDRAIL_SAFEGUARD_MODEL] if (guardrails_enabled and settings.ENABLE_LLM_GUARDRAILS) else [],
            },
        }
