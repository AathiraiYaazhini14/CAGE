import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import { useToast } from '../components/Toast';
import { VerdictBadge, SampleDataBadge, ActionBadge } from '../components/VerdictBadge';
import {
  ShieldAlert,
  Search,
  Filter,
  Download,
  Calendar,
  ChevronLeft,
  ChevronRight,
  X,
  Layers,
  Sparkles,
  BarChart3,
  Flame,
  Info,
  Clock,
  ExternalLink,
  Code2
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell
} from 'recharts';

export function AnalysisView() {
  const { addToast } = useToast();

  // Filters state
  const [range, setRange] = useState('30d');
  const [verdict, setVerdict] = useState('all');
  const [category, setCategory] = useState('all');
  const [sourceType, setSourceType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Pagination state
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [totalLogs, setTotalLogs] = useState(0);

  // Data state
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Selected Log Drawer state
  const [selectedLog, setSelectedLog] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Load stats
  const fetchStats = useCallback(async () => {
    try {
      const data = await api.stats.get(range === 'all' ? '30d' : range);
      setStats(data);
    } catch (err) {
      console.warn('Failed to load stats for analysis:', err);
    }
  }, [range]);

  // Load logs
  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const data = await api.logs.list({
        limit: pageSize,
        offset,
        range: range === 'all' ? undefined : range,
        verdict,
        category,
        source_type: sourceType,
        q: debouncedSearch,
      });

      setLogs(data.items || []);
      setTotalLogs(data.total || 0);
    } catch (err) {
      addToast(err.message || 'Failed to retrieve logs', 'error');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, range, verdict, category, sourceType, debouncedSearch, addToast]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Open Log Drawer
  const handleOpenDetail = async (logId) => {
    setLoadingDetail(true);
    setSelectedLog(null);
    try {
      const full = await api.logs.get(logId);
      setSelectedLog(full);
    } catch (err) {
      addToast(err.message || 'Failed to fetch detailed audit record', 'error');
    } finally {
      setLoadingDetail(false);
    }
  };

  // Export CSV
  const handleExportCsv = async () => {
    setExporting(true);
    try {
      await api.logs.exportCsv({
        range: range === 'all' ? undefined : range,
        verdict,
        category,
        source_type: sourceType,
        q: debouncedSearch,
      });
      addToast('Audit log export downloaded successfully', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to export CSV', 'error');
    } finally {
      setExporting(false);
    }
  };

  const totalPages = Math.ceil(totalLogs / pageSize) || 1;

  // "Where attacks come from" data
  const sourcesData = [
    {
      source: 'User Input',
      count: stats?.source_types?.user_input || 0,
      fill: '#7C6CF0',
    },
    {
      source: 'Retrieved Docs',
      count: stats?.source_types?.retrieved_document || 0,
      fill: '#9082F5',
    },
    {
      source: 'Tool Output',
      count: stats?.source_types?.tool_output || 0,
      fill: '#5846E2',
    },
  ];

  // Dynamic insight line
  const totalAttacksBySource = sourcesData.reduce((acc, s) => acc + s.count, 0);
  const ragCount = stats?.source_types?.retrieved_document || 0;
  const ragShare = totalAttacksBySource > 0 ? Math.round((ragCount / totalAttacksBySource) * 100) : 0;

  const generatedInsight =
    ragShare >= 30
      ? `${ragShare}% of intercepted attacks originated from retrieved documents, indicating heavy indirect injection targeting downstream RAG pipelines.`
      : `Direct user inputs account for the majority of detected threats; autonomous input isolation remains the primary defense layer.`;

  // Hour-by-weekday heatmap preparation
  const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const heatmapMatrix = stats?.weekday_hour_matrix || Array(7).fill(Array(24).fill(0));

  // Find max value in heatmap for normalized opacity
  let maxHeat = 1;
  heatmapMatrix.forEach((row) => {
    row.forEach((v) => {
      if (v > maxHeat) maxHeat = v;
    });
  });

  return (
    <div className="space-y-6">
      {/* 1. TOP HEADER & TELEMETRY SUMMARY */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#7C6CF0]" />
            <span>Threat Analysis & Audit Logs</span>
          </h1>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Full telemetry on inspected payloads, chunk-level scoring, and temporal attack distributions.
          </p>
        </div>

        {/* Defense Outcomes & CSV Export */}
        <div className="flex items-center gap-3">
          {/* Prevented Calls Stat Badge */}
          <div className="panel-card px-3.5 py-1.5 flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-[#7C6CF0]" />
            <div className="text-xs">
              <span className="text-[#94A3B8]">LLM Calls Prevented: </span>
              <strong className="text-white font-mono font-bold">
                {stats?.prevented_calls?.toLocaleString() || 0}
              </strong>
            </div>
          </div>

          <button
            onClick={handleExportCsv}
            disabled={exporting}
            className="panel-card px-3.5 py-2 hover:border-[#7C6CF0]/50 hover:bg-[#1A1A26] transition-all text-xs font-medium text-white flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <Download className={`w-3.5 h-3.5 ${exporting ? 'animate-bounce text-[#7C6CF0]' : ''}`} />
            <span>{exporting ? 'Exporting...' : 'Export CSV'}</span>
          </button>
        </div>
      </div>

      {/* 2. WHERE ATTACKS COME FROM & TOP TRIGGERED PHRASES ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Where attacks come from chart (2 cols) */}
        <div className="panel-card p-5 lg:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-sm font-semibold text-white">Where Attacks Originate</h3>
              <p className="text-xs text-[#94A3B8]">
                Payload distribution across direct inputs, retrieved documents, and tool responses
              </p>
            </div>
            <BarChart3 className="w-4 h-4 text-[#7C6CF0]" />
          </div>

          <div className="h-44 w-full my-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sourcesData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <XAxis type="number" stroke="#64748B" tick={{ fill: '#64748B', fontSize: 11 }} />
                <YAxis dataKey="source" type="category" stroke="#64748B" tick={{ fill: '#CBD5E1', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#12121A',
                    borderColor: '#232333',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontFamily: 'var(--font-mono)',
                  }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                  {sourcesData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Generated Insight Line */}
          <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#232333] flex items-start gap-2.5">
            <Info className="w-4 h-4 text-[#7C6CF0] mt-0.5 shrink-0" />
            <p className="text-xs text-[#CBD5E1] leading-relaxed">
              <strong className="text-white">Security Telemetry Insight:</strong> {generatedInsight}
            </p>
          </div>
        </div>

        {/* Top Triggered Phrases List (1 col) */}
        <div className="panel-card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-semibold text-white">Top Triggered Patterns</h3>
              <Flame className="w-4 h-4 text-[#F59E0B]" />
            </div>
            <p className="text-xs text-[#94A3B8] mb-3">
              Most frequent heuristic signature matches
            </p>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {!stats?.top_patterns || stats.top_patterns.length === 0 ? (
                <div className="text-xs text-[#64748B] py-6 text-center font-mono">
                  No heuristic matches recorded
                </div>
              ) : (
                stats.top_patterns.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-[#0A0A0F] border border-[#232333] flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-mono text-white truncate font-medium">
                        "{item.pattern}"
                      </div>
                      <div className="text-[10px] text-[#64748B] capitalize">
                        {item.category ? item.category.replace(/_/g, ' ') : 'heuristic'}
                      </div>
                    </div>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#232333] text-[#7C6CF0] shrink-0">
                      {item.count}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="text-[11px] text-[#64748B] mt-2 font-mono">
            * Scored with bounded regex weights (0.15 - 0.40)
          </div>
        </div>
      </div>

      {/* 3. HOUR-BY-WEEKDAY INCIDENT HEATMAP */}
      <div className="panel-card p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Temporal Incident Density (7 × 24 Heatmap)</h3>
            <p className="text-xs text-[#94A3B8]">
              Scan concentration by day-of-week and hour-of-day
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#64748B]">
            <span>Low</span>
            <div className="flex gap-1">
              <span className="w-3 h-3 rounded-sm bg-[#232333]" />
              <span className="w-3 h-3 rounded-sm bg-[#7C6CF0]/30" />
              <span className="w-3 h-3 rounded-sm bg-[#7C6CF0]/60" />
              <span className="w-3 h-3 rounded-sm bg-[#7C6CF0]" />
            </div>
            <span>High</span>
          </div>
        </div>

        <div className="overflow-x-auto pb-2">
          <div className="min-w-[640px]">
            {/* Hour Headers (00 to 23) */}
            <div className="grid grid-cols-[48px_repeat(24,1fr)] gap-1 text-[10px] font-mono text-[#64748B] text-center mb-1">
              <span />
              {Array.from({ length: 24 }).map((_, h) => (
                <span key={h}>{h % 3 === 0 ? `${h}h` : ''}</span>
              ))}
            </div>

            {/* Matrix Rows */}
            {daysOfWeek.map((day, dayIdx) => (
              <div key={day} className="grid grid-cols-[48px_repeat(24,1fr)] gap-1 items-center mb-1">
                <span className="text-xs font-mono text-[#94A3B8] font-medium">{day}</span>
                {heatmapMatrix[dayIdx]?.map((val, hIdx) => {
                  const ratio = val > 0 ? Math.max(0.2, val / maxHeat) : 0;
                  const bgColor =
                    val === 0
                      ? '#12121A'
                      : `rgba(124, 108, 240, ${ratio})`;
                  return (
                    <div
                      key={hIdx}
                      title={`${day} ${hIdx}:00 — ${val} scan(s)`}
                      className="h-6 rounded-sm border border-[#232333]/60 transition-all hover:scale-110 hover:border-white cursor-pointer flex items-center justify-center text-[9px] font-mono text-white/80"
                      style={{ backgroundColor: bgColor }}
                    >
                      {val > 0 ? val : ''}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. FILTERS BAR */}
      <div className="panel-card p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#7C6CF0]" />
            <span className="text-xs font-semibold text-white uppercase tracking-wider">
              Filter Audit Stream
            </span>
          </div>

          <div className="text-xs text-[#94A3B8] font-mono">
            Showing <strong className="text-white">{logs.length}</strong> of{' '}
            <strong className="text-white">{totalLogs}</strong> records
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          {/* Search Input */}
          <div className="relative md:col-span-2">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#64748B]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search prompts, snippets, or IDs..."
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#0A0A0F] border border-[#232333] text-xs text-white placeholder-[#64748B] focus:border-[#7C6CF0] focus:ring-1 focus:ring-[#7C6CF0] outline-none font-mono"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Verdict Filter */}
          <div>
            <select
              value={verdict}
              onChange={(e) => {
                setVerdict(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-lg bg-[#0A0A0F] border border-[#232333] text-xs text-white focus:border-[#7C6CF0] outline-none"
            >
              <option value="all">All Verdicts</option>
              <option value="allow">Allow</option>
              <option value="isolate">Isolate</option>
              <option value="block">Block</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-lg bg-[#0A0A0F] border border-[#232333] text-xs text-white focus:border-[#7C6CF0] outline-none"
            >
              <option value="all">All Attack Types</option>
              <option value="instruction_override">Instruction Override</option>
              <option value="role_override">Role Override / Jailbreak</option>
              <option value="prompt_extraction">Prompt Extraction</option>
              <option value="action_hijack">Action Hijack</option>
              <option value="delimiter_injection">Delimiter Injection</option>
            </select>
          </div>

          {/* Source Type Filter */}
          <div>
            <select
              value={sourceType}
              onChange={(e) => {
                setSourceType(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-lg bg-[#0A0A0F] border border-[#232333] text-xs text-white focus:border-[#7C6CF0] outline-none"
            >
              <option value="all">All Source Types</option>
              <option value="user_input">User Input</option>
              <option value="retrieved_document">Retrieved Document</option>
              <option value="tool_output">Tool Output</option>
            </select>
          </div>
        </div>
      </div>

      {/* 5. THREAT LOG TABLE */}
      <div className="panel-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#232333] bg-[#0A0A0F]/60 text-[#64748B] font-mono uppercase tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Input Snippet</th>
                <th className="py-3 px-4">Calibrated Score</th>
                <th className="py-3 px-4">Tier / Verdict</th>
                <th className="py-3 px-4">Action Taken</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#232333]/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-[#64748B] font-mono">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-[#7C6CF0] border-t-transparent rounded-full animate-spin" />
                      <span>Streaming audit records from SQLite...</span>
                    </div>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-[#64748B] font-mono">
                    No threat logs matched the specified filter criteria
                  </td>
                </tr>
              ) : (
                logs.map((row) => {
                  const score = row.final_score ?? row.classifier_score ?? 0;
                  return (
                    <tr
                      key={row.id}
                      onClick={() => handleOpenDetail(row.id)}
                      className="hover:bg-[#1A1A26]/60 transition-colors cursor-pointer group"
                    >
                      {/* Timestamp */}
                      <td className="py-3 px-4 font-mono text-[#94A3B8] whitespace-nowrap">
                        {row.timestamp ? row.timestamp.replace('T', ' ').slice(0, 19) : '—'}
                      </td>

                      {/* Source */}
                      <td className="py-3 px-4 font-mono whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded bg-[#0A0A0F] border border-[#232333] text-[#CBD5E1]">
                          {row.source_type || 'user_input'}
                        </span>
                      </td>

                      {/* Input Snippet */}
                      <td className="py-3 px-4 font-mono text-white max-w-xs sm:max-w-md truncate">
                        <div className="flex items-center gap-2 truncate">
                          <span className="truncate">{row.input_text || '—'}</span>
                          {row.is_demo === 1 && <SampleDataBadge />}
                        </div>
                      </td>

                      {/* Score */}
                      <td className="py-3 px-4 font-mono whitespace-nowrap">
                        <span
                          className={`font-bold ${
                            score >= 0.945
                              ? 'text-[#EF4444]'
                              : score >= 0.9
                              ? 'text-[#F59E0B]'
                              : 'text-[#10B981]'
                          }`}
                        >
                          {score.toFixed(4)}
                        </span>
                      </td>

                      {/* Tier / Verdict */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <VerdictBadge verdict={row.tier || row.defense_action} size="xs" />
                      </td>

                      {/* Action Taken */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <ActionBadge action={row.defense_action} />
                      </td>

                      {/* Details Link */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <span className="text-xs text-[#7C6CF0] group-hover:underline font-mono">
                          Inspect &rarr;
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-3.5 border-t border-[#232333] flex items-center justify-between gap-3 text-xs font-mono">
          <div className="text-[#64748B]">
            Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="px-3 py-1.5 rounded-lg bg-[#0A0A0F] border border-[#232333] hover:border-[#7C6CF0]/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-white flex items-center gap-1 cursor-pointer"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="px-3 py-1.5 rounded-lg bg-[#0A0A0F] border border-[#232333] hover:border-[#7C6CF0]/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-white flex items-center gap-1 cursor-pointer"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* 6. DETAIL DRAWER (MODAL) */}
      {(selectedLog || loadingDetail) && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/70 backdrop-blur-sm p-4 sm:p-6 animate-fade-in">
          <div className="w-full max-w-xl h-full panel-card flex flex-col justify-between overflow-hidden shadow-2xl border border-[#7C6CF0]/30 animate-slide-up">
            {/* Drawer Header */}
            <div className="p-5 border-b border-[#232333] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-[#7C6CF0]" />
                <h3 className="text-sm font-semibold text-white font-mono">
                  Audit Transaction #{selectedLog?.id}
                </h3>
                {selectedLog?.is_demo === 1 && <SampleDataBadge />}
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[#232333] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="p-6 overflow-y-auto space-y-5 flex-1 font-sans text-xs">
              {loadingDetail ? (
                <div className="py-20 text-center font-mono text-[#64748B]">
                  Loading audit log payload...
                </div>
              ) : selectedLog && (
                <>
                  {/* Verdict & Score Metrics Header */}
                  <div className="grid grid-cols-3 gap-3 p-3.5 rounded-xl bg-[#0A0A0F] border border-[#232333]">
                    <div>
                      <div className="text-[10px] text-[#64748B] uppercase font-mono mb-1">Decision Tier</div>
                      <VerdictBadge verdict={selectedLog.tier || selectedLog.defense_action} size="md" />
                    </div>
                    <div>
                      <div className="text-[10px] text-[#64748B] uppercase font-mono mb-1">Defense Action</div>
                      <ActionBadge action={selectedLog.defense_action} />
                    </div>
                    <div>
                      <div className="text-[10px] text-[#64748B] uppercase font-mono mb-1">Calibrated Score</div>
                      <div className="text-base font-bold font-mono text-white">
                        {(selectedLog.final_score ?? selectedLog.classifier_score ?? 0).toFixed(4)}
                      </div>
                    </div>
                  </div>

                  {/* Highlighted Triggered Chunk */}
                  <div>
                    <label className="text-[11px] font-mono text-[#7C6CF0] uppercase tracking-wider block mb-1.5 font-bold">
                      Triggered Chunk (Highest Risk Window)
                    </label>
                    <div className="p-3.5 rounded-lg bg-[#0A0A0F] border border-[#EF4444]/40 font-mono text-xs text-[#CBD5E1] leading-relaxed">
                      {selectedLog.triggered_chunk ? (
                        <span className="bg-[#EF4444]/25 text-[#FCA5A5] px-1 py-0.5 rounded border border-[#EF4444]/40">
                          {selectedLog.triggered_chunk}
                        </span>
                      ) : (
                        <span className="text-[#64748B] italic">No isolated attack chunk identified</span>
                      )}
                    </div>
                  </div>

                  {/* Full Input Payload */}
                  <div>
                    <label className="text-[11px] font-mono text-[#94A3B8] uppercase tracking-wider block mb-1.5">
                      Full Input Text ({selectedLog.source_type || 'user_input'})
                    </label>
                    <div className="p-3.5 rounded-lg bg-[#0A0A0F] border border-[#232333] font-mono text-xs text-[#CBD5E1] leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
                      {selectedLog.input_text}
                    </div>
                  </div>

                  {/* Matched Heuristic Patterns */}
                  <div>
                    <label className="text-[11px] font-mono text-[#94A3B8] uppercase tracking-wider block mb-1.5">
                      Matched Heuristic Signatures
                    </label>
                    {(!selectedLog.matched_patterns || selectedLog.matched_patterns.length === 0) ? (
                      <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#232333] text-[#64748B] font-mono text-xs">
                        Zero regex matches; scored via character n-gram subword features
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {selectedLog.matched_patterns.map((pat, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-lg bg-[#0A0A0F] border border-[#232333] flex items-center justify-between text-xs"
                          >
                            <div>
                              <span className="font-mono text-white">"{pat.pattern}"</span>
                              <span className="text-[10px] text-[#64748B] block capitalize">
                                Category: {pat.category}
                              </span>
                            </div>
                            <span className="px-2 py-0.5 rounded bg-[#232333] text-[#7C6CF0] font-mono font-bold">
                              +{pat.weight}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Telemetry Metadata */}
                  <div className="pt-2 border-t border-[#232333] grid grid-cols-2 gap-2 text-[11px] text-[#64748B] font-mono">
                    <div>Latency: <span className="text-white">{selectedLog.latency_ms ?? '—'} ms</span></div>
                    <div>Source Type: <span className="text-white">{selectedLog.source_type}</span></div>
                    <div>Timestamp: <span className="text-white">{selectedLog.timestamp}</span></div>
                    <div>User ID: <span className="text-white">{selectedLog.user_id ?? 'Anonymous'}</span></div>
                  </div>
                </>
              )}
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-[#232333] bg-[#0A0A0F] flex items-center justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-lg bg-[#12121A] border border-[#232333] hover:border-white text-xs font-medium text-white transition-colors cursor-pointer"
              >
                Close Record
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

