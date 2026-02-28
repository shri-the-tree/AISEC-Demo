import { useState } from 'react'

const TOOL_ICONS = {
  get_patient_record: '👤',
  check_drug_interaction: '💊',
  book_appointment: '📅',
  issue_prescription: '📋',
}

export default function ToolCallCard({ toolCall }) {
  const [expanded, setExpanded] = useState(false)
  const icon = TOOL_ICONS[toolCall.name] || '🔧'
  const success = toolCall.status === 'success'

  const resultData = toolCall.result?.data
  const resultError = toolCall.result?.error

  return (
    <div className="my-2 mx-4 rounded-lg border border-amber-800/50 bg-amber-950/30 overflow-hidden text-xs">
      {/* Header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-amber-900/20 transition-colors text-left"
      >
        <span className="text-sm">{icon}</span>
        <span className="font-mono font-medium text-amber-300">{toolCall.name}</span>
        <span className={`ml-auto px-2 py-0.5 rounded-full font-medium text-[10px] ${
          success
            ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-800/50'
            : 'bg-red-900/50 text-red-300 border border-red-800/50'
        }`}>
          {success ? '✓ success' : '✗ error'}
        </span>
        <span className="text-slate-500 ml-1">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Args row (always visible) */}
      <div className="px-3 pb-2 flex flex-wrap gap-1">
        {Object.entries(toolCall.arguments || {}).map(([k, v]) => (
          <span key={k} className="inline-flex items-center gap-1 bg-slate-800/60 rounded px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
            <span className="text-slate-500">{k}:</span>
            <span className="text-slate-300 truncate max-w-[140px]">{String(v)}</span>
          </span>
        ))}
      </div>

      {/* Expanded result */}
      {expanded && (
        <div className="border-t border-amber-800/30 px-3 py-2 bg-slate-900/60">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Result</div>
          {resultError ? (
            <div className="text-red-400 font-mono text-[11px]">{resultError}</div>
          ) : resultData ? (
            <pre className="text-slate-300 font-mono text-[10px] whitespace-pre-wrap overflow-auto max-h-40">
              {JSON.stringify(resultData, null, 2)}
            </pre>
          ) : (
            <div className="text-slate-500 italic text-[11px]">No data returned</div>
          )}
        </div>
      )}
    </div>
  )
}
