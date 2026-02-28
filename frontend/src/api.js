const BASE = 'http://127.0.0.1:8000'

export async function getHealth() {
  const res = await fetch(`${BASE}/health`)
  return res.json()
}

export async function getPatients() {
  const res = await fetch(`${BASE}/patients`)
  if (!res.ok) throw new Error('Failed to load patients')
  return res.json()
}

export async function createSession(role, patientId = null) {
  const res = await fetch(`${BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, patient_id: patientId || null }),
  })
  if (!res.ok) throw new Error('Failed to create session')
  return res.json()
}

export async function sendMessage(sessionId, message, role, patientId = null, guardrailsEnabled = true) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      role,
      patient_id: patientId || null,
      guardrails_enabled: guardrailsEnabled,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Chat request failed')
  }
  return res.json()
}
