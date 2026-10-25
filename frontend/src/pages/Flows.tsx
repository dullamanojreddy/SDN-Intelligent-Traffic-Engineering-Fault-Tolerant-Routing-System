import React, { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { FlowEntry } from '../types/network';

export const Flows: React.FC = () => {
  const [flows, setFlows] = useState<FlowEntry[]>([]);
  const [switchId, setSwitchId] = useState('all');

  const refresh = () => api.getFlows().then((res) => setFlows(res.data)).catch(console.error);
  useEffect(() => { refresh(); }, []);

  const visibleFlows = switchId === 'all' ? flows : flows.filter((flow) => flow.dpid === switchId);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white">Flow Tables</h2>
          <p className="text-sm text-slate-400">OpenFlow entries exposed by the backend.</p>
        </div>
        <div className="flex gap-2">
          <select value={switchId} onChange={(e) => setSwitchId(e.target.value)} className="control">
            <option value="all">All switches</option>
            {Array.from({ length: 7 }, (_, i) => <option key={i} value={`s${i + 1}`}>s{i + 1}</option>)}
          </select>
          <button onClick={refresh} className="button-secondary"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>
      </div>
      <div className="glass-panel rounded-2xl border border-cyber-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0E1017] text-slate-400 uppercase tracking-wider">
              <tr><th className="p-4">Switch</th><th className="p-4">Destination IP</th><th className="p-4">Output port</th><th className="p-4">Priority</th><th className="p-4">Packets</th><th className="p-4">Bytes</th></tr>
            </thead>
            <tbody className="divide-y divide-cyber-border/60">
              {visibleFlows.map((flow) => (
                <tr key={flow.flow_id}>
                  <td className="p-4 font-mono text-purple-300">{flow.dpid}</td>
                  <td className="p-4 font-mono text-slate-300">{flow.match.ipv4_dst ?? 'N/A'}</td>
                  <td className="p-4 text-emerald-400">{flow.instructions[0]?.actions.join(', ') || 'N/A'}</td>
                  <td className="p-4 text-slate-300">{flow.priority}</td>
                  <td className="p-4 text-slate-300">{flow.packet_count.toLocaleString()}</td>
                  <td className="p-4 text-slate-300">{flow.byte_count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!visibleFlows.length && <p className="p-4 text-sm text-slate-500">N/A — no flow entries available for this switch.</p>}
      </div>
    </div>
  );
};
