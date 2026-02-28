import { useState, useCallback, useEffect } from 'react'

const MIN_WIDTH = 200
const MAX_WIDTH = 480

const ALL_TOOLS = [
  {
    key: 'get_patient_record',
    label: 'Patient Records',
    icon: '👤',
    description: 'Retrieves full patient details — name, DOB, sex, phone, and clinical notes including diagnosis and current medications.',
  },
  {
    key: 'view_prescriptions',
    label: 'View Prescriptions',
    icon: '📊',
    description: 'View current prescriptions and medication timings for a patient, including drug name, dose, route, and frequency.',
  },
  {
    key: 'check_drug_interaction',
    label: 'Drug Interactions',
    icon: '💊',
    description: 'Checks two drug names against the interactions database and returns any known adverse combinations or contraindications.',
  },
  {
    key: 'book_appointment',
    label: 'Book Appointment',
    icon: '📅',
    description: 'Creates a scheduled appointment entry for a patient, including department, clinician name, and datetime.',
  },
  {
    key: 'issue_prescription',
    label: 'Issue Prescription',
    icon: '📋',
    description: 'Writes a new draft prescription for a patient — specifying drug name, dose, route, and frequency. Saved as a draft record.',
  },
]

const ROLE_TOOLS = {
  Doctor: ['get_patient_record', 'view_prescriptions', 'check_drug_interaction', 'book_appointment', 'issue_prescription'],
  Nurse: ['view_prescriptions', 'check_drug_interaction', 'book_appointment'],
  Admin: ['get_patient_record', 'view_prescriptions'],
}

const ROLE_COLORS = {
  Doctor: 'border-blue-500 bg-blue-500/10 text-blue-300',
  Nurse: 'border-emerald-500 bg-emerald-500/10 text-emerald-300',
  Admin: 'border-amber-500 bg-amber-500/10 text-amber-300',
}

export default function Sidebar({ role, roles, onRoleChange, patientId, onPatientIdChange, sessionId, patients, guardrailsOn, onGuardrailsToggle }) {
  const allowedTools = ROLE_TOOLS[role] || ROLE_TOOLS.Doctor
  const [width, setWidth] = useState(256)
  const [dragging, setDragging] = useState(false)
  const [hoveredTool, setHoveredTool] = useState(null)

  const onMouseDown = useCallback((e) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  useEffect(() => {
    if (!dragging) return
    const onMouseMove = (e) => {
      setWidth(w => Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX)))
    }
    const onMouseUp = () => setDragging(false)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [dragging])

  return (
    <aside
      style={{ width }}
      className="relative flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col overflow-visible select-none"
    >
    {/* Drag handle */}
    <div
      onMouseDown={onMouseDown}
      className={`absolute right-0 top-0 h-full w-1 z-10 cursor-col-resize group/handle transition-colors ${dragging ? 'bg-blue-500' : 'hover:bg-blue-500/60'}`}
    >
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col gap-1 opacity-0 group-hover/handle:opacity-100 transition-opacity">
        {[0,1,2].map(i => <div key={i} className="w-0.5 h-0.5 rounded-full bg-slate-400" />)}
      </div>
    </div>
    <div className="flex flex-col flex-1 overflow-y-auto">

      {/* Role Selector */}
      <div className="p-4 border-b border-slate-800">
        <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
          Active Role
        </label>
        <select
          value={role}
          onChange={e => onRoleChange(e.target.value)}
          className="w-full bg-slate-800 text-white text-sm rounded-md px-3 py-2 border border-slate-700 focus:outline-none focus:border-slate-500 cursor-pointer"
        >
          {roles.map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <p className="mt-2 text-xs text-slate-500">Changing role resets the session.</p>
      </div>

      {/* Patient ID */}
      <div className="p-4 border-b border-slate-800">
        <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
          Patient ID
        </label>
        <input
          type="text"
          value={patientId}
          onChange={e => onPatientIdChange(e.target.value)}
          placeholder="Paste patient UUID..."
          className="w-full bg-slate-800 text-white text-xs rounded-md px-3 py-2 border border-slate-700 focus:outline-none focus:border-slate-500 placeholder-slate-600 font-mono"
        />
      </div>

      {/* Patient List */}
      {patients.length > 0 && (
        <div className="p-4 border-b border-slate-800">
          <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
            Demo Patients
          </label>
          <div className="space-y-1.5">
            {patients.map(p => (
              <button
                key={p.id}
                onClick={() => onPatientIdChange(p.id)}
                className={`w-full text-left rounded-md px-2.5 py-2 text-xs transition-colors ${
                  patientId === p.id
                    ? 'bg-slate-600 text-white'
                    : 'bg-slate-800/60 text-slate-300 hover:bg-slate-700/60'
                }`}
              >
                <div className="font-medium truncate">{p.full_name}</div>
                <div className="text-slate-500 font-mono truncate text-[10px] mt-0.5">{p.id.slice(0, 18)}…</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Session Info */}
      <div className="p-4 border-b border-slate-800">
        <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
          Session
        </label>
        {sessionId ? (
          <div className="font-mono text-[10px] text-slate-400 break-all leading-relaxed">
            {sessionId}
          </div>
        ) : (
          <div className="text-xs text-slate-600 italic">No active session — send a message to start.</div>
        )}
      </div>

      {/* Guardrails Toggle */}
      <div className="p-4 border-b border-slate-800">
        <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
          AI Safety Guardrails
        </label>
        <button
          onClick={onGuardrailsToggle}
          className={`w-full flex items-center justify-between rounded-lg px-3 py-2.5 text-xs font-medium transition-all duration-200 border ${
            guardrailsOn
              ? 'bg-emerald-900/30 border-emerald-700/50 text-emerald-300 hover:bg-emerald-900/50'
              : 'bg-red-900/30 border-red-700/50 text-red-300 hover:bg-red-900/50'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm">{guardrailsOn ? '🛡️' : '⚠️'}</span>
            <span>{guardrailsOn ? 'Guardrails Active' : 'Guardrails Off'}</span>
          </div>
          {/* Toggle switch */}
          <div className={`relative w-9 h-5 rounded-full transition-colors duration-200 ${guardrailsOn ? 'bg-emerald-600' : 'bg-slate-600'}`}>
            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${guardrailsOn ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </div>
        </button>
        <p className="mt-2 text-[10px] text-slate-500 leading-relaxed">
          {guardrailsOn
            ? 'Input validation, prompt-injection detection, role enforcement, and output filtering are active.'
            : 'Guardrails disabled — all safety checks, role enforcement, and tool restrictions are bypassed.'}
        </p>

        {/* Open-source guardrail models — only shown when active */}
        {guardrailsOn && (
          <div className="mt-3 space-y-1.5">
            <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">Open-Source Safety Models</div>
            {[
              { id: 'meta-llama/llama-prompt-guard-2-86m', label: 'Llama Prompt Guard 2', org: 'Meta', role: 'Prompt injection & jailbreak detection', icon: '🦙' },
              { id: 'openai/gpt-oss-safeguard-20b', label: 'GPT-OSS-Safeguard', org: 'OpenAI', role: 'Policy-following safety classifier', icon: '🔬' },
            ].map(m => (
              <div key={m.id} className="flex items-start gap-2 rounded-md bg-slate-800/60 border border-slate-700/40 px-2.5 py-2">
                <span className="text-sm mt-0.5">{m.icon}</span>
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold text-slate-200 leading-tight">{m.label}</div>
                  <div className="text-[10px] text-slate-500 font-mono truncate">{m.id}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{m.role}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Role Permissions */}
      <div className="p-4 flex-1">
        <div className="flex items-center gap-2 mb-3">
          <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Role Permissions
          </label>
        </div>

        <div className={`rounded-md border px-3 py-2 mb-3 text-xs font-medium ${ROLE_COLORS[role]}`}>
          {role}
        </div>

        <div onMouseLeave={() => setHoveredTool(null)}>
          <div className="space-y-2">
            {ALL_TOOLS.map(tool => {
              const allowed = allowedTools.includes(tool.key)
              const isHovered = hoveredTool?.key === tool.key
              return (
                <div
                  key={tool.key}
                  onMouseEnter={() => setHoveredTool(tool)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs cursor-default transition-colors ${
                    allowed
                      ? isHovered
                        ? 'bg-emerald-900/40 border border-emerald-700/60 text-emerald-200'
                        : 'bg-emerald-900/20 border border-emerald-800/40 text-emerald-300'
                      : isHovered
                        ? 'bg-slate-700/50 border border-slate-600/50 text-slate-400'
                        : 'bg-slate-800/40 border border-slate-700/40 text-slate-500'
                  }`}
                >
                  <span className="text-sm">{tool.icon}</span>
                  <span className="flex-1">{tool.label}</span>
                  {allowed
                    ? <span className="text-emerald-400 font-bold">✓</span>
                    : <span className="text-slate-600">✗</span>
                  }
                </div>
              )
            })}
          </div>

          <div className={`mt-3 overflow-hidden transition-all duration-200 ${hoveredTool ? 'max-h-40 opacity-100' : 'max-h-0 opacity-0'}`}>
            {hoveredTool && (
              <div className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2.5">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="text-sm">{hoveredTool.icon}</span>
                  <span className="text-xs font-semibold text-white">{hoveredTool.label}</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">{hoveredTool.description}</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
    </aside>
  )
}
