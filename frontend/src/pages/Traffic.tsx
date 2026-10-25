import React, { useEffect, useMemo, useState } from 'react';
import { Activity, RefreshCw } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { api } from '../services/api';
import { LinkEdge, NetworkMetrics, TopologyData } from '../types/network';

export const Traffic: React.FC = () => {
  const [metrics, setMetrics] = useState<NetworkMetrics | null>(null);
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [history, setHistory] = useState<{ time: string; utilization: number }[]>([]);

  const refresh = async () => {
    const [metricsRes, topologyRes] = await Promise.all([api.getMetrics(), api.getTopology()]);
    setMetrics(metricsRes.data);
    setTopology(topologyRes.data);
    setHistory((current) => [
      ...current.slice(-11),
      { time: new Date(metricsRes.data.timestamp).toLocaleTimeString(), utilization: metricsRes.data.avg_utilization_pct },
    ]);
  };

  useEffect(() => {
    refresh().catch(console.error);
    const interval = setInterval(() => refresh().catch(console.error), 3000);
    return () => clearInterval(interval);
  }, []);

  const links = useMemo(() => topology?.links ?? [], [topology]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Traffic &amp; Metrics</h2>
          <p className="text-sm text-slate-400">Measurements reported by the existing topology and metrics APIs.</p>
        </div>
        <button onClick={() => refresh().catch(console.error)} className="button-secondary">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          ['Average utilization', metrics ? `${metrics.avg_utilization_pct.toFixed(1)}%` : 'N/A'],
          ['Peak utilization', metrics ? `${metrics.max_utilization_pct.toFixed(1)}%` : 'N/A'],
          ['Average latency', metrics ? `${metrics.avg_latency_ms.toFixed(1)} ms` : 'N/A'],
          ['Congested links', metrics ? metrics.congested_links_count : 'N/A'],
        ].map(([label, value]) => (
          <div key={label} className="glass-panel p-4 rounded-2xl border border-cyber-border">
            <p className="text-xs text-slate-500 uppercase tracking-wider">{label}</p>
            <p className="mt-2 text-xl font-mono font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      <div className="glass-panel p-5 rounded-2xl border border-cyber-border">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-purple-400" /> Available utilization measurements
        </h3>
        <div className="h-64">
          {history.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232738" />
                <XAxis dataKey="time" stroke="#64748B" fontSize={11} />
                <YAxis stroke="#64748B" fontSize={11} unit="%" />
                <Tooltip contentStyle={{ backgroundColor: '#12141D', borderColor: '#232738' }} />
                <Area type="monotone" dataKey="utilization" name="Average utilization" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-slate-500">N/A — no live measurements available.</p>}
        </div>
      </div>

      <div className="glass-panel rounded-2xl border border-cyber-border overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#0E1017] text-slate-400 uppercase tracking-wider">
            <tr><th className="p-4">Link</th><th className="p-4">Throughput</th><th className="p-4">Utilization</th><th className="p-4">Latency</th><th className="p-4">Packet loss</th></tr>
          </thead>
          <tbody className="divide-y divide-cyber-border/60">
            {links.map((link: LinkEdge) => (
              <tr key={link.link_id}>
                <td className="p-4 font-mono text-purple-300">{link.src_dpid} → {link.dst_dpid}</td>
                <td className="p-4 text-slate-300">{link.current_rate_mbps.toFixed(2)} Mbps</td>
                <td className="p-4 text-slate-300">{link.utilization_pct.toFixed(1)}%</td>
                <td className="p-4 text-slate-300">{link.latency_ms} ms</td>
                <td className="p-4 text-slate-300">{link.packet_loss_pct.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!links.length && <p className="p-4 text-sm text-slate-500">N/A — no link measurements available.</p>}
      </div>
    </div>
  );
};
