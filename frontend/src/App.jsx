import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './components/Toast';
import { api } from './api';
import { AuthView } from './views/AuthView';
import { HomeView } from './views/HomeView';
import { AnalysisView } from './views/AnalysisView';
import { DemoView } from './views/DemoView';
import { ApiKeysView, DEFAULT_INITIAL_KEYS } from './views/ApiKeysView';
import { Sidebar } from './components/Sidebar';
import { CreateKeyModal } from './components/CreateKeyModal';
import { LatticeShieldIcon } from './components/LatticeShield';
import { Menu, X, ShieldAlert, Cpu, Key } from 'lucide-react';

function MainApp() {
  const { isAuthenticated, loading, user } = useAuth();
  const [currentTab, setCurrentTab] = useState('home'); // 'home' | 'analysis' | 'demo' | 'keys'
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [createKeyModalOpen, setCreateKeyModalOpen] = useState(false);

  // Account-scoped API Keys store
  const [keys, setKeys] = useState([]);
  const [keysLoading, setKeysLoading] = useState(false);

  // Sync keys whenever active user changes
  useEffect(() => {
    if (!user) {
      setKeys([]);
      return;
    }

    const userKeyStorageId = `cage_api_keys_${user.id || user.email}`;

    // 1. Initial hydration from user-specific cache
    try {
      const cached = localStorage.getItem(userKeyStorageId);
      if (cached) {
        setKeys(JSON.parse(cached));
      } else if (user.email === 'demo@cage.dev') {
        setKeys(DEFAULT_INITIAL_KEYS);
      } else {
        setKeys([]);
      }
    } catch (_) {
      setKeys([]);
    }

    // 2. Fetch fresh account-isolated keys from backend
    let isCancelled = false;
    setKeysLoading(true);
    api.keys
      .list()
      .then((serverKeys) => {
        if (!isCancelled && Array.isArray(serverKeys)) {
          setKeys(serverKeys);
          try {
            localStorage.setItem(userKeyStorageId, JSON.stringify(serverKeys));
          } catch (_) {}
        }
      })
      .catch((err) => {
        console.warn('[CAGE API Keys] Offline/cache fallback:', err.message);
      })
      .finally(() => {
        if (!isCancelled) setKeysLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [user]);

  const handleKeyCreated = async (keyPayload) => {
    if (!user) return null;
    const userKeyStorageId = `cage_api_keys_${user.id || user.email}`;

    try {
      const created = await api.keys.create(keyPayload);
      setKeys((prev) => {
        const next = [created, ...prev];
        try {
          localStorage.setItem(userKeyStorageId, JSON.stringify(next));
        } catch (_) {}
        return next;
      });
      return created;
    } catch (err) {
      console.warn('[CAGE API Keys] Fallback to client generation:', err.message);
      const prefix = keyPayload.environment === 'Production' ? 'cage_live_' : 'cage_test_';
      const randomHex = Array.from({ length: 32 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join('');
      const fullKey = `${prefix}${randomHex}`;
      const localKey = {
        id: `key_${Date.now()}`,
        name: keyPayload.name,
        prefix: `${fullKey.slice(0, 14)}••••••••••••${fullKey.slice(-4)}`,
        fullKey: fullKey,
        environment: keyPayload.environment,
        scope: keyPayload.scope,
        createdAt: new Date().toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        }),
        status: 'Active',
        lastUsed: 'Never'
      };
      setKeys((prev) => {
        const next = [localKey, ...prev];
        try {
          localStorage.setItem(userKeyStorageId, JSON.stringify(next));
        } catch (_) {}
        return next;
      });
      return localKey;
    }
  };

  const handleRevokeKey = async (keyId) => {
    if (!user) return;
    const userKeyStorageId = `cage_api_keys_${user.id || user.email}`;

    try {
      await api.keys.revoke(keyId);
    } catch (err) {
      console.warn('[CAGE API Keys] Offline revoke fallback:', err.message);
    }

    setKeys((prev) => {
      const next = prev.filter((k) => k.id !== keyId);
      try {
        localStorage.setItem(userKeyStorageId, JSON.stringify(next));
      } catch (_) {}
      return next;
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen w-full bg-[#0A0A0F] flex flex-col items-center justify-center text-white">
        <LatticeShieldIcon className="w-12 h-12 mb-4" glowing />
        <div className="flex items-center gap-2 font-mono text-xs text-[#7C6CF0] tracking-widest uppercase">
          <div className="w-3 h-3 border-2 border-[#7C6CF0] border-t-transparent rounded-full animate-spin" />
          <span>Verifying Security Session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthView />;
  }

  return (
    <div className="min-h-screen w-full bg-[#0A0A0F] text-[#F1F5F9] flex">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 md:pl-64 flex flex-col min-h-screen">
        {/* Top Navbar / Mobile Header */}
        <header className="h-16 border-b border-[#232333] px-6 flex items-center justify-between bg-[#0A0A0F]/80 backdrop-blur-md sticky top-0 z-30">
          <div className="flex items-center gap-3">
            {/* Mobile Hamburger Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-lg bg-[#12121A] border border-[#232333] text-[#94A3B8] hover:text-white md:hidden cursor-pointer"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Breadcrumb / Title */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-[#64748B] uppercase tracking-wider hidden sm:inline">
                CAGE CONSOLE
              </span>
              <span className="text-xs font-mono text-[#64748B] hidden sm:inline">/</span>
              <span className="text-sm font-semibold text-white capitalize font-mono">
                {currentTab === 'home' && 'Security Operations Dashboard'}
                {currentTab === 'analysis' && 'Incident Telemetry & Audit Analysis'}
                {currentTab === 'demo' && 'Interactive RAG Defense Playground'}
                {currentTab === 'keys' && 'Keys Created & API Access Tokens'}
              </span>
            </div>
          </div>

          {/* Header Right Actions */}
          <div className="flex items-center gap-3">
            {/* Quick Engine Status Indicator */}
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-full bg-[#12121A] border border-[#232333] text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
              <span className="text-[#CBD5E1] text-[11px]">DEFENSE ACTIVE</span>
            </div>

            {/* GET API KEY Segment / Button */}
            <button
              type="button"
              onClick={() => setCreateKeyModalOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-[#7C6CF0] hover:bg-[#6857EB] text-white text-xs font-semibold shadow-md transition-all flex items-center gap-1.5 cursor-pointer glow-violet-subtle border border-[#7C6CF0]/40"
            >
              <Key className="w-3.5 h-3.5" />
              <span>Get API Key</span>
            </button>
          </div>
        </header>

        {/* View Viewport */}
        <main className="flex-1 p-6 sm:p-8 max-w-7xl w-full mx-auto">
          {currentTab === 'home' && <HomeView onNavigate={setCurrentTab} />}
          {currentTab === 'analysis' && <AnalysisView />}
          {currentTab === 'demo' && <DemoView />}
          {currentTab === 'keys' && (
            <ApiKeysView
              onOpenCreateModal={() => setCreateKeyModalOpen(true)}
              keys={keys}
              onRevokeKey={handleRevokeKey}
              user={user}
              loading={keysLoading}
            />
          )}
        </main>
      </div>

      {/* Create Key Modal */}
      <CreateKeyModal
        isOpen={createKeyModalOpen}
        onClose={() => setCreateKeyModalOpen(false)}
        onKeyCreated={handleKeyCreated}
      />
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <MainApp />
      </AuthProvider>
    </ToastProvider>
  );
}
