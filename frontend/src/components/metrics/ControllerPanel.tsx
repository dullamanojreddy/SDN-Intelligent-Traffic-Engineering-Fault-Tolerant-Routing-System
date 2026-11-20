import React, { useEffect, useState } from 'react';
import { Cpu } from 'lucide-react';
import { api } from '../../services/api';
import { ControllerStatus } from '../../types/network';

/** Primary/standby controller health, OpenFlow role and recent failover events. */
export const ControllerPanel: React.FC = () => {
  const [status, setStatus] = useState<ControllerStatus | null>(null);

  useEffect(() => {
    const load = () => api.getControllerStatus().then((res) => setStatus(res.data)).catch(() => setStatus(null));
    load();
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-3">
      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
        <Cpu className="w-3.5 h-3.5 text-purple-400" />
        <span>Controllers</span>
        {status && (
          <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded border ${status.status === 'UP' ? 'text-emerald-300 border-emerald-500/30' : 'text-red-300 border-red-500/40'}`}>
            {status.status}
          </span>
        )}
      </h4>
      {!status && <p className="text-xs text-slate-500">Backend unreachable.</p>}
      {status?.endpoints.map((ep) => (
        <div key={ep.url} className="p-3 rounded-xl bg-[#0E1017] border border-cyber-border/80 text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-200">{ep.role === 'primary' ? 'Primary' : 'Standby'}</span>
            <span className={ep.healthy ? 'text-emerald-400' : ep.healthy === false ? 'text-red-400' : 'text-slate-500'}>
              {ep.healthy ? 'healthy' : ep.healthy === false ? 'unreachable' : 'unknown'}
            </span>
          </div>
          <div className="font-mono text-[11px] text-slate-400">{ep.url.replace('http://', '')}</div>
          <div className="font-mono text-[11px] text-slate-400">
            OpenFlow role: <b className={ep.of_role === 'MASTER' ? 'text-amber-300' : 'text-slate-300'}>{ep.of_role ?? '—'}</b>
            {ep.active && <span className="text-purple-300 ml-3">● ACTIVE (management)</span>}
          </div>
        </div>
      ))}
      {status && (
        <div className="text-[11px] text-slate-400 font-mono">
          failovers: {status.failover_count} · outages: {status.outage_count}
          {status.pending_sync ? ' · edits pending sync' : ''}
        </div>
      )}
      <div className="space-y-1 max-h-28 overflow-y-auto">
        {status?.history.slice().reverse().slice(0, 4).map((e, i) => (
          <p key={i} className="text-[10px] text-slate-500"><b className="text-slate-300">{e.type}</b> {e.timestamp.slice(11, 19)}</p>
        ))}
      </div>
    </div>
  );
};
