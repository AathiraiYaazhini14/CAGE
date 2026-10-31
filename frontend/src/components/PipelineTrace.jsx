import React from 'react';
import { 
  FileInput, 
  ShieldCheck, 
  ShieldAlert, 
  Bot, 
  CheckCheck, 
  XCircle,
  ArrowRight
} from 'lucide-react';

export default function PipelineTrace({ result }) {
  if (!result) return null;

  const { defense_action = 'allow', output_validation } = result;
  const isBlocked = defense_action === 'blocked';
  const valPassed = output_validation ? output_validation.passed : true;

  const steps = [
    {
      id: 'input',
      label: 'Input Payload',
      icon: FileInput,
      status: 'completed', // Always runs
      detail: 'Payload Received',
    },
    {
      id: 'detection',
      label: 'Score Fusion',
      icon: ShieldCheck,
      status: 'completed', // Always runs
      detail: 'Heuristics + ML',
    },
    {
      id: 'defense',
      label: 'Defense Engine',
      icon: isBlocked ? ShieldAlert : ShieldCheck,
      status: 'completed',
      detail: defense_action.toUpperCase(),
    },
    {
      id: 'llm',
      label: 'LLM Execution',
      icon: Bot,
      status: isBlocked ? 'skipped' : 'completed',
      detail: isBlocked ? 'Blocked (Skipped)' : 'Processed',
    },
    {
      id: 'validation',
      label: 'Output Validation',
      icon: valPassed ? CheckCheck : XCircle,
      status: isBlocked ? 'skipped' : (valPassed ? 'completed' : 'failed'),
      detail: isBlocked ? 'Skipped' : (valPassed ? 'Passed' : 'Failed'),
    },
  ];

  const getStepClasses = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-cyan-950/80 border-cyan-500/50 text-cyan-300 shadow-md shadow-cyan-950/50';
      case 'failed':
        return 'bg-rose-950/80 border-rose-500/50 text-rose-300 shadow-md shadow-rose-950/50';
      case 'skipped':
      default:
        return 'bg-slate-900/40 border-slate-800 text-slate-600 opacity-60';
    }
  };

  const getBadgeClasses = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60';
      case 'failed':
        return 'bg-rose-950/80 text-rose-400 border-rose-800/60';
      case 'skipped':
      default:
        return 'bg-slate-950/80 text-slate-500 border-slate-800';
    }
  };

  return (
    <div className="w-full glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
        <ArrowRight className="w-4 h-4 text-cyan-400" />
        <span>Execution Pipeline Trace</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-1">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div
              key={step.id}
              className={`p-3 rounded-xl border flex flex-col justify-between space-y-2 transition-all duration-300 ${getStepClasses(
                step.status
              )}`}
            >
              <div className="flex items-center justify-between">
                <Icon className="w-4 h-4 shrink-0" />
                <span className="text-[10px] font-mono text-slate-500 font-bold">
                  0{index + 1}
                </span>
              </div>

              <div>
                <p className="text-xs font-bold truncate text-slate-200">
                  {step.label}
                </p>
                <span
                  className={`inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-mono border ${getBadgeClasses(
                    step.status
                  )}`}
                >
                  {step.detail}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
