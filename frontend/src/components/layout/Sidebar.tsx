import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Network,
  Activity,
  GitCommit,
  GitFork,
  FlaskConical,
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Topology', path: '/topology', icon: Network },
  { name: 'Traffic & Metrics', path: '/traffic', icon: Activity },
  { name: 'Flow Tables', path: '/flows', icon: GitCommit },
  { name: 'Routing Decisions', path: '/routing', icon: GitFork },
  { name: 'Experiments', path: '/experiments', icon: FlaskConical },
];

export const Sidebar: React.FC = () => (
  <aside className="w-64 border-r border-cyber-border bg-[#0E1017]/90 flex flex-col p-4 shrink-0 min-h-[calc(100vh-4rem)]">
    <div className="mb-6 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
      Network Operations
    </div>
    <nav className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                isActive
                  ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-cyber-card'
              }`
            }
          >
            <Icon className="w-4 h-4 mr-3" />
            <span>{item.name}</span>
          </NavLink>
        );
      })}
    </nav>
  </aside>
);
