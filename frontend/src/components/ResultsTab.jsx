import React from 'react';
import { 
  Trophy, 
  AlertTriangle, 
  CheckCircle2, 
  BarChart3, 
  ShieldCheck, 
  Layers, 
  Info,
  Scale
} from 'lucide-react';
import benchmarkData from '../data/benchmarkResults.json';

export default function ResultsTab() {
  const { candidates, production_tiers, note_holdout_fpr, candidate_g_stress_breakdown } = benchmarkData;

  return (
    <div className="w-full space-y-8 animate-slide-up">
      {/* Overview Banner */}
      <div className="glass-panel rounded-2xl p-6 border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 via-slate-950/60 to-slate-900/40 space-y-3">
        <div className="flex items-center gap-2.5 text-cyan-400 font-semibold text-sm">
          <Trophy className="w-5 h-5 text-amber-400" />
          <span>Final Detection Selection Matrix</span>
        </div>
        <p className="text-slate-300 text-sm leading-relaxed">
          Comparing the final detector candidates across the frozen test set, external holdout benchmark, 
          and 200-word embedded-injection stress test. The shipped production engine is{' '}
          <strong className="text-white">Candidate G (Ablated Stacker)</strong>, enforcing multi-tier defense 
          with calibrated thresholds.
        </p>
        <div className="flex items-center gap-2 text-xs text-amber-300/90 font-mono bg-amber-950/40 border border-amber-800/50 rounded-lg px-3 py-2">
          <Info className="w-4 h-4 text-amber-400 shrink-0" />
          <span>{note_holdout_fpr}</span>
        </div>
      </div>

      {/* Production Multi-Tier Defense Rules */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> Allow Tier
            </span>
            <span className="text-xs font-mono font-bold text-slate-300">&lt; 0.9000</span>
          </div>
          <p className="text-xs text-slate-400">
            Clean prompt or low-suspicion content. Dispatched directly to upstream LLM pipeline without alterations.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4" /> Isolate Tier
            </span>
            <span className="text-xs font-mono font-bold text-slate-300">0.9000 – 0.9450</span>
          </div>
          <p className="text-xs text-slate-400">
            Quarantine suspicious inputs inside untrusted external delimiters: 
            <code className="text-amber-300 block mt-1 text-[11px] bg-slate-950 p-1 rounded font-mono">[UNTRUSTED EXTERNAL CONTENT]</code>
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" /> Block Tier
            </span>
            <span className="text-xs font-mono font-bold text-slate-300">&ge; 0.9450</span>
          </div>
          <p className="text-xs text-slate-400">
            Confirmed adversarial injection. Immediate termination of upstream execution (<code className="text-rose-300">safe_text = None</code>).
          </p>
        </div>
      </div>

      {/* Main Candidate Comparison Table */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden space-y-4 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            <span>Benchmark Comparison Matrix</span>
          </div>
          <span className="text-xs text-slate-500 font-mono">Dev / Test / Holdout / Stress</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400">
                <th className="py-3 px-3">Candidate Engine</th>
                <th className="py-3 px-2">Test F1</th>
                <th className="py-3 px-2">Test Rec</th>
                <th className="py-3 px-2">Test FPR</th>
                <th className="py-3 px-2">Holdout F1</th>
                <th className="py-3 px-2">Holdout Rec</th>
                <th className="py-3 px-2">Holdout FPR*</th>
                <th className="py-3 px-2">200w Stress Rec</th>
                <th className="py-3 px-3">Selection Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {candidates.map((cand) => (
                <tr 
                  key={cand.key}
                  className={cand.is_shipped 
                    ? "bg-cyan-950/30 border-l-4 border-l-cyan-400 hover:bg-cyan-950/40" 
                    : "hover:bg-slate-900/40"}
                >
                  <td className="py-3 px-3 font-sans font-medium text-slate-200">
                    <div className="flex items-center gap-2">
                      {cand.is_shipped && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40">
                          PROD
                        </span>
                      )}
                      <span>{cand.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-2 font-bold text-slate-200">{(cand.test_f1 * 100).toFixed(1)}%</td>
                  <td className="py-3 px-2 text-slate-300">{(cand.test_recall * 100).toFixed(1)}%</td>
                  <td className={`py-3 px-2 font-bold ${cand.test_fpr <= 0.05 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {(cand.test_fpr * 100).toFixed(2)}%
                  </td>
                  <td className="py-3 px-2 text-slate-300">{(cand.holdout_f1 * 100).toFixed(1)}%</td>
                  <td className="py-3 px-2 text-slate-300">{(cand.holdout_recall * 100).toFixed(1)}%</td>
                  <td className="py-3 px-2 text-emerald-400">{(cand.holdout_fpr * 100).toFixed(1)}%</td>
                  <td className="py-3 px-2 font-bold text-cyan-300">{(cand.stress_200w_recall * 100).toFixed(1)}%</td>
                  <td className="py-3 px-3 font-sans text-xs">
                    <span className={`inline-block px-2 py-0.5 rounded text-[11px] ${
                      cand.is_shipped 
                        ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800' 
                        : 'bg-slate-800/60 text-slate-400'
                    }`}>
                      {cand.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Embedding Stress Test Breakdown for Shipped Model */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Shipped Candidate G: Embedded Injection Stress Profile</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          Evaluating how well the shipped ablated stacker catches short injection payloads surrounded by 50, 200, 
          and 500 words of benign document padding across start, middle, and end positions:
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-center space-y-1">
            <span className="text-[11px] text-slate-400 uppercase font-mono">50-Word Recall</span>
            <div className="text-lg font-bold font-mono text-cyan-400">
              {(candidate_g_stress_breakdown.pad_50w_recall * 100).toFixed(1)}%
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-center space-y-1">
            <span className="text-[11px] text-slate-400 uppercase font-mono">200-Word Recall</span>
            <div className="text-lg font-bold font-mono text-cyan-400">
              {(candidate_g_stress_breakdown.pad_200w_recall * 100).toFixed(1)}%
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-center space-y-1">
            <span className="text-[11px] text-slate-400 uppercase font-mono">500-Word Recall</span>
            <div className="text-lg font-bold font-mono text-cyan-400">
              {(candidate_g_stress_breakdown.pad_500w_recall * 100).toFixed(1)}%
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-center space-y-1">
            <span className="text-[11px] text-slate-400 uppercase font-mono">Benign Padding FPR</span>
            <div className="text-lg font-bold font-mono text-emerald-400">
              {(candidate_g_stress_breakdown.benign_padding_fpr * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-400 space-y-1.5">
          <div className="flex items-center gap-1.5 font-semibold text-slate-300">
            <Scale className="w-4 h-4 text-cyan-400" />
            <span>Design Decision Rationale</span>
          </div>
          <p>
            Candidate E/D achieved high 200-word recall (91.1%) via regex OR rules, but produced an unviable{' '}
            <strong className="text-rose-400">33.8% Test FPR</strong> and{' '}
            <strong className="text-rose-400">67.8% Benign Padding FPR</strong>. Candidate G was selected because it preserves a strict{' '}
            <strong className="text-emerald-400">4.29% Test FPR</strong> (&le; 5%) while delivering the highest robust recall among qualifying models.
          </p>
        </div>
      </div>
    </div>
  );
}
