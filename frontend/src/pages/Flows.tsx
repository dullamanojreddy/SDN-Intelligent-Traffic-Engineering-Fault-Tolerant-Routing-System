import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { FlowEntry } from '../types/network';
import { GitCommit, Filter, RefreshCw } from 'lucide-react';

export const Flows: React.FC = () => {
  const [flows, setFlows] = useState<FlowEntry[]>([]);

  useEffect(() => {
    api.getFlows().then((res) => setFlows(res.data));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">OpenFlow Flow Tables</h2>
          <p className="text-sm text-slate-400">Inspected Table-0 rules installed across active Open vSwitches.</p>
        </div>
      </div>

      <div className="glass-panel rounded-2xl border border-cyber-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0E1017] border-b border-cyber-border text-slate-400 uppercase tracking-wider">
              <tr>
                <th className="p-4">Flow ID</th>
                <th className="p-4">Switch DPID</th>
                <th className="p-4">Priority</th>
                <th className="p-4">Match Filter</th>
                <th className="p-4">Action</th>
                <th className="p-4">Packet Count</th>
                <th className="p-4">Byte Count</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-border/60">
              {flows.map((f) => (
                <tr key={f.flow_id} className="hover:bg-cyber-card/60 transition">
                  <td className="p-4 font-bold text-purple-400">{f.flow_id}</td>
                  <td className="p-4 text-slate-300">{f.dpid.toUpperCase()}</td>
                  <td className="p-4 text-slate-300">{f.priority}</td>
                  <td className="p-4 text-slate-400">
                    {f.match.ipv4_src ? `src:${f.match.ipv4_src} dst:${f.match.ipv4_dst}` : 'Table-Miss'}
                  </td>
                  <td className="p-4 text-emerald-400">{f.instructions[0]?.actions.join(', ') || 'CONTROLLER'}</td>
                  <td className="p-4 text-slate-300">{f.packet_count.toLocaleString()}</td>
                  <td className="p-4 text-slate-300">{(f.byte_count / 1024 / 1024).toFixed(2)} MB</td>
                  <td className="p-4">
                    <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full text-[10px] font-bold">
                      {f.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
