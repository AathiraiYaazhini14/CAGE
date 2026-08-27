import React from 'react';
import { Search, Loader2, AlertTriangle, Send } from 'lucide-react';

export default function AnalyzerInput({ text, setText, onAnalyze, isLoading, error }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && !isLoading) {
      onAnalyze(text);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      <div className="relative">
        <div className="flex items-center justify-between mb-2">
          <label htmlFor="prompt-input" className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5 text-cyan-400" />
            <span>Prompt Inspection Payload</span>
          </label>
          <span className="text-xs text-slate-500 font-mono">
            {text.length} chars
          </span>
        </div>

        <textarea
          id="prompt-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste or type an LLM prompt to inspect for injection vulnerabilities..."
          rows={5}
          className="w-full glass-input rounded-xl p-4 text-slate-100 placeholder-slate-500 focus:outline-none font-mono text-sm leading-relaxed resize-y min-h-[130px]"
        />

        {error && (
          <div className="mt-3 p-3 rounded-lg bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2.5 animate-slide-up">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      <div className="flex justify-end gap-3">
        {text && (
          <button
            type="button"
            onClick={() => setText('')}
            className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
          >
            Clear Input
          </button>
        )}

        <button
          type="submit"
          disabled={!text.trim() || isLoading}
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium text-sm text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-400 hover:from-cyan-300 hover:to-teal-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20 transition-all duration-200 active:scale-95 cursor-pointer"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
              <span>Analyzing Prompt...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4 text-slate-950" />
              <span>Analyze Prompt</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
}
