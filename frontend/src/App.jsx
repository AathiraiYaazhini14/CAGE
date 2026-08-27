import React, { useState } from 'react';
import { ShieldCheck, Lock, Cpu, Radio } from 'lucide-react';
import AnalyzerInput from './components/AnalyzerInput';
import SampleAttacks from './components/SampleAttacks';
import ResultCard from './components/ResultCard';

export default function App() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async (promptText) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: promptText }),
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

  const handleSelectSample = (sampleText) => {
    setText(sampleText);
    setError(null);
  };

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto flex flex-col justify-between">
      {/* Header Section */}
      <header className="space-y-6 text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/70 border border-cyan-700/50 text-cyan-400 text-xs font-mono tracking-wide shadow-lg shadow-cyan-950/40">
          <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
          <span>Real-time LLM Prompt Firewall</span>
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
      </header>

      {/* Main Content Area */}
      <main className="space-y-8 glass-panel p-6 sm:p-8 rounded-3xl border border-slate-800">
        {/* Quick Sample Presets */}
        <SampleAttacks onSelectSample={handleSelectSample} />

        <div className="border-t border-slate-800/80 pt-6">
          {/* Input Form */}
          <AnalyzerInput
            text={text}
            setText={setText}
            onAnalyze={handleAnalyze}
            isLoading={isLoading}
            error={error}
          />
        </div>

        {/* Result Card Output */}
        {result && (
          <div className="border-t border-slate-800/80 pt-6">
            <ResultCard result={result} />
          </div>
        )}
      </main>

      {/* Footer Info */}
      <footer className="mt-12 text-center text-xs text-slate-500 space-y-2">
        <div className="flex items-center justify-center gap-4 text-slate-400">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-cyan-500" /> Rule-Based Heuristics
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-teal-500" /> Fast & Deterministic
          </span>
        </div>
        <p>College Mini-Project Demo • CAGE Security Suite</p>
      </footer>
    </div>
  );
}
