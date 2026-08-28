import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AlertItem } from '../types/network';
import { AlertTriangle, ShieldCheck, Filter, Bell } from 'lucide-react';

export const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useEffect(() => {
    api.getAlerts().then((res) => setAlerts(res.data));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Security & Telemetry Alerts</h2>
          <p className="text-sm text-slate-400">Real-time notifications for threshold breaches, persistent congestion, and outages.</p>
        </div>
      </div>

      <div className="space-y-3">
        {alerts.map((al, idx) => (
          <div
            key={idx}
            className="glass-panel p-4 rounded-2xl border border-cyber-border flex items-start justify-between text-xs transition hover:border-purple-500/30"
          >
            <div className="flex items-start space-x-3">
              <div
                className={`p-2 rounded-xl mt-0.5 ${
                  al.severity === 'CRITICAL' || al.severity === 'ERROR'
                    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                    : al.severity === 'WARNING'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                }`}
              >
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center space-x-2 font-bold">
                  <span className="text-white">{al.type}</span>
                  <span className="text-slate-500 font-mono">[{al.source}]</span>
                </div>
                <p className="text-slate-300">{al.message}</p>
                <div className="text-[10px] text-slate-500 font-mono">{al.timestamp}</div>
              </div>
            </div>

            <span
              className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                al.status === 'RESOLVED'
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                  : 'text-amber-400 bg-amber-500/10 border-amber-500/20 animate-pulse'
              }`}
            >
              {al.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
