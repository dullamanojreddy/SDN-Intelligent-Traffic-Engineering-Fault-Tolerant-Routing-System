import React, { useEffect, useState } from 'react';
import { TopologyGraph } from '../components/topology/TopologyGraph';
import { api } from '../services/api';
import { TopologyData, SwitchNode, HostNode, LinkEdge } from '../types/network';
import { Server } from 'lucide-react';

export const Topology: React.FC = () => {
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [selectedElement, setSelectedElement] = useState<SwitchNode | HostNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<LinkEdge | null>(null);

  useEffect(() => {
    const refreshTopology = () => {
      api.getTopology().then((res) => setTopology(res.data)).catch(console.error);
    };

    refreshTopology();
    const interval = setInterval(refreshTopology, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Interactive Topology Discovery</h2>
        <p className="text-sm text-slate-400">
          Inspect switches, physical port links, link utilization rates, and trigger link fault simulations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TopologyGraph
            topology={topology}
            onSelectNode={(node) => {
              setSelectedElement(node);
              setSelectedLink(null);
            }}
            onSelectLink={(link) => {
              setSelectedLink(link);
              setSelectedElement(null);
            }}
          />
        </div>

        {/* Element Inspector */}
        <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
            <Server className="w-4 h-4 text-purple-400" />
            <span>Element Inspector</span>
          </h3>

          {selectedLink ? (
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-[#0E1017] rounded-xl border border-cyber-border space-y-2">
                <div className="flex justify-between font-mono font-bold text-slate-200">
                  <span>Link {selectedLink.link_id.toUpperCase()}</span>
                  <span className={selectedLink.is_active ? 'text-emerald-400' : 'text-red-400'}>
                    {selectedLink.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-slate-400">Capacity: {selectedLink.capacity_mbps} Mbps</div>
                <div className="text-slate-400">Current Traffic: {selectedLink.current_rate_mbps} Mbps</div>
                <div className="text-slate-400">Utilization: {selectedLink.utilization_pct.toFixed(1)}%</div>
                <div className="text-slate-400">Latency: {selectedLink.latency_ms} ms</div>
                <div className="text-slate-400">Loss: {selectedLink.packet_loss_pct}%</div>
              </div>

            </div>
          ) : selectedElement ? (
            <div className="p-3 bg-[#0E1017] rounded-xl border border-cyber-border space-y-2 text-xs">
              <div className="font-mono font-bold text-purple-300">
                {'dpid' in selectedElement ? `Switch ${selectedElement.name}` : `Host ${selectedElement.name}`}
              </div>
              {'dpid' in selectedElement ? (
                <>
                  <div className="text-slate-400">DPID: {selectedElement.dpid}</div>
                  <div className="text-slate-400">Active Flows: {selectedElement.active_flows}</div>
                  <div className="text-slate-400">Status: Operational (OF 1.3)</div>
                </>
              ) : (
                <>
                  <div className="text-slate-400">IP: {selectedElement.ip}</div>
                  <div className="text-slate-400">MAC: {selectedElement.mac}</div>
                  <div className="text-slate-400">Attached Switch: {selectedElement.connected_switch} (Port {selectedElement.connected_port})</div>
                </>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-500">Click any switch, host, or link in the canvas to inspect real-time telemetry.</p>
          )}
        </div>
      </div>
    </div>
  );
};
