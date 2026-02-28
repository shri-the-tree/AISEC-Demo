import { useState } from 'react'

const TOOL_ICONS = {
  get_patient_record:     '👤',
  check_drug_interaction: '💊',
  book_appointment:       '📅',
  issue_prescription:     '📋',
  view_prescriptions:     '📊',
  update_patient_record:  '✏️',
}

export default function RightPanel({ lastToolCall, allToolCalls }) {
  const [activeTab, setActiveTab] = useState('last')

  return (
    <aside className="w-80 flex-shrink-0 bg-slate-900 border-l border-slate-800 flex flex-col overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-slate-800 flex-shrink-0">
        <TabButton active={activeTab === 'last'} onClick={() => setActiveTab('last')}>
          Last Tool
        </TabButton>
        <TabButton active={activeTab === 'log'} onClick={() => setActiveTab('log')}>
          Tool Log
          {allToolCalls.length > 0 && (
            <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-slate-700 text-slate-300 text-[10px] font-medium">
              {allToolCalls.length}
            </span>
          )}
        </TabButton>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'last' && <LastToolView toolCall={lastToolCall} />}
        {activeTab === 'log' && <ToolLogView toolCalls={allToolCalls} />}
      </div>
    </aside>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-1 px-4 py-3 text-xs font-medium transition-colors border-b-2 ${
        active
          ? 'border-blue-500 text-blue-400 bg-slate-800/50'
          : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-800/30'
      }`}
    >
      {children}
    </button>
  )
}

function LastToolView({ toolCall }) {
  if (!toolCall) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center px-6">
        <div className="text-3xl mb-3">🔧</div>
        <p className="text-slate-500 text-xs leading-relaxed">
          No tool has been called yet. Tool executions will appear here.
        </p>
      </div>
    )
  }

  const success = toolCall.status === 'success'
  const icon = TOOL_ICONS[toolCall.name] || '🔧'

  return (
    <div className="p-4 space-y-4">
      {/* Tool name + status */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-lg">{icon}</span>
          <span className="font-mono text-sm font-semibold text-white">{toolCall.name}</span>
          <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium ${
            success
              ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-800/50'
              : 'bg-red-900/50 text-red-300 border border-red-800/50'
          }`}>
            {success ? '✓ success' : '✗ error'}
          </span>
        </div>
        {toolCall.timestamp && (
          <div className="text-[10px] text-slate-500 font-mono">
            {new Date(toolCall.timestamp).toLocaleTimeString()}
            {toolCall.traceId && ` · ${toolCall.traceId.slice(0, 8)}`}
          </div>
        )}
      </div>

      {/* Arguments */}
      <div>
        <SectionLabel>Arguments</SectionLabel>
        {Object.keys(toolCall.arguments || {}).length === 0 ? (
          <div className="text-slate-500 text-xs italic">No arguments</div>
        ) : (
          <div className="space-y-1">
            {Object.entries(toolCall.arguments || {}).map(([k, v]) => (
              <div key={k} className="bg-slate-800/60 rounded-md px-3 py-2">
                <div className="text-[10px] text-slate-500 uppercase mb-0.5">{k}</div>
                <div className="text-xs text-slate-200 font-mono break-all">{String(v)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Result */}
      <div>
        <SectionLabel>Result</SectionLabel>
        {toolCall.result?.error ? (
          <div className="bg-red-900/20 border border-red-800/40 rounded-md px-3 py-2 text-xs text-red-300 font-mono">
            {toolCall.result.error}
          </div>
        ) : toolCall.result?.data ? (
          <pre className="bg-slate-800/60 rounded-md px-3 py-2 text-[10px] text-slate-300 font-mono whitespace-pre-wrap overflow-auto max-h-64">
            {JSON.stringify(toolCall.result.data, null, 2)}
          </pre>
        ) : (
          <div className="text-slate-500 text-xs italic">No data returned</div>
        )}
      </div>
    </div>
  )
}

function ToolLogView({ toolCalls }) {
  if (toolCalls.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center px-6">
        <div className="text-3xl mb-3">📜</div>
        <p className="text-slate-500 text-xs leading-relaxed">
          Tool call log is empty. Calls made during this session will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="p-3 space-y-2">
      {[...toolCalls].reverse().map((tc, i) => {
        const success = tc.status === 'success'
        const icon = TOOL_ICONS[tc.name] || '🔧'
        return (
          <div
            key={i}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2.5"
          >
            <div className="flex items-center gap-2">
              <span>{icon}</span>
              <span className="font-mono text-xs text-slate-200 flex-1 truncate">{tc.name}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                success ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {success ? '✓' : '✗'}
              </span>
            </div>
            {Object.keys(tc.arguments || {}).length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {Object.entries(tc.arguments).map(([k, v]) => (
                  <span key={k} className="text-[10px] font-mono bg-slate-700/60 text-slate-400 rounded px-1.5 py-0.5 truncate max-w-[120px]">
                    {k}: {String(v).slice(0, 20)}{String(v).length > 20 ? '…' : ''}
                  </span>
                ))}
              </div>
            )}
            {tc.timestamp && (
              <div className="mt-1 text-[10px] text-slate-600 font-mono">
                {new Date(tc.timestamp).toLocaleTimeString()}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function SectionLabel({ children }) {
  return (
    <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-2">
      {children}
    </div>
  )
}
