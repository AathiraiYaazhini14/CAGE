import React from 'react';
import { LatticeShieldIcon } from './LatticeShield';
import { useAuth } from '../context/AuthContext';
import { LayoutDashboard, ShieldAlert, BotMessageSquare, LogOut, Terminal, User, Key } from 'lucide-react';

export function Sidebar({ currentTab, onSelectTab, mobileOpen, onCloseMobile }) {
  const { user, logout } = useAuth();

  const navItems = [
    {
      id: 'home',
      label: 'Home',
      icon: LayoutDashboard,
      description: 'Operations console & live activity',
    },
    {
      id: 'analysis',
      label: 'Analysis',
      icon: ShieldAlert,
      description: 'Audit logs, heatmaps & attack origins',
    },
    {
      id: 'demo',
      label: 'Demo',
      icon: BotMessageSquare,
      description: 'Interactive RAG defense playground',
    },
    {
      id: 'keys',
      label: 'Keys Created',
      icon: Key,
      description: 'Manage generated client API keys',
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden"
        />
      )}

      {/* Main Sidebar */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-[#0A0A0F] border-r border-[#232333] flex flex-col justify-between transition-transform duration-300 ease-in-out md:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Logo & App Header */}
        <div>
          <div className="h-16 px-6 flex items-center gap-3 border-b border-[#232333]/80">
            <LatticeShieldIcon className="w-6 h-6" glowing />
            <div className="flex flex-col">
              <span className="font-bold tracking-wider text-white text-base leading-none">CAGE</span>
              <span className="text-[10px] font-mono text-[#7C6CF0] tracking-widest mt-0.5">
                SEC-OPS CONSOLE
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            <div className="px-3 pb-2 text-[10px] font-mono text-[#64748B] uppercase tracking-wider">
              Navigation
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelectTab(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all text-left cursor-pointer ${
                    isActive
                      ? 'bg-[#12121A] text-white border border-[#7C6CF0]/40 glow-violet-subtle'
                      : 'text-[#94A3B8] hover:text-white hover:bg-[#12121A]/50 border border-transparent'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive ? 'text-[#7C6CF0]' : 'text-[#64748B]'
                    }`}
                  />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom User Profile & Logout */}
        <div className="p-4 border-t border-[#232333]/80">
          <div className="panel-card p-3 flex items-center gap-3 bg-[#12121A]/70">
            <div className="w-8 h-8 rounded-lg bg-[#232333] border border-[#7C6CF0]/30 flex items-center justify-center text-xs font-mono text-[#7C6CF0] shrink-0 font-bold">
              {user?.name ? user.name.slice(0, 2).toUpperCase() : 'AU'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">
                {user?.name || 'Security Analyst'}
              </p>
              <p className="text-[11px] font-mono text-[#94A3B8] truncate">
                {user?.email || 'analyst@cage.dev'}
              </p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="p-1.5 rounded-lg text-[#64748B] hover:text-[#EF4444] hover:bg-[#232333]/50 transition-colors shrink-0 cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

