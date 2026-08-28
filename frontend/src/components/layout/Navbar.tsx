import React from 'react';
import { Shield, Activity, Bell, Wifi, Sun, Moon, Sparkles } from 'lucide-react';
import { SystemStatus } from '../../types/network';

interface NavbarProps {
  status?: SystemStatus | null;
}

export const Navbar: React.FC<NavbarProps> = ({ status }) => {
  return (
    <header className="h-16 border-b border-cyber-border bg-[#0B0C10]/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
          <Activity className="w-5 h-5 text-white animate-pulse" />
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-purple-300 bg-clip-text text-transparent">
            SDN-ITE Operations
          </h1>
          <p className="text-[11px] text-slate-400 font-mono">Intelligent Traffic Engineering & Failover</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Status Indicator Badges */}
        <div className="flex items-center space-x-2 bg-cyber-card border border-cyber-border px-3 py-1.5 rounded-full text-xs font-mono">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-slate-300">OpenFlow 1.3:</span>
          <span className="text-emerald-400 font-semibold">PORT 6653</span>
        </div>

        <div className="flex items-center space-x-2 bg-purple-950/40 border border-purple-500/30 px-3.5 py-1.5 rounded-full text-xs font-medium text-purple-300 shadow-sm shadow-purple-900/50">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span>SDN Engine: Active</span>
        </div>

        <div className="h-4 w-px bg-cyber-border mx-1" />

        {/* Action icons */}
        <button
          aria-label="Notifications"
          className="relative p-2 rounded-lg text-slate-400 hover:text-white hover:bg-cyber-card border border-transparent hover:border-cyber-border transition"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-purple-500" />
        </button>

        {/* User / Profile Avatar */}
        <div className="flex items-center space-x-2.5 pl-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white shadow-md">
            OP
          </div>
          <div className="hidden md:block text-left">
            <div className="text-xs font-medium text-slate-200">Network Admin</div>
            <div className="text-[10px] text-slate-500 font-mono">admin@sdn-ite.local</div>
          </div>
        </div>
      </div>
    </header>
  );
};
