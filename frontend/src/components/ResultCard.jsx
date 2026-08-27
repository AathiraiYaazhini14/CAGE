import React, { useState } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  ChevronDown, 
  ChevronUp, 
  FileCode, 
  Tag, 
  Activity,
  AlertCircle
} from 'lucide-react';

export default function ResultCard({ result }) {
  const [isPatternsOpen, setIsPatternsOpen] = useState(true);

  if (!result) return null;

  const { flagged, score, attack_type, matched_patterns } = result;
  const percentage = Math.round(score * 100);

  return (
    <div className="w-full glass-panel rounded-2xl p-6 space-y-6 animate-slide-up border border-slate-800">
      {/* Header Verdict Badge & Attack Category Tag */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          {flagged ? (
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 font-bold text-sm shadow-inner">
              <ShieldAlert className="w-5 h-5 text-rose-400 animate-pulse" />
              <span>⚠ Injection Detected</span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold text-sm shadow-inner">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <span>✓ Clean Prompt</span>
            </div>
          )}

          {attack_type && attack_type !== 'none' && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-xs font-mono">
              <Tag className="w-3.5 h-3.5 text-cyan-400" />
              <span>{attack_type}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <Activity className="w-3.5 h-3.5 text-slate-500" />
          <span>Status: Verified</span>
        </div>
      </div>

      {/* Confidence Score Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-medium">
          <span className="text-slate-400 uppercase tracking-wider text-[11px]">
            Risk Confidence Score
          </span>
          <span className={`font-mono text-sm font-bold ${
            flagged ? 'text-rose-400' : 'text-emerald-400'
          }`}>
            {percentage}%
          </span>
        </div>

        <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden p-0.5 border border-slate-800">
          <div
            className={`h-full rounded-full transition-all duration-700 ease-out ${
              flagged
                ? 'bg-gradient-to-r from-amber-500 to-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.4)]'
                : 'bg-gradient-to-r from-teal-500 to-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.3)]'
            }`}
            style={{ width: `${Math.max(percentage, 5)}%` }}
          />
        </div>
      </div>

      {/* Matched Patterns Collapsible Section */}
      {matched_patterns && matched_patterns.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 overflow-hidden">
          <button
            type="button"
            onClick={() => setIsPatternsOpen(!isPatternsOpen)}
            className="w-full px-4 py-3 flex items-center justify-between bg-slate-900/50 hover:bg-slate-800/40 text-xs font-semibold uppercase tracking-wider text-slate-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-cyan-400" />
              <span>Matched Attack Signatures ({matched_patterns.length})</span>
            </div>
            {isPatternsOpen ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>

          {isPatternsOpen && (
            <div className="p-4 space-y-3 divide-y divide-slate-800/60 font-mono text-xs">
              {matched_patterns.map((item, index) => (
                <div key={index} className={index > 0 ? "pt-3" : ""}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="px-2 py-0.5 rounded bg-rose-950/70 border border-rose-800/60 text-rose-300 text-[11px]">
                      {item.category}
                    </span>
                    <span className="text-slate-500 text-[11px]">
                      weight: +{item.weight}
                    </span>
                  </div>

                  <div className="text-slate-300 space-y-1">
                    <div className="text-slate-400 text-[11px] flex items-center gap-1">
                      <AlertCircle className="w-3 h-3 text-amber-400 shrink-0" />
                      <span>Matched string:</span>
                      <code className="text-rose-300 bg-rose-950/40 px-1.5 py-0.5 rounded font-bold">
                        "{item.matched_text}"
                      </code>
                    </div>
                    <div className="text-slate-500 text-[11px]">
                      Regex pattern: <span className="text-slate-400">{item.pattern}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
