import React from 'react';
import { ShieldCheck, AlertCircle, Ban, Database } from 'lucide-react';

export function VerdictBadge({ verdict, size = 'sm', showIcon = true }) {
  const norm = (verdict || 'allow').toLowerCase();

  let styles = 'bg-[#10B981]/15 text-[#10B981] border-[#10B981]/40';
  let Icon = ShieldCheck;
  let label = 'ALLOW';

  if (norm === 'block' || norm === 'blocked') {
    styles = 'bg-[#EF4444]/15 text-[#EF4444] border-[#EF4444]/40';
    Icon = Ban;
    label = 'BLOCK';
  } else if (norm === 'isolate' || norm === 'isolated') {
    styles = 'bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/40';
    Icon = AlertCircle;
    label = 'ISOLATE';
  }

  const sizeClasses =
    size === 'lg'
      ? 'px-3 py-1.5 text-xs'
      : size === 'md'
        ? 'px-2.5 py-1 text-[11px]'
        : 'px-2 py-0.5 text-[10px]';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-semibold rounded-md border tracking-wider uppercase ${sizeClasses} ${styles}`}
    >
      {showIcon && <Icon className={size === 'lg' ? 'w-3.5 h-3.5' : 'w-3 h-3'} />}
      <span>{label}</span>
    </span>
  );
}

export function SampleDataBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono tracking-wider bg-[#232333]/80 text-[#94A3B8] border border-[#232333]">
      <Database className="w-2.5 h-2.5 text-[#7C6CF0]" />
      <span>Sample data</span>
    </span>
  );
}

export function ActionBadge({ action }) {
  const norm = (action || 'allow').toLowerCase();

  if (norm === 'blocked' || norm === 'dropped') {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/30">
        {norm}
      </span>
    );
  }
  if (norm === 'isolated') {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30">
        isolated
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30">
      allowed
    </span>
  );
}

