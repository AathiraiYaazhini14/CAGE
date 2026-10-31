import React, { useState } from 'react';
import { 
  Search, 
  Loader2, 
  AlertTriangle, 
  Send, 
  FileText, 
  MessageSquare, 
  Layers, 
  ChevronDown 
} from 'lucide-react';

export default function AnalyzerInput({ 
  text, 
  setText, 
  sourceType, 
  setSourceType, 
  mode, 
  setMode, 
  onAnalyze, 
  isLoading, 
  error 
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && !isLoading) {
      onAnalyze(text, sourceType);
    }
  };

  const isDocMode = mode === 'document';

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      {/* Mode Selector and Source Type Dropdown */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-1">
        <div className="inline-flex rounded-xl bg-slate-900/90 p-1 border border-slate-800 text-xs">
          <button
            type="button"
            id="mode-prompt-btn"
            onClick={() => setMode('prompt')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
              !isDocMode 
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Prompt Mode</span>
          </button>

          <button
            type="button"
            id="mode-document-btn"
            onClick={() => setMode('document')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
              isDocMode 
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            <span>Document Mode</span>
          </button>
        </div>

        {/* Source Type Selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="source-type-select" className="text-xs text-slate-400 font-mono flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Source Type:</span>
          </label>
          <div className="relative">
            <select
              id="source-type-select"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="appearance-none bg-slate-900/90 border border-slate-700/80 rounded-xl px-3 py-1.5 pr-8 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500 cursor-pointer shadow-inner"
            >
              <option value="user_input">user_input (Direct Prompt)</option>
              <option value="retrieved_document">retrieved_document (RAG / Context)</option>
              <option value="tool_output">tool_output (Agent API)</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Main Textarea Area */}
      <div className="relative">
        <div className="flex items-center justify-between mb-2">
          <label 
            htmlFor="prompt-input" 
            className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5"
          >
            <Search className="w-3.5 h-3.5 text-cyan-400" />
            <span>{isDocMode ? "Document / Context Payload" : "Prompt Inspection Payload"}</span>
          </label>
          <div className="flex items-center gap-3 text-xs text-slate-500 font-mono">
            <span>{text.split(/\s+/).filter(Boolean).length} words</span>
            <span>•</span>
            <span>{text.length} chars</span>
          </div>
        </div>

        <textarea
          id="prompt-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            isDocMode
              ? "Paste a full document, resume, external article, or RAG context to scan for embedded prompt injections across fine-grained sliding chunks..."
              : "Paste or type an LLM prompt to inspect for injection vulnerabilities..."
          }
          rows={isDocMode ? 12 : 5}
          className={`w-full glass-input rounded-xl p-4 text-slate-100 placeholder-slate-500 focus:outline-none font-mono text-sm leading-relaxed resize-y ${
            isDocMode ? 'min-h-[260px]' : 'min-h-[130px]'
          }`}
        />

        {error && (
          <div className="mt-3 p-3 rounded-lg bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2.5 animate-slide-up">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between pt-1">
        <div className="text-xs text-slate-500 font-mono">
          Tier thresholds: <span className="text-amber-400 font-bold">isolate &ge; 0.90</span> |{' '}
          <span className="text-rose-400 font-bold">block &ge; 0.945</span>
        </div>

        <div className="flex items-center gap-3">
          {text && (
            <button
              type="button"
              id="clear-input-btn"
              onClick={() => setText('')}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors cursor-pointer"
            >
              Clear Input
            </button>
          )}

          <button
            type="submit"
            id="analyze-submit-btn"
            disabled={!text.trim() || isLoading}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium text-sm text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-400 hover:from-cyan-300 hover:to-teal-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20 transition-all duration-200 active:scale-95 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                <span>Analyzing {isDocMode ? 'Document' : 'Payload'}...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4 text-slate-950" />
                <span>Scan &amp; Defense Engine</span>
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
