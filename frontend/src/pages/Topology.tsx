import React, { useEffect, useState } from 'react';
import { TopologyGraph } from '../components/topology/TopologyGraph';
import { api } from '../services/api';
import { TopologyData, SwitchNode, HostNode, LinkEdge } from '../types/network';
import { AlertCircle, Plus, RefreshCw, Server, Trash2, Unplug } from 'lucide-react';

export const Topology: React.FC = () => {
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [selectedElement, setSelectedElement] = useState<SwitchNode | HostNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<LinkEdge | null>(null);
  const [switchName, setSwitchName] = useState('');
  const [hostForm, setHostForm] = useState({ name: '', ip: '', connected_switch: '' });
  const [linkForm, setLinkForm] = useState({ src: '', dst: '' });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const refreshTopology = () => {
      api.getTopology().then((res) => {
        setTopology(res.data);
        setHostForm((current) => ({
          ...current,
          connected_switch: current.connected_switch || res.data.switches[0]?.dpid || '',
        }));
        setLinkForm((current) => ({
          src: current.src || res.data.switches[0]?.dpid || '',
          dst: current.dst || res.data.switches[1]?.dpid || '',
        }));
      }).catch((error) => setMessage(error.response?.data?.detail || 'Unable to load topology'));
    };

    refreshTopology();
    const interval = setInterval(refreshTopology, 3000);
    return () => clearInterval(interval);
  }, []);

  const refresh = () => api.getTopology().then((res) => setTopology(res.data));
  const runOperation = (operation: Promise<unknown>, success: string) => operation
    .then(() => { setMessage(success); return refresh(); })
    .catch((error) => setMessage(error.response?.data?.detail || 'Topology operation failed'));

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-2xl font-bold text-white tracking-tight">Interactive Topology Editor</h2>
          <button onClick={refresh} className="button-secondary"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>
        <p className="text-sm text-slate-400">
          Manage the running topology. Dragging nodes changes presentation only; mutations are applied by the backend.
        </p>
      </div>

      {message && (
        <div className="flex items-center gap-2 rounded-xl border border-cyber-border bg-cyber-card px-4 py-3 text-xs text-slate-300">
          <AlertCircle className="w-4 h-4 text-purple-300" /> {message}
          <button className="ml-auto text-slate-500 hover:text-white" onClick={() => setMessage(null)}>Dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <form className="glass-panel rounded-2xl p-4 space-y-3" onSubmit={(event) => {
          event.preventDefault();
          if (switchName) runOperation(api.createSwitch(switchName), `Switch ${switchName} created`);
          setSwitchName('');
        }}>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Add switch</h3>
          <div className="flex gap-2"><input className="control flex-1" value={switchName} onChange={(e) => setSwitchName(e.target.value)} placeholder="s8" />
            <button className="button-secondary" type="submit"><Plus className="w-4 h-4" /> Add</button></div>
        </form>
        <form className="glass-panel rounded-2xl p-4 space-y-3" onSubmit={(event) => {
          event.preventDefault();
          runOperation(api.createHost(hostForm), `Host ${hostForm.name} created`);
          setHostForm((current) => ({ ...current, name: '', ip: '' }));
        }}>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Add host</h3>
          <div className="grid grid-cols-3 gap-2">
            <input className="control" required placeholder="h9" value={hostForm.name} onChange={(e) => setHostForm({ ...hostForm, name: e.target.value })} />
            <input className="control" required placeholder="10.0.0.9" value={hostForm.ip} onChange={(e) => setHostForm({ ...hostForm, ip: e.target.value })} />
            <select className="control" required value={hostForm.connected_switch} onChange={(e) => setHostForm({ ...hostForm, connected_switch: e.target.value })}>
              {topology?.switches.map((sw) => <option key={sw.dpid} value={sw.dpid}>{sw.dpid}</option>)}
            </select>
          </div>
          <button className="button-secondary" type="submit"><Plus className="w-4 h-4" /> Add host</button>
        </form>
        <form className="glass-panel rounded-2xl p-4 space-y-3" onSubmit={(event) => {
          event.preventDefault();
          if (linkForm.src !== linkForm.dst) runOperation(api.createLink(linkForm), `Link ${linkForm.src}-${linkForm.dst} created`);
        }}>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Connect switches</h3>
          <div className="flex gap-2">
            <select className="control flex-1" value={linkForm.src} onChange={(e) => setLinkForm({ ...linkForm, src: e.target.value })}>{topology?.switches.map((sw) => <option key={sw.dpid} value={sw.dpid}>{sw.dpid}</option>)}</select>
            <select className="control flex-1" value={linkForm.dst} onChange={(e) => setLinkForm({ ...linkForm, dst: e.target.value })}>{topology?.switches.map((sw) => <option key={sw.dpid} value={sw.dpid}>{sw.dpid}</option>)}</select>
          </div>
          <button className="button-secondary" type="submit"><Plus className="w-4 h-4" /> Connect</button>
        </form>
      </div>

      {topology && <div className="flex flex-wrap gap-2 text-xs">
        {topology.switches.map((sw) => <button key={sw.dpid} className="button-secondary" onClick={() => {
          if (window.confirm(`Remove ${sw.dpid} and all connected links?`)) runOperation(api.deleteSwitch(sw.dpid), `Switch ${sw.dpid} removed`);
        }}><Trash2 className="w-3 h-3 text-red-400" /> {sw.dpid}</button>)}
        {topology.hosts.map((host) => <button key={host.name} className="button-secondary" onClick={() => {
          if (host.name && window.confirm(`Remove ${host.name}?`)) runOperation(api.deleteHost(host.name), `Host ${host.name} removed`);
        }}><Trash2 className="w-3 h-3 text-red-400" /> {host.name}</button>)}
        {topology.links.filter((link) => link.src_dpid < link.dst_dpid).map((link) => <button key={link.link_id} className="button-secondary" onClick={() => {
          if (window.confirm(`Delete link ${link.src_dpid}-${link.dst_dpid}?`)) runOperation(api.deleteLink(link.src_dpid, link.dst_dpid), `Link ${link.src_dpid}-${link.dst_dpid} removed`);
        }}><Unplug className="w-3 h-3 text-amber-400" /> {link.src_dpid}-{link.dst_dpid}</button>)}
      </div>}

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
