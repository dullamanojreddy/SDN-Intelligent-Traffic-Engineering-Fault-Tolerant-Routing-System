import React from 'react';
import { Activity } from 'lucide-react';
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

      </div>
    </header>
  );
};
