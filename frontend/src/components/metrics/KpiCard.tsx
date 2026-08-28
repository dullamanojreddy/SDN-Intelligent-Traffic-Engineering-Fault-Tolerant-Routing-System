import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'purple' | 'emerald' | 'amber' | 'red' | 'indigo';
  change?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'purple',
  change
}) => {
  const colorMap = {
    purple: {
      border: 'border-purple-500/20 hover:border-purple-500/40',
      iconBg: 'bg-purple-500/10 text-purple-400',
      badge: 'text-purple-400 bg-purple-500/10 border-purple-500/20'
    },
    emerald: {
      border: 'border-emerald-500/20 hover:border-emerald-500/40',
      iconBg: 'bg-emerald-500/10 text-emerald-400',
      badge: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    },
    amber: {
      border: 'border-amber-500/20 hover:border-amber-500/40',
      iconBg: 'bg-amber-500/10 text-amber-400',
      badge: 'text-amber-400 bg-amber-500/10 border-amber-500/20'
    },
    red: {
      border: 'border-red-500/20 hover:border-red-500/40',
      iconBg: 'bg-red-500/10 text-red-400',
      badge: 'text-red-400 bg-red-500/10 border-red-500/20'
    },
    indigo: {
      border: 'border-indigo-500/20 hover:border-indigo-500/40',
      iconBg: 'bg-indigo-500/10 text-indigo-400',
      badge: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20'
    }
  };

  const scheme = colorMap[color];

  return (
    <div className={`glass-panel p-5 rounded-2xl border transition-all duration-200 ${scheme.border}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</span>
        <div className={`p-2.5 rounded-xl ${scheme.iconBg}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <div className="text-2xl font-extrabold text-white font-mono tracking-tight">{value}</div>
        {change && (
          <span className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded-full border ${scheme.badge}`}>
            {change}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-1 text-[11px] text-slate-500">{subtitle}</p>}
    </div>
  );
};
