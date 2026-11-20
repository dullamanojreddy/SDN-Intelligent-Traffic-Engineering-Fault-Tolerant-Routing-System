import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AlertItem, RoutingCandidate, RoutingDecision } from '../types/network';
import { GitFork, ArrowRight, Zap, Scale, CheckCircle2, UploadCloud } from 'lucide-react';

export const Routing: React.FC = () => {
  const [decisions, setDecisions] = useState<RoutingDecision[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [srcIp, setSrcIp] = useState('10.0.0.1');
  const [dstIp, setDstIp] = useState('10.0.0.8');
  const [qosClass, setQosClass] = useState('VIDEO');
  const [candidatePaths, setCandidatePaths] = useState<RoutingCandidate[]>([]);
  const [explanation, setExplanation] = useState('');
  const [routeError, setRouteError] = useState('');
  const [installation, setInstallation] = useState<any>(null);

  useEffect(() => {
    Promise.all([api.getRoutingDecisions(), api.getAlerts()])
      .then(([decisionsRes, alertsRes]) => {
        setDecisions(decisionsRes.data);
        setAlerts(alertsRes.data);
      })
      .catch(console.error);
  }, []);

  const handleCompute = async () => {
    try {
      setRouteError('');
      const res = await api.recalculateRoute({
        source_ip: srcIp,
        dest_ip: dstIp,
        qos_class: qosClass
      });
      setCandidatePaths(res.data.candidate_paths || []);
      setExplanation(res.data.explanation || '');
      setInstallation(null);
    } catch (error: any) {
      setCandidatePaths([]);
      setExplanation('');
      setRouteError(error.response?.data?.detail || 'Unable to calculate a route');
    }
  };

  const handleInstall = async (path: string[]) => {
    try {
      setRouteError('');
      const result = await api.installRoute({
        installation_id: `install-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        source_ip: srcIp,
        dest_ip: dstIp,
        path,
      });
      setInstallation(result.data);
    } catch (error: any) {
      setInstallation(error.response?.data || { status: 'FAILED', failure_details: error.response?.data?.detail || 'Installation failed' });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Intelligent Multi-Metric Routing Engine</h2>
        <p className="text-sm text-slate-400">
          Evaluates normalized composite costs: Cost = α·Latency + β·Utilization + γ·Loss
        </p>
      </div>

      {/* Manual Route Optimizer Tester */}
      <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
          <Scale className="w-4 h-4 text-purple-400" />
          <span>Dynamic Path Evaluator</span>
        </h3>

        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div>
            <label className="text-slate-400 font-mono block mb-1">Source IP</label>
            <input
              value={srcIp}
              onChange={(e) => setSrcIp(e.target.value)}
              className="bg-[#0E1017] border border-cyber-border rounded-xl px-3 py-2 text-white font-mono"
            />
          </div>
          <div>
            <label className="text-slate-400 font-mono block mb-1">Destination IP</label>
            <input
              value={dstIp}
              onChange={(e) => setDstIp(e.target.value)}
              className="bg-[#0E1017] border border-cyber-border rounded-xl px-3 py-2 text-white font-mono"
            />
          </div>
          <div>
            <label className="text-slate-400 font-mono block mb-1">QoS Service Tier</label>
            <select
              value={qosClass}
              onChange={(e) => setQosClass(e.target.value)}
              className="bg-[#0E1017] border border-cyber-border rounded-xl px-3 py-2 text-white font-mono"
            >
              <option value="VOICE">VOICE (Latency Priority)</option>
              <option value="VIDEO">VIDEO (Bandwidth Priority)</option>
              <option value="WEB">WEB (Balanced)</option>
              <option value="BACKGROUND">BACKGROUND (Best Effort)</option>
            </select>
          </div>

          <div className="pt-4">
            <button
              onClick={handleCompute}
              className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl flex items-center space-x-2 shadow-lg shadow-purple-600/30"
            >
              <Zap className="w-4 h-4" />
              <span>Evaluate Dijkstra Paths</span>
            </button>
          </div>
        </div>

        {candidatePaths.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Candidate Evaluated Paths:</h4>
            {explanation && <p className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-3 text-xs text-purple-200">{explanation}</p>}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {candidatePaths.map((p, idx) => (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border text-xs space-y-2 ${
                    p.selected ? 'bg-purple-950/20 border-purple-500/40 text-purple-200' : 'bg-[#0E1017] border-cyber-border text-slate-300'
                  }`}
                >
                  <div className="flex justify-between items-center font-bold">
                    <span>Rank #{idx + 1} Path</span>
                    {p.selected && <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">Selected</span>}
                  </div>
                  <div className="font-mono text-xs">{p.path.join(' → ')}</div>
                  <div className="text-[11px] text-slate-400 space-y-0.5 font-mono">
                    <div>Composite Cost: {p.cost}</div>
                    <div>Est. Latency: {p.latency_ms} ms</div>
                    <div>Peak Util: {p.max_utilization_pct}%</div>
                    <div className="text-slate-500">{p.decision}</div>
                  </div>
                  {p.selected && <button onClick={() => handleInstall(p.path)} className="button-secondary mt-2"><UploadCloud className="w-3 h-3" /> Install selected route</button>}
                </div>
              ))}
            </div>
          </div>
        )}
        {routeError && <p className="mt-4 text-xs text-red-400">{routeError}</p>}
        {installation && <div className="rounded-xl border border-cyber-border bg-[#0E1017] p-3 text-xs">
          <div className="font-semibold text-slate-200">Installation: <span className={installation.status === 'INSTALLED' ? 'text-amber-400' : installation.status === 'VERIFIED' ? 'text-emerald-400' : 'text-red-400'}>{installation.status}</span></div>
          <div className="text-slate-400 mt-1">Flow verification: {installation.verification_status}</div>
          {installation.failure_details && <div className="text-red-400 mt-1">{installation.failure_details}</div>}
        </div>}
      </div>

      <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-3">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Latest routing and network alerts</h3>
        {alerts.length ? alerts.slice(0, 4).map((alert, index) => (
          <div key={`${alert.timestamp}-${index}`} className="flex items-start justify-between gap-4 p-3 rounded-xl bg-[#0E1017] text-xs">
            <div>
              <p className="font-semibold text-slate-200">{alert.type} <span className="text-slate-500">({alert.source})</span></p>
              <p className="text-slate-400 mt-1">{alert.message}</p>
            </div>
            <span className="text-slate-500 font-mono whitespace-nowrap">{alert.timestamp}</span>
          </div>
        )) : <p className="text-sm text-slate-500">N/A — no alerts reported.</p>}
      </div>

      {/* Historical Audit Trail */}
      <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Autonomous Reroute Audit Trail</h3>
        <div className="space-y-3">
          {decisions.map((dec) => (
            <div key={dec.decision_id} className="p-4 rounded-xl bg-[#0E1017] border border-cyber-border space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-mono text-slate-300 font-bold">{dec.source_ip} → {dec.dest_ip}</span>
                <span className="text-slate-500 font-mono">{dec.timestamp}</span>
              </div>
              <div className="flex items-center space-x-2 font-mono">
                <span className="text-slate-500 line-through">{dec.old_path.join('→')} (Cost: {dec.old_cost})</span>
                <span className="text-purple-400 font-bold">⇒</span>
                <span className="text-emerald-400 font-bold">{dec.new_path.join('→')} (Cost: {dec.new_cost})</span>
              </div>
              <p className="text-slate-400">{dec.reason}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
