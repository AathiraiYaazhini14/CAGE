import React, { useState } from 'react';
import { ShieldCheck, Lock, Cpu, Radio, ShieldAlert, BarChart3, Terminal } from 'lucide-react';
import AnalyzerInput from './components/AnalyzerInput';
import SampleAttacks from './components/SampleAttacks';
import ResultCard from './components/ResultCard';
import PipelineTrace from './components/PipelineTrace';
import LogsPanel from './components/LogsPanel';
import ResultsTab from './components/ResultsTab';

export default function App() {
  const [activeTab, setActiveTab] = useState('playground'); // 'playground' | 'results'
  const [text, setText] = useState('');
  const [sourceType, setSourceType] = useState('user_input');
  const [mode, setMode] = useState('prompt'); // 'prompt' | 'document'
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async (promptText, selectedSourceType = sourceType) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          text: promptText,
          source_type: selectedSourceType
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned error status: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error('Fetch error:', err);
      setError('Backend server not reachable. Ensure uvicorn is running on http://localhost:8000');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSample = (sampleText, sampleSourceType = 'user_input') => {
    setText(sampleText);
    setSourceType(sampleSourceType);
    if (sampleSourceType === 'retrieved_document') {
      setMode('document');
    }
    setError(null);
  };

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto flex flex-col justify-between space-y-8">
      {/* Header Section */}
      <header className="space-y-6 text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/70 border border-cyan-700/50 text-cyan-400 text-xs font-mono tracking-wide shadow-lg shadow-cyan-950/40">
          <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
          <span>Multi-Layer LLM Firewall & Defense Pipeline v2</span>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-center gap-3">
            <div className="p-3 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-teal-500/10 border border-cyan-500/30 text-cyan-400 shadow-xl shadow-cyan-500/10">
              <ShieldCheck className="w-9 h-9" />
            </div>
            <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white font-sans">
              CAGE
            </h1>
          </div>
          <p className="text-slate-400 text-sm sm:text-base font-medium max-w-lg mx-auto">
            Context-Aware Guard for LLM Exploits
          </p>
        </div>

        {/* Primary View Switcher Navigation */}
        <div className="flex justify-center pt-2">
          <div className="inline-flex rounded-2xl bg-slate-900/90 p-1.5 border border-slate-800 shadow-xl">
            <button
              type="button"
              id="tab-playground-btn"
              onClick={() => setActiveTab('playground')}
              className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === 'playground'
                  ? 'bg-gradient-to-r from-cyan-500/30 to-teal-500/20 text-cyan-300 border border-cyan-500/50 shadow-md shadow-cyan-950/50'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>Live Defense Playground</span>
            </button>

            <button
              type="button"
              id="tab-results-btn"
              onClick={() => setActiveTab('results')}
              className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === 'results'
                  ? 'bg-gradient-to-r from-cyan-500/30 to-teal-500/20 text-cyan-300 border border-cyan-500/50 shadow-md shadow-cyan-950/50'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <span>Benchmark Results</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="space-y-8 glass-panel p-6 sm:p-8 rounded-3xl border border-slate-800">
        {activeTab === 'playground' ? (
          <>
            {/* Quick Sample Presets */}
            <SampleAttacks onSelectSample={handleSelectSample} />

            <div className="border-t border-slate-800/80 pt-6">
              {/* Input Form with Prompt & Document Modes */}
              <AnalyzerInput
                text={text}
                setText={setText}
                sourceType={sourceType}
                setSourceType={setSourceType}
                mode={mode}
                setMode={setMode}
                onAnalyze={handleAnalyze}
                isLoading={isLoading}
                error={error}
              />
            </div>

            {/* Pipeline Trace Visualizer & Result Card with Highlighting */}
            {result && (
              <div className="border-t border-slate-800/80 pt-6 space-y-6">
                <PipelineTrace result={result} />
                <ResultCard result={result} />
              </div>
            )}

            {/* Audit Logs Panel */}
            <div className="border-t border-slate-800/80 pt-6">
              <LogsPanel />
            </div>
          </>
        ) : (
          /* Benchmark Results Tab */
          <ResultsTab />
        )}
      </main>

      {/* Footer Info */}
      <footer className="mt-8 text-center text-xs text-slate-500 space-y-2">
        <div className="flex items-center justify-center gap-4 text-slate-400">
          <span className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-cyan-500" /> Multi-View Heuristics + ML Classifier
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Multi-Tier Defense (Allow / Isolate / Block)
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-teal-500" /> Output Validator
          </span>
        </div>
        <p>CAGE Security Suite • Context-Aware Guard for LLM Exploits v2.0</p>
      </footer>
    </div>
  );
}
