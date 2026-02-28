"""
Guardrails engine for ClinicalCopilot (unified).

Roles: Doctor, Nurse, Admin.
Patient-specific checks removed. Nurse prescribing block retained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailResult:
    passed: bool
    violations: list[dict[str, str]] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return not self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            'passed': self.passed,
            'violations': self.violations,
        }


_PROMPT_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r'ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts)', 'Prompt injection: ignore previous instructions'),
    (r'disregard\s+(your|all|the)\s+(rules|guidelines|instructions|system)', 'Prompt injection: disregard rules'),
    (r'system\s*:\s*', 'Prompt injection: raw system-role injection'),
    (r'<\s*system\s*>', 'Prompt injection: XML system tag injection'),
    (r'\[\s*INST\s*\]', 'Prompt injection: instruction tag injection'),
    (r'override\s+(safety|guardrail|security|restriction)', 'Prompt injection: override safety'),
    (r'jailbreak', 'Prompt injection: jailbreak keyword'),
    (r'dan\s+mode', 'Prompt injection: DAN mode attempt'),
    (r'developer\s+mode', 'Prompt injection: developer mode attempt'),
    (r'system\s+instruction', 'Prompt injection: system instruction override attempt'),
    (r'respond\s+as\s+if\s+you\s+(have\s+no|are\s+not)', 'Prompt injection: persona override attempt'),
    (r'new\s+rule\s*:', 'Prompt injection: rule injection attempt'),
]

_BULK_QUERY_PATTERNS: list[tuple[str, str]] = [
    (r'\ball\s+patients?\b', 'cross_patient_access: bulk patient query attempt'),
    (r'records?\s+for\s+all\b', 'cross_patient_access: bulk record request'),
    (r'(every|each)\s+patient\b', 'cross_patient_access: bulk patient enumeration'),
    # Catch 3+ of the known patient names appearing in the same message
    (r'(margaret|robert|sarah|james).{0,80}(margaret|robert|sarah|james).{0,80}(margaret|robert|sarah|james)', 'cross_patient_access: multiple patient names in single query'),
]

_PII_OUTPUT_PATTERNS: list[tuple[str, str]] = [
    (r'\b\d{3}-\d{2}-\d{4}\b', 'PII leak: SSN-like pattern detected'),
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'PII leak: email address detected in output'),
]


class Guardrails:
    """Stateless guardrail checker."""

    @staticmethod
    def check_input(message: str, role: str) -> GuardrailResult:
        """Validate user input before it reaches the LLM."""
        violations: list[dict[str, str]] = []
        lower = message.lower()

        for pattern, label in _PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, lower):
                violations.append({'type': 'prompt_injection', 'message': label})

        for pattern, label in _BULK_QUERY_PATTERNS:
            if re.search(pattern, lower, re.DOTALL):
                violations.append({'type': 'cross_patient_access', 'message': label})
                break  # one match is sufficient

        if len(message) > 8000:
            violations.append({
                'type': 'input_length',
                'message': f'Message too long ({len(message)} chars). Maximum is 8000 characters.',
            })

        # Nurses cannot prescribe — catch attempts at the input stage
        if role == 'Nurse':
            prescribe_patterns = [
                r'(prescribe|issue\s+prescription|write\s+(a\s+)?prescription)',
                r'(change|modify|update)\s+(the\s+)?prescription',
            ]
            for pattern in prescribe_patterns:
                if re.search(pattern, lower):
                    violations.append({
                        'type': 'role_violation',
                        'message': 'Nurses cannot issue or modify prescriptions. Please consult the attending doctor.',
                    })

        return GuardrailResult(passed=len(violations) == 0, violations=violations)

    @staticmethod
    def check_output(response: str, role: str) -> GuardrailResult:
        """Validate LLM output before it reaches the user."""
        violations: list[dict[str, str]] = []

        for pattern, label in _PII_OUTPUT_PATTERNS:
            if re.search(pattern, response):
                violations.append({'type': 'pii_leak', 'message': label})

        if len(response) > 14000:
            violations.append({
                'type': 'output_length',
                'message': 'Response exceeds safe length limit.',
            })

        return GuardrailResult(passed=len(violations) == 0, violations=violations)

    @staticmethod
    def check_tool_call(
        tool_name: str,
        arguments: dict[str, Any],
        role: str,
        session_patient_id: str | None = None,
    ) -> GuardrailResult:
        """Validate a tool invocation against role-based policies."""
        violations: list[dict[str, str]] = []

        # Nurses have no access to prescribing or full patient records
        if role == 'Nurse' and tool_name in ('issue_prescription', 'get_patient_record'):
            violations.append({
                'type': 'unauthorized_tool',
                'message': f'Nurses do not have permission to use {tool_name}. Contact the attending doctor.',
            })

        return GuardrailResult(passed=len(violations) == 0, violations=violations)
