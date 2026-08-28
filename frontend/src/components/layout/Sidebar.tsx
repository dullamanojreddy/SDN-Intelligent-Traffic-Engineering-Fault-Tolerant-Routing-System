import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Network,
  Activity,
  GitCommit,
  GitFork,
  AlertTriangle,
  FlaskConical,
  Settings,
  PlusCircle,
  Zap
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Topology', path: '/topology', icon: Network },
  { name: 'Traffic & Metrics', path: '/traffic', icon: Activity },
  { name: 'Flow Tables', path: '/flows', icon: GitCommit },
  { name: 'Routing Decisions', path: '/routing', icon: GitFork },
  { name: 'Alerts', path: '/alerts', icon: AlertTriangle, badge: '2' },
  { name: 'Experiments', path: '/experiments', icon: FlaskConical },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-cyber-border bg-[#0E1017]/90 flex flex-col justify-between p-4 shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        {/* Quick Action Button */}
        <button className="w-full bg-gradient-to-r from-purple-600 via-purple-700 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium py-2.5 px-4 rounded-xl shadow-lg shadow-purple-600/25 flex items-center justify-center space-x-2 transition duration-200 text-sm">
          <PlusCircle className="w-4 h-4" />
          <span>New Experiment</span>
        </button>

        {/* Navigation links */}
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition duration-150 ${
                    isActive
                      ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30 shadow-inner'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-cyber-card'
                  }`
                }
              >
                <div className="flex items-center space-x-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="bg-purple-500/20 border border-purple-500/40 text-purple-300 text-[11px] font-mono font-bold px-2 py-0.5 rounded-full">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Pro / Engine Card */}
      <div className="p-4 rounded-2xl bg-gradient-to-b from-purple-950/40 to-cyber-card border border-purple-500/20 text-center space-y-2">
        <div className="w-8 h-8 mx-auto rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400">
          <Zap className="w-4 h-4" />
        </div>
        <div className="text-xs font-semibold text-slate-200">SDN Intelligence</div>
        <div className="text-[11px] text-slate-400">Dijkstra dynamic cost recomputation is active.</div>
      </div>
    </aside>
  );
};
