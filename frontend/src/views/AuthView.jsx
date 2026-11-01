import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import { LatticeShieldIcon, GlowingLatticeGraphic } from '../components/LatticeShield';
import { ShieldCheck, Lock, Eye, EyeOff, Sparkles, Layers, ArrowRight } from 'lucide-react';

export function AuthView() {
  const { login, signup, loginAsDemo } = useAuth();
  const { addToast } = useToast();

  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  // Form validation state
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  // Password strength calculation
  const calculateStrength = (pwd) => {
    if (!pwd) return { score: 0, label: 'None', color: 'bg-transparent' };
    let score = 0;
    if (pwd.length >= 8) score += 1;
    if (pwd.length >= 12) score += 1;
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score += 1;
    if (/\d/.test(pwd)) score += 1;
    if (/[^a-zA-Z0-9]/.test(pwd)) score += 1;

    if (score <= 1) return { score: 1, label: 'Weak', color: 'bg-[#EF4444]' };
    if (score <= 3) return { score: 2, label: 'Medium', color: 'bg-[#F59E0B]' };
    return { score: 3, label: 'Strong', color: 'bg-[#7C6CF0]' };
  };

  const strength = calculateStrength(password);

  const validateEmail = (val) => {
    const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    if (!val) {
      setEmailError('Email is required');
      return false;
    }
    if (!valid) {
      setEmailError('Please enter a valid email address');
      return false;
    }
    setEmailError('');
    return true;
  };

  const validatePassword = (val) => {
    if (!val) {
      setPasswordError('Password is required');
      return false;
    }
    if (val.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return false;
    }
    setPasswordError('');
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const isEmailValid = validateEmail(email);
    const isPwdValid = validatePassword(password);

    if (!isEmailValid || !isPwdValid) return;

    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
        addToast('Signed in successfully', 'success');
      } else {
        if (!name.trim()) {
          addToast('Full name is required for registration', 'error');
          setLoading(false);
          return;
        }
        await signup(name, email, password);
        addToast('Account created successfully', 'success');
      }
    } catch (err) {
      addToast(err.message || 'Authentication failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setLoading(true);
    try {
      await loginAsDemo();
      addToast('Authenticated with Demo Account', 'success');
    } catch (err) {
      addToast(err.message || 'Demo login failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#0A0A0F] flex flex-col md:flex-row items-stretch text-[#F1F5F9]">
      {/* LEFT COLUMN: HERO & BRANDING */}
      <div className="md:w-1/2 p-8 md:p-16 flex flex-col justify-between border-b md:border-b-0 md:border-r border-[#232333] relative overflow-hidden bg-gradient-to-br from-[#0A0A0F] via-[#12121A]/70 to-[#0A0A0F]">
        {/* Subtle grid background */}
        <div className="absolute inset-0 lattice-grid opacity-30 pointer-events-none" />

        {/* Brand Header */}
        <div className="relative z-10 flex items-center gap-3">
          <LatticeShieldIcon className="w-8 h-8" glowing />
          <span className="text-xl font-bold tracking-wider text-white">CAGE</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-[#232333] text-[#7C6CF0] font-mono border border-[#7C6CF0]/30">
            v2.0 CONSOLE
          </span>
        </div>

        {/* Center Graphic & Tagline */}
        <div className="relative z-10 my-12 flex flex-col items-center md:items-start">
          <div className="self-center mb-8">
            <GlowingLatticeGraphic />
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-white leading-tight text-center md:text-left">
            Every prompt inspected. <br />
            <span className="text-[#7C6CF0]">Every injection caged.</span>
          </h1>

          <p className="mt-4 text-base text-[#94A3B8] max-w-lg leading-relaxed text-center md:text-left font-sans">
            Autonomous multi-tier defense proxy neutralizing prompt injections,
            jailbreaks, and indirect document smuggling across upstream LLMs and RAG pipelines.
          </p>

          {/* Three Feature Lines */}
          <div className="mt-8 space-y-4 w-full max-w-md">
            <div className="flex items-start gap-3">
              <div className="p-1.5 rounded-lg bg-[#12121A] border border-[#232333] text-[#7C6CF0] mt-0.5 shrink-0">
                <Layers className="w-4 h-4" />
              </div>
              <p className="text-sm text-[#CBD5E1]">
                <strong className="text-white font-medium">Multi-Tier Feature Scoring:</strong> Multi-view normalization, fine-grained chunk sliding windows, and calibrated logistic stacking.
              </p>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-1.5 rounded-lg bg-[#12121A] border border-[#232333] text-[#7C6CF0] mt-0.5 shrink-0">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <p className="text-sm text-[#CBD5E1]">
                <strong className="text-white font-medium">Active Context Quarantine:</strong> Borderline indirect attacks are isolated in untrusted delimiters; critical threats are blocked before LLM execution.
              </p>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-1.5 rounded-lg bg-[#12121A] border border-[#232333] text-[#7C6CF0] mt-0.5 shrink-0">
                <Sparkles className="w-4 h-4" />
              </div>
              <p className="text-sm text-[#CBD5E1]">
                <strong className="text-white font-medium">Autonomous Output Validation:</strong> Post-generation leak scanning prevents verbatim prompt leakage and canary compromise.
              </p>
            </div>
          </div>
        </div>

        {/* Footer Info */}
        <div className="relative z-10 text-xs text-[#64748B] flex items-center justify-between border-t border-[#232333]/60 pt-4 font-mono">
          <span>SEC-OPS RUNTIME KERNEL</span>
          <span>ENTERPRISE GATEWAY</span>
        </div>
      </div>

      {/* RIGHT COLUMN: AUTH CARD */}
      <div className="md:w-1/2 p-6 sm:p-12 md:p-16 flex items-center justify-center relative">
        <div className="w-full max-w-md panel-card p-6 sm:p-8 relative z-10 shadow-2xl">
          {/* Auth Tab Switcher */}
          <div className="flex items-center p-1 rounded-lg bg-[#0A0A0F] border border-[#232333] mb-6">
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setEmailError('');
                setPasswordError('');
              }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'login'
                ? 'bg-[#12121A] text-white shadow border border-[#232333]'
                : 'text-[#94A3B8] hover:text-white'
                }`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('signup');
                setEmailError('');
                setPasswordError('');
              }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'signup'
                ? 'bg-[#12121A] text-white shadow border border-[#232333]'
                : 'text-[#94A3B8] hover:text-white'
                }`}
            >
              Create account
            </button>
          </div>

          <h2 className="text-xl font-bold text-white mb-2 font-sans">
            {mode === 'login' ? 'Access Security Console' : 'Initialize Enterprise Profile'}
          </h2>
          <p className="text-xs text-[#94A3B8] mb-6">
            {mode === 'login'
              ? 'Enter credentials to manage inspection feeds and threat analytics.'
              : 'Register to monitor LLM interactions and indirect payload detections.'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-medium text-[#94A3B8] uppercase tracking-wider mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Security Lead"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#0A0A0F] border border-[#232333] text-sm text-white placeholder-[#64748B] focus:border-[#7C6CF0] focus:ring-1 focus:ring-[#7C6CF0] transition-colors outline-none"
                />
              </div>
            )}

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-medium text-[#94A3B8] uppercase tracking-wider">
                  Work Email
                </label>
                {emailError && <span className="text-xs text-[#EF4444]">{emailError}</span>}
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailError) validateEmail(e.target.value);
                }}
                onBlur={(e) => validateEmail(e.target.value)}
                placeholder="analyst@cage.dev"
                className={`w-full px-3.5 py-2.5 rounded-lg bg-[#0A0A0F] border text-sm text-white placeholder-[#64748B] transition-colors outline-none font-mono ${emailError
                  ? 'border-[#EF4444] focus:ring-1 focus:ring-[#EF4444]'
                  : 'border-[#232333] focus:border-[#7C6CF0] focus:ring-1 focus:ring-[#7C6CF0]'
                  }`}
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-medium text-[#94A3B8] uppercase tracking-wider">
                  Password
                </label>
                {passwordError && <span className="text-xs text-[#EF4444]">{passwordError}</span>}
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (passwordError) validatePassword(e.target.value);
                  }}
                  onBlur={(e) => validatePassword(e.target.value)}
                  placeholder="Min 8 characters"
                  className={`w-full px-3.5 py-2.5 pr-10 rounded-lg bg-[#0A0A0F] border text-sm text-white placeholder-[#64748B] transition-colors outline-none font-mono ${passwordError
                    ? 'border-[#EF4444] focus:ring-1 focus:ring-[#EF4444]'
                    : 'border-[#232333] focus:border-[#7C6CF0] focus:ring-1 focus:ring-[#7C6CF0]'
                    }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              {/* Password Strength Meter (Shown on signup or input) */}
              {password.length > 0 && (
                <div className="mt-2.5">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-[#64748B]">Strength:</span>
                    <span className="font-mono text-xs font-medium text-white">{strength.label}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-1.5 h-1.5 w-full bg-[#0A0A0F] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-300 ${strength.score >= 1 ? strength.color : 'bg-transparent'}`} />
                    <div className={`h-full rounded-full transition-all duration-300 ${strength.score >= 2 ? strength.color : 'bg-transparent'}`} />
                    <div className={`h-full rounded-full transition-all duration-300 ${strength.score >= 3 ? strength.color : 'bg-transparent'}`} />
                  </div>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 rounded-lg bg-[#7C6CF0] hover:bg-[#6857EB] text-white font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-[#7C6CF0]/25 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <span>{mode === 'login' ? 'Authorize Session' : 'Create Account'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#232333]" />
            </div>
            <span className="relative px-3 bg-[#12121A] text-xs font-mono text-[#64748B] uppercase">
              Or Instant Preview
            </span>
          </div>

          {/* Continue as Demo User Button */}
          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-[#0A0A0F] hover:bg-[#1A1A26] border border-[#232333] hover:border-[#7C6CF0]/50 text-[#F1F5F9] font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2.5 cursor-pointer"
          >
            <Lock className="w-4 h-4 text-[#7C6CF0]" />
            <span>Continue as demo user</span>
            <span className="ml-auto text-xs px-2 py-0.5 rounded bg-[#232333] text-[#94A3B8] font-mono">
              demo@cage.dev
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

