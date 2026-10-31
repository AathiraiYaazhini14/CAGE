import React, { useState } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  ChevronDown, 
  ChevronUp, 
  FileCode, 
  Tag, 
  Activity,
  AlertCircle,
  Lock,
  Cpu,
  Bot,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Sliders,
  Crosshair,
  Layers,
  FileSearch
} from 'lucide-react';

export default function ResultCard({ result }) {
  const [isPatternsOpen, setIsPatternsOpen] = useState(true);
  const [isChunkOpen, setIsChunkOpen] = useState(true);

  if (!result) return null;

  const { 
    flagged, 
    final_score, 
    score, 
    heuristic_score = 0, 
    classifier_score = 0, 
    severity = 'none',
    attack_type, 
    matched_patterns = [],
    defense_action = 'allow',
    tier,
    triggered_chunk,
    source_type = 'user_input',
    input_text = '',
    llm_response,
    output_validation,
    latency_ms
  } = result;

  const totalScore = final_score !== undefined ? final_score : (score || 0);
  const percentage = Math.round(totalScore * 100);
  const heurPercentage = Math.round((heuristic_score || 0) * 100);
  const classPercentage = Math.round((classifier_score || 0) * 100);

  // Active tier calculation
  const activeTier = tier || (defense_action === 'blocked' ? 'block' : (defense_action === 'isolated' ? 'isolate' : 'allow'));

  // Tier Badge rendering
  const renderTierBadge = () => {
    switch (activeTier) {
      case 'block':
        return (
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-rose-500/20 border border-rose-500/50 text-rose-300 font-bold text-xs uppercase tracking-wider shadow-lg shadow-rose-950/40">
            <XCircle className="w-4 h-4 text-rose-400 animate-pulse" />
            <span>Tier: Block (&ge; 0.945)</span>
          </div>
        );
      case 'isolate':
        return (
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-amber-500/20 border border-amber-500/50 text-amber-300 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-950/40">
            <AlertTriangle className="w-4 h-4 text-amber-400 animate-bounce" />
            <span>Tier: Isolate (0.90 – 0.945)</span>
          </div>
        );
      case 'allow':
      default:
        return (
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 font-bold text-xs uppercase tracking-wider shadow-lg shadow-emerald-950/40">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Tier: Allow (&lt; 0.90)</span>
          </div>
        );
    }
  };

  // Defense Action Badge styling
  const renderDefenseBadge = () => {
    switch (defense_action) {
      case 'blocked':
        return (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 font-mono text-xs">
            <span>Action: blocked</span>
          </div>
        );
      case 'isolated':
        return (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-950/60 border border-amber-800/60 text-amber-300 font-mono text-xs">
            <span>Action: isolated</span>
          </div>
        );
      case 'allow':
      default:
        return (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 font-mono text-xs">
            <span>Action: allow</span>
          </div>
        );
    }
  };

  // Highlight triggered chunk inside input_text
  const renderHighlightedDocument = () => {
    if (!input_text) return null;
    if (!triggered_chunk || !triggered_chunk.trim()) {
      return (
        <div className="text-slate-300 text-xs font-mono whitespace-pre-wrap leading-relaxed">
          {input_text}
        </div>
      );
    }

    const chunkTrimmed = triggered_chunk.trim();
    const lowerInput = input_text.toLowerCase();
    const lowerChunk = chunkTrimmed.toLowerCase();
    const matchIndex = lowerInput.indexOf(lowerChunk);

    if (matchIndex !== -1) {
      const before = input_text.substring(0, matchIndex);
      const matched = input_text.substring(matchIndex, matchIndex + chunkTrimmed.length);
      const after = input_text.substring(matchIndex + chunkTrimmed.length);

      return (
        <div className="text-slate-300 text-xs font-mono whitespace-pre-wrap leading-relaxed">
          <span>{before}</span>
          <mark 
            id="highlighted-trigger-chunk"
            className="bg-rose-500/30 text-rose-200 border border-rose-500/70 rounded px-1.5 py-0.5 font-bold shadow-md shadow-rose-950/50"
          >
            {matched}
          </mark>
          <span>{after}</span>
        </div>
      );
    }

    // If chunk does not match verbatim (e.g. due to normalization/base64 decoding)
    return (
      <div className="space-y-2 font-mono text-xs">
        <div className="text-slate-300 whitespace-pre-wrap leading-relaxed">
          {input_text}
        </div>
      </div>
    );
  };

  return (
    <div className="w-full glass-panel rounded-2xl p-6 space-y-6 animate-slide-up border border-slate-800">
      {/* Header Verdict Badge & Action Tag */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="flex flex-wrap items-center gap-3">
          {renderTierBadge()}
          {renderDefenseBadge()}

          {source_type && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-xs font-mono">
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              <span>{source_type}</span>
            </div>
          )}

          {attack_type && attack_type !== 'none' && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-900 border border-slate-700/80 text-slate-300 text-xs font-mono">
              <Tag className="w-3.5 h-3.5 text-cyan-400" />
              <span>{attack_type}</span>
            </div>
          )}
        </div>

        {latency_ms !== undefined && (
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>Latency: {latency_ms}ms</span>
          </div>
        )}
      </div>

      {/* Main Score & Stacker Metrics */}
      <div className="space-y-4 bg-slate-950/50 p-4 rounded-xl border border-slate-800/80">
        <div className="flex items-center justify-between text-xs font-medium">
          <span className="text-slate-300 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            Stacker Risk Score (v2_final Candidate G)
          </span>
          <div className="flex items-center gap-2 font-mono">
            <span className="text-slate-400 text-xs">({Number(totalScore).toFixed(4)})</span>
            <span className={`text-base font-extrabold ${
              activeTier === 'block' ? 'text-rose-400' : (activeTier === 'isolate' ? 'text-amber-400' : 'text-emerald-400')
            }`}>
              {percentage}%
            </span>
          </div>
        </div>

        {/* Score Bar with Threshold Markers */}
        <div className="relative pt-2">
          <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden p-0.5 border border-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${
                activeTier === 'block'
                  ? 'bg-gradient-to-r from-amber-500 to-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.4)]'
                  : activeTier === 'isolate'
                  ? 'bg-gradient-to-r from-cyan-500 to-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.3)]'
                  : 'bg-gradient-to-r from-teal-500 to-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.3)]'
              }`}
              style={{ width: `${Math.max(percentage, 5)}%` }}
            />
          </div>

          {/* Threshold markers */}
          <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono pt-1.5 px-0.5">
            <span>0.00 (Clean)</span>
            <span className="text-amber-400/90 font-bold">| 0.90 Isolate</span>
            <span className="text-rose-400/90 font-bold">| 0.945 Block</span>
            <span>1.00 (Adversarial)</span>
          </div>
        </div>

        {/* Feature Breakdown */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-800/60">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span className="flex items-center gap-1">
                <Lock className="w-3 h-3 text-cyan-400" /> Max Heuristic Score
              </span>
              <span className="font-bold text-slate-200">{heurPercentage}%</span>
            </div>
            <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-cyan-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(heurPercentage, 3)}%` }}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span className="flex items-center gap-1">
                <Cpu className="w-3 h-3 text-teal-400" /> Max-Chunk Classifier Score
              </span>
              <span className="font-bold text-slate-200">{classPercentage}%</span>
            </div>
            <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-teal-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(classPercentage, 3)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Triggered Chunk & Highlighted Document Section */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 overflow-hidden">
        <button
          type="button"
          onClick={() => setIsChunkOpen(!isChunkOpen)}
          className="w-full px-4 py-3 flex items-center justify-between bg-slate-900/50 hover:bg-slate-800/40 text-xs font-semibold uppercase tracking-wider text-slate-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Crosshair className="w-4 h-4 text-rose-400" />
            <span>Document Inspection &amp; Triggered Chunk Highlighting</span>
          </div>
          {isChunkOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>

        {isChunkOpen && (
          <div className="p-4 space-y-4 font-mono text-xs">
            {triggered_chunk ? (
              <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/70 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                    Highest Suspicion Trigger Chunk
                  </span>
                  <span className="text-[10px] text-rose-400/90 font-mono bg-rose-950 px-2 py-0.5 rounded border border-rose-800/60">
                    Active Trigger
                  </span>
                </div>
                <div className="text-rose-100 font-mono text-xs bg-slate-950/70 p-2.5 rounded-lg border border-rose-900/40 whitespace-pre-wrap leading-relaxed">
                  "{triggered_chunk}"
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-slate-900/50 text-slate-400 text-xs">
                No anomalous chunk triggered above threshold.
              </div>
            )}

            {/* Document with In-line Highlighting */}
            {input_text && (
              <div className="space-y-1.5">
                <div className="text-slate-400 text-[11px] font-semibold uppercase flex items-center gap-1.5">
                  <FileSearch className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Inspected Text Body (Chunk Highlighted in Red)</span>
                </div>
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 max-h-72 overflow-y-auto">
                  {renderHighlightedDocument()}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* LLM Response Section */}
      <div className="space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <span>LLM Pipeline Response</span>
        </div>

        {defense_action === 'blocked' ? (
          <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs font-mono flex items-center gap-3">
            <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>Request blocked before reaching LLM (Block Tier Active: {percentage}%)</span>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 text-slate-200 text-xs font-mono leading-relaxed whitespace-pre-wrap">
            {llm_response || '[No response returned]'}
          </div>
        )}
      </div>

      {/* Output Validation Warning Badge */}
      {output_validation && output_validation.passed === false && (
        <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-200 text-xs space-y-2 animate-slide-up">
          <div className="flex items-center gap-2 font-bold text-rose-300 uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>Output Validation Failed — Security Issue Detected</span>
          </div>
          <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-rose-300">
            {output_validation.issues.map((issue, idx) => (
              <li key={idx}>{issue}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Matched Patterns Collapsible Section */}
      {matched_patterns && matched_patterns.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 overflow-hidden">
          <button
            type="button"
            onClick={() => setIsPatternsOpen(!isPatternsOpen)}
            className="w-full px-4 py-3 flex items-center justify-between bg-slate-900/50 hover:bg-slate-800/40 text-xs font-semibold uppercase tracking-wider text-slate-300 transition-colors cursor-pointer"
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
