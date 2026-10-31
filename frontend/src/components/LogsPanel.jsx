import React, { useState, useEffect } from 'react';
import { 
  Database, 
  ChevronDown, 
  ChevronUp, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  Clock,
  Layers
} from 'lucide-react';

export default function LogsPanel() {
  const [logs, setLogs] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/logs');
      if (!response.ok) {
        throw new Error(`Error status: ${response.status}`);
      }
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
      setError('Unable to fetch audit logs from backend.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  const renderTierBadge = (tier, action) => {
    const activeTier = tier || (action === 'blocked' ? 'block' : (action === 'isolated' ? 'isolate' : 'allow'));
    switch (activeTier) {
      case 'block':
        return <span className="px-2 py-0.5 rounded bg-rose-950/80 border border-rose-800 text-rose-300 font-bold text-[10px]">BLOCK</span>;
      case 'isolate':
        return <span className="px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-bold text-[10px]">ISOLATE</span>;
      case 'allow':
      default:
        return <span className="px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-bold text-[10px]">ALLOW</span>;
    }
  };

  const renderActionBadge = (action) => {
    switch (action) {
      case 'blocked':
        return <span className="text-rose-400 font-bold">blocked</span>;
      case 'isolated':
        return <span className="text-amber-400 font-bold">isolated</span>;
      case 'allow':
      default:
        return <span className="text-emerald-400">allow</span>;
    }
  };

  return (
    <div className="w-full glass-panel rounded-2xl border border-slate-800 overflow-hidden">
      <button
        type="button"
        id="logs-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between bg-slate-900/60 hover:bg-slate-800/40 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
          <Database className="w-4 h-4 text-cyan-400" />
          <span>Security Audit Logs</span>
          {logs.length > 0 && (
            <span className="ml-2 px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 text-[10px] font-mono">
              {logs.length} records
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {isOpen && (
            <button
              type="button"
              id="logs-refresh-btn"
              onClick={(e) => {
                e.stopPropagation();
                fetchLogs();
              }}
              disabled={isLoading}
              className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition-colors cursor-pointer"
              title="Refresh logs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          )}

          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="p-4 border-t border-slate-800/80 space-y-3 font-mono text-xs">
          {error && (
            <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {logs.length === 0 && !isLoading && !error && (
            <p className="text-slate-500 text-center py-6 text-xs font-sans">
              No audit logs recorded yet. Run a prompt inspection above to populate logs.
            </p>
          )}

          {logs.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] text-slate-400 uppercase tracking-wider">
                    <th className="pb-2 font-medium">Time</th>
                    <th className="pb-2 font-medium">Source</th>
                    <th className="pb-2 font-medium">Tier</th>
                    <th className="pb-2 font-medium">Payload Preview</th>
                    <th className="pb-2 font-medium">Score</th>
                    <th className="pb-2 font-medium">Action</th>
                    <th className="pb-2 font-medium">Val</th>
                    <th className="pb-2 font-medium">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-[11px]">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-900/40">
                      <td className="py-2.5 text-slate-400 whitespace-nowrap text-[10px]">
                        {log.timestamp.split(' ')[1] || log.timestamp}
                      </td>
                      <td className="py-2.5 text-slate-400 text-[10px]">
                        <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400">
                          {log.source_type || 'user_input'}
                        </span>
                      </td>
                      <td className="py-2.5">
                        {renderTierBadge(log.tier, log.defense_action)}
                      </td>
                      <td className="py-2.5 text-slate-300 max-w-[200px] truncate" title={log.input_text}>
                        {log.input_text}
                      </td>
                      <td className="py-2.5 font-bold">
                        <span className={log.final_score >= 0.90 ? 'text-rose-400' : 'text-emerald-400'}>
                          {log.final_score !== undefined ? Number(log.final_score).toFixed(4) : '-'}
                        </span>
                      </td>
                      <td className="py-2.5">
                        {renderActionBadge(log.defense_action)}
                      </td>
                      <td className="py-2.5">
                        {log.output_validation_passed === true && (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                        {log.output_validation_passed === false && (
                          <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        )}
                        {log.output_validation_passed === null && (
                          <span className="text-slate-600">-</span>
                        )}
                      </td>
                      <td className="py-2.5 text-slate-400 whitespace-nowrap text-[10px]">
                        {log.latency_ms}ms
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
