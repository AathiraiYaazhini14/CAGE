import React, { useState } from 'react';
import { X, Copy, Check, Key, Shield, AlertTriangle, Terminal, Sparkles } from 'lucide-react';
import { useToast } from './Toast';

export function CreateKeyModal({ isOpen, onClose, onKeyCreated }) {
  const { addToast } = useToast();

  const [step, setStep] = useState('form'); // 'form' | 'created'
  const [keyName, setKeyName] = useState('');
  const [environment, setEnvironment] = useState('production');
  const [scope, setScope] = useState('full');
  const [generatedKey, setGeneratedKey] = useState(null);
  const [copied, setCopied] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!keyName.trim() || submitting) {
      if (!keyName.trim()) addToast('Please provide a name for this API key', 'error');
      return;
    }

    setSubmitting(true);
    try {
      let createdRecord = null;
      if (onKeyCreated) {
        createdRecord = await onKeyCreated({
          name: keyName.trim(),
          environment: environment === 'production' ? 'Production' : 'Staging',
          scope: scope === 'full' ? 'Full Access (Scan + Demo)' : 'Read-Only (Stats & Logs)',
        });
      }

      if (!createdRecord) {
        // Fallback client generation if offline
        const prefix = environment === 'production' ? 'cage_live_' : 'cage_test_';
        const randomHex = Array.from({ length: 32 }, () =>
          Math.floor(Math.random() * 16).toString(16)
        ).join('');
        const fullKey = `${prefix}${randomHex}`;

        createdRecord = {
          id: `key_${Date.now()}`,
          name: keyName.trim(),
          prefix: `${fullKey.slice(0, 14)}••••••••••••${fullKey.slice(-4)}`,
          fullKey: fullKey,
          environment: environment === 'production' ? 'Production' : 'Staging',
          scope: scope === 'full' ? 'Full Access (Scan + Demo)' : 'Read-Only (Stats & Logs)',
          createdAt: new Date().toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
          }),
          status: 'Active',
          lastUsed: 'Never'
        };
      }

      setGeneratedKey(createdRecord);
      setStep('created');
      addToast(`API Key "${createdRecord.name}" created successfully`, 'success');
    } catch (err) {
      addToast(err.message || 'Failed to generate API key', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (!generatedKey) return;
    navigator.clipboard.writeText(generatedKey.fullKey);
    setCopied(true);
    addToast('API key copied to clipboard', 'info');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleResetAndClose = () => {
    setStep('form');
    setKeyName('');
    setEnvironment('production');
    setScope('full');
    setGeneratedKey(null);
    setCopied(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 sm:p-6 animate-fade-in">
      <div className="w-full max-w-lg panel-card overflow-hidden shadow-2xl border border-[#7C6CF0]/40 flex flex-col">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-[#232333] flex items-center justify-between bg-[#0A0A0F]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-[#7C6CF0]/20 border border-[#7C6CF0]/40 text-[#7C6CF0]">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                {step === 'form' ? 'Create New API Key' : 'API Key Generated'}
              </h3>
              <p className="text-[11px] text-[#64748B] font-mono mt-0.5">
                {step === 'form' ? 'Provision a client token for CAGE gateway' : 'Store this secret securely'}
              </p>
            </div>
          </div>
          <button
            onClick={handleResetAndClose}
            className="p-1 rounded-lg text-[#64748B] hover:text-white hover:bg-[#12121A] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 sm:p-6 space-y-4 bg-[#12121A]">
          {step === 'form' ? (
            <form onSubmit={handleGenerate} className="space-y-4">
              {/* Key Name Input */}
              <div>
                <label className="text-[11px] font-mono text-[#CBD5E1] uppercase tracking-wider block mb-1.5">
                  Key Name <span className="text-[#EF4444]">*</span>
                </label>
                <input
                  type="text"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  placeholder="e.g. Production LLM Gateway, Customer Support Bot"
                  autoFocus
                  required
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#0A0A0F] border border-[#232333] text-xs text-white placeholder-[#64748B] focus:border-[#7C6CF0] focus:ring-1 focus:ring-[#7C6CF0] outline-none font-sans"
                />
                <p className="text-[10px] text-[#64748B] font-mono mt-1">
                  A descriptive identifier to track this token in your audit records.
                </p>
              </div>

              {/* Environment Selection */}
              <div>
                <label className="text-[11px] font-mono text-[#CBD5E1] uppercase tracking-wider block mb-1.5">
                  Environment
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setEnvironment('production')}
                    className={`p-2.5 rounded-lg border text-left cursor-pointer transition-all ${environment === 'production'
                      ? 'bg-[#7C6CF0]/15 border-[#7C6CF0] text-white font-medium'
                      : 'bg-[#0A0A0F] border-[#232333] text-[#94A3B8] hover:text-white'
                      }`}
                  >
                    <div className="text-xs font-semibold">Production</div>
                    <div className="text-[10px] font-mono text-[#64748B] mt-0.5">prefix: cage_live_</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setEnvironment('staging')}
                    className={`p-2.5 rounded-lg border text-left cursor-pointer transition-all ${environment === 'staging'
                      ? 'bg-[#7C6CF0]/15 border-[#7C6CF0] text-white font-medium'
                      : 'bg-[#0A0A0F] border-[#232333] text-[#94A3B8] hover:text-white'
                      }`}
                  >
                    <div className="text-xs font-semibold">Staging / Test</div>
                    <div className="text-[10px] font-mono text-[#64748B] mt-0.5">prefix: cage_test_</div>
                  </button>
                </div>
              </div>

              {/* Permissions Scope */}
              <div>
                <label className="text-[11px] font-mono text-[#CBD5E1] uppercase tracking-wider block mb-1.5">
                  Permissions Scope
                </label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#0A0A0F] border border-[#232333] text-xs text-white focus:border-[#7C6CF0] outline-none font-sans cursor-pointer"
                >
                  <option value="full">Full Access (Prompt Scanning, RAG Demo & Telemetry)</option>
                  <option value="readonly">Read-Only Telemetry (Stats & Audit Logs Export)</option>
                </select>
              </div>

              {/* Actions Footer */}
              <div className="pt-3 border-t border-[#232333] flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={handleResetAndClose}
                  className="px-3.5 py-2 rounded-lg text-xs text-[#94A3B8] hover:text-white bg-[#0A0A0F] border border-[#232333] hover:border-[#64748B] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!keyName.trim() || submitting}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-[#7C6CF0] hover:bg-[#6857EB] disabled:opacity-40 disabled:cursor-not-allowed shadow-md transition-all cursor-pointer flex items-center gap-1.5"
                >
                  {submitting ? (
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5" />
                  )}
                  <span>{submitting ? 'Generating...' : 'Generate Key'}</span>
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4 animate-fade-in">
              {/* Security Alert Banner */}
              <div className="p-3 rounded-lg bg-[#F59E0B]/15 border border-[#F59E0B]/40 text-[#FCD34D] text-xs font-sans flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-[#F59E0B] shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <strong className="font-semibold text-white block">Copy your API key now</strong>
                  <p className="text-[11px] text-[#FCD34D]/90 leading-relaxed">
                    This key will not be shown in full again. Store it in a secure password vault or environment secret manager.
                  </p>
                </div>
              </div>

              {/* Key Box with Copy Button */}
              <div>
                <label className="text-[10px] font-mono text-[#64748B] uppercase tracking-wider block mb-1">
                  Secret Key ({generatedKey.name})
                </label>
                <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#232333] flex items-center justify-between gap-2">
                  <code className="text-xs font-mono text-[#10B981] break-all select-all font-semibold">
                    {generatedKey.fullKey}
                  </code>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="shrink-0 p-2 rounded-md bg-[#12121A] hover:bg-[#232333] border border-[#232333] text-[#7C6CF0] hover:text-white transition-all cursor-pointer flex items-center gap-1.5 text-xs font-mono"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              {/* Quick Curl Snippet */}
              <div>
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-[#64748B] uppercase tracking-wider mb-1">
                  <Terminal className="w-3 h-3 text-[#7C6CF0]" />
                  <span>Integration Example</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#0A0A0F] border border-[#232333] font-mono text-[10px] text-[#CBD5E1] overflow-x-auto leading-relaxed">
                  <span className="text-[#64748B]"># Test prompt inspection via curl</span>
                  <br />
                  <span className="text-[#7C6CF0]">curl</span> -X POST http://localhost:8000/scan \
                  <br />
                  &nbsp;&nbsp;-H <span className="text-[#10B981]">"Authorization: Bearer {generatedKey.fullKey.slice(0, 18)}..."</span> \
                  <br />
                  &nbsp;&nbsp;-H <span className="text-[#94A3B8]">"Content-Type: application/json"</span> \
                  <br />
                  &nbsp;&nbsp;-d <span className="text-[#FCD34D]">'{"{\"text\": \"Inspect this input\"}"}'</span>
                </div>
              </div>

              {/* Modal Finish Footer */}
              <div className="pt-3 border-t border-[#232333] flex items-center justify-between">
                <span className="text-[10px] font-mono text-[#64748B]">
                  Saved to "Keys Created" tab
                </span>
                <button
                  type="button"
                  onClick={handleResetAndClose}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-white bg-[#7C6CF0] hover:bg-[#6857EB] transition-all cursor-pointer shadow-md"
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

