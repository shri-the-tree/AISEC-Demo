import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import RightPanel from './components/RightPanel'
import { getPatients, sendMessage } from './api'

const ROLES = ['Doctor', 'Nurse', 'Admin']

export default function App() {
  const [role, setRole] = useState('Doctor')
  const [sessionId, setSessionId] = useState(null)
  const [patientId, setPatientId] = useState('')
  const [turns, setTurns] = useState([])
  const [patients, setPatients] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [backendOnline, setBackendOnline] = useState(null)
  const [guardrailsOn, setGuardrailsOn] = useState(true)

  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(() => setPatients([]))
  }, [])

  useEffect(() => {
    fetch('http://127.0.0.1:8000/health')
      .then(r => r.ok ? setBackendOnline(true) : setBackendOnline(false))
      .catch(() => setBackendOnline(false))
  }, [])

  const handleRoleChange = useCallback((newRole) => {
    setRole(newRole)
    setSessionId(null)
    setTurns([])
  }, [])

  // Toggle guardrails — resets session so next message gets the correct
  // system prompt (guarded vs unguarded), but keeps visual chat history.
  const handleGuardrailsToggle = useCallback(() => {
    setGuardrailsOn(g => !g)
    setSessionId(null)
  }, [])

  const handleSend = useCallback(async (message) => {
    if (!message.trim() || isLoading) return

    setIsLoading(true)

    const turnId = crypto.randomUUID()
    const optimisticTurn = {
      id: turnId,
      userMessage: message,
      toolCalls: [],
      response: null,
      latencyMs: null,
      traceId: null,
      timestamp: new Date(),
      loading: true,
    }
    setTurns(prev => [...prev, optimisticTurn])

    try {
      const data = await sendMessage(sessionId, message, role, patientId || null, guardrailsOn)

      setTurns(prev => prev.map(t =>
        t.id === turnId
          ? {
              ...t,
              toolCalls: data.tool_calls || [],
              response: data.response,
              latencyMs: data.latency_ms,
              traceId: data.trace_id,
              guardrails: data.guardrails || null,
              loading: false,
            }
          : t
      ))
      setSessionId(data.session_id)
    } catch (err) {
      setTurns(prev => prev.map(t =>
        t.id === turnId
          ? { ...t, response: `Error: ${err.message}`, loading: false, isError: true }
          : t
      ))
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, sessionId, role, patientId, guardrailsOn])

  const allToolCalls = turns.flatMap(t =>
    t.toolCalls.map(tc => ({ ...tc, traceId: t.traceId, timestamp: t.timestamp }))
  )
  const lastToolCall = allToolCalls.length > 0 ? allToolCalls[allToolCalls.length - 1] : null

  return (
    <div className={`flex flex-col h-screen bg-slate-950 text-white font-sans transition-all duration-500 ${
      !guardrailsOn ? 'ring-2 ring-inset ring-red-500/50' : ''
    }`}>

      {/* Header */}
      <header className={`flex items-center justify-between px-5 h-12 border-b flex-shrink-0 transition-colors duration-500 ${
        guardrailsOn ? 'bg-slate-900 border-slate-800' : 'bg-red-950/40 border-red-800/60'
      }`}>
        <div className="flex items-center gap-3">
          <span className="text-white font-semibold tracking-tight text-base">ClinicalCopilot</span>

          {/* Pulsing UNPROTECTED badge — appears only when guardrails OFF */}
          {!guardrailsOn && (
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-red-500/20 border border-red-500/50 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
              <span className="text-[11px] font-bold text-red-300 uppercase tracking-widest">Unprotected</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${backendOnline === true ? 'bg-emerald-400' : backendOnline === false ? 'bg-red-500' : 'bg-slate-500'}`} />
          <span className="text-xs text-slate-400">
            {backendOnline === true ? 'API online' : backendOnline === false ? 'API offline' : 'checking...'}
          </span>
          <RoleBadge role={role} unsafe={!guardrailsOn} />
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          role={role}
          roles={ROLES}
          onRoleChange={handleRoleChange}
          patientId={patientId}
          onPatientIdChange={setPatientId}
          sessionId={sessionId}
          patients={patients}
          guardrailsOn={guardrailsOn}
          onGuardrailsToggle={handleGuardrailsToggle}
        />
        <ChatPanel
          turns={turns}
          isLoading={isLoading}
          onSend={handleSend}
          role={role}
          guardrailsOn={guardrailsOn}
        />
        <RightPanel
          lastToolCall={lastToolCall}
          allToolCalls={allToolCalls}
        />
      </div>
    </div>
  )
}

function RoleBadge({ role, unsafe }) {
  const safeColors = {
    Doctor:  'bg-blue-500/20 text-blue-300 border border-blue-500/40',
    Nurse:   'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
    Admin:   'bg-amber-500/20 text-amber-300 border border-amber-500/40',
  }
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors duration-300 ${
      unsafe ? 'bg-red-500/20 text-red-300 border border-red-500/50' : (safeColors[role] || safeColors.Doctor)
    }`}>
      {role}
    </span>
  )
}
