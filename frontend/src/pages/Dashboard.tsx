import React, { useEffect, useState } from 'react';
import {
  Server,
  Monitor,
  Activity,
  GitCommit,
  AlertTriangle,
  Zap,
  ArrowUpRight,
  TrendingUp,
  Cpu,
  Layers
} from 'lucide-react';
import { KpiCard } from '../components/metrics/KpiCard';
import { TopologyGraph } from '../components/topology/TopologyGraph';
import { api } from '../services/api';
import { TopologyData, NetworkMetrics, AlertItem, RoutingDecision } from '../types/network';

export const Dashboard: React.FC = () => {
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [metrics, setMetrics] = useState<NetworkMetrics | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [decisions, setDecisions] = useState<RoutingDecision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [topoRes, metRes, alRes, decRes] = await Promise.all([
          api.getTopology(),
          api.getMetrics(),
          api.getAlerts(),
          api.getRoutingDecisions(),
        ]);
        setTopology(topoRes.data);
        setMetrics(metRes.data);
        setAlerts(alRes.data);
        setDecisions(decRes.data);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">SDN Intelligent Operations Center</h2>
          <p className="text-sm text-slate-400">
            Real-time topology monitoring, autonomous Dijkstra traffic engineering & fault recovery.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => api.recalculateRoute({ source_ip: '10.0.0.1', dest_ip: '10.0.0.8' })}
            className="bg-purple-600/20 border border-purple-500/40 hover:bg-purple-600/30 text-purple-300 px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Recalculate Routes</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Active Switches"
          value={metrics?.total_switches ?? 7}
          subtitle="OpenFlow 1.3 Datapaths"
          icon={Server}
          color="purple"
          change="All Healthy"
        />
        <KpiCard
          title="Discovered Hosts"
          value={metrics?.total_hosts ?? 4}
          subtitle="ARP Auto-Learned Endpoints"
          icon={Monitor}
          color="emerald"
          change="10.0.0.0/24"
        />
        <KpiCard
          title="Total Bandwidth"
          value={`${metrics?.total_bandwidth_mbps ?? 78.4} M`}
          subtitle={`Avg Util: ${metrics?.avg_utilization_pct ?? 34.2}%`}
          icon={TrendingUp}
          color="indigo"
          change="Real-time"
        />
        <KpiCard
          title="Active Flows"
          value={metrics?.active_flows ?? 14}
          subtitle="Installed Table-0 Matches"
          icon={GitCommit}
          color="amber"
          change="Dynamic"
        />
      </div>

      {/* Main Grid: Topology Visualizer (Left) + Right Control / Status Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Network Topology Graph (2 Columns) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center space-x-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <span>Multi-Path Mesh Topology</span>
            </h3>
            <span className="text-xs text-slate-500 font-mono">Live OpenFlow 1.3 Graph</span>
          </div>
          <TopologyGraph topology={topology} />
        </div>

        {/* Recent Events & Decisions (1 Column) */}
        <div className="space-y-6">
          {/* Recent Routing Decisions */}
          <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                <Zap className="w-3.5 h-3.5 text-purple-400" />
                <span>Autonomous Reroute Decisions</span>
              </h4>
            </div>

            <div className="space-y-3">
              {decisions.slice(0, 2).map((dec) => (
                <div
                  key={dec.decision_id}
                  className="p-3.5 rounded-xl bg-[#0E1017] border border-cyber-border/80 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="font-mono">{dec.source_ip} → {dec.dest_ip}</span>
                    <span className="text-[10px] text-purple-400 font-bold px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20">
                      {dec.qos_class}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 font-mono text-slate-200">
                    <span className="text-slate-500 line-through">{dec.old_path.join('→')}</span>
                    <span className="text-purple-400 font-bold">⇒</span>
                    <span className="text-emerald-400 font-bold">{dec.new_path.join('→')}</span>
                  </div>
                  <p className="text-[11px] text-slate-400">{dec.reason}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Real-time Alerts */}
          <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span>Telemetry Alerts</span>
              </h4>
            </div>

            <div className="space-y-2.5">
              {alerts.slice(0, 3).map((al, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-[#0E1017] border border-cyber-border/70 flex items-start space-x-3 text-xs"
                >
                  <div
                    className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                      al.severity === 'CRITICAL' || al.severity === 'ERROR'
                        ? 'bg-red-500 animate-ping'
                        : al.severity === 'WARNING'
                        ? 'bg-amber-500'
                        : 'bg-indigo-400'
                    }`}
                  />
                  <div className="space-y-0.5 overflow-hidden">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{al.type}</span>
                      <span className="text-[10px] text-slate-500 font-mono">{al.source}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate">{al.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
