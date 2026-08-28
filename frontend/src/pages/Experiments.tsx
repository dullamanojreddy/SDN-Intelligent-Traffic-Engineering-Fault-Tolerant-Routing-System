import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { ExperimentItem } from '../types/network';
import { FlaskConical, Play, CheckCircle2, BarChart2, Zap } from 'lucide-react';

export const Experiments: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.getExperiments().then((res) => setExperiments(res.data));
  }, []);

  const handleRun = (type: string, name: string) => {
    setRunning(true);
    api.startExperiment({ name, type }).then(() => {
      setTimeout(() => setRunning(false), 2000);
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Experiment & Benchmark Suite</h2>
          <p className="text-sm text-slate-400">Automated performance evaluation comparing Static vs SDN Dynamic routing.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-white text-sm">Exp 1: Congestion Dynamic Rerouting</h3>
            <span className="text-xs font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">Active Scenario</span>
          </div>
          <p className="text-xs text-slate-400">
            Injects 90 Mbps elephant traffic to overwhelm primary link S2-S5 and verifies seamless failover to S3-S6.
          </p>
          <button
            onClick={() => handleRun('CONGESTION_TEST', 'Congestion Dynamic Rerouting')}
            disabled={running}
            className="w-full bg-purple-600 hover:bg-purple-500 text-white py-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{running ? 'Running Test...' : 'Launch Experiment'}</span>
          </button>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-white text-sm">Exp 2: Abrupt Link Outage Recovery</h3>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Sub-Second Test</span>
          </div>
          <p className="text-xs text-slate-400">
            Simulates instant severance of core links and computes restoration latency and packet loss.
          </p>
          <button
            onClick={() => handleRun('FAILOVER_TEST', 'Link Outage Recovery')}
            disabled={running}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{running ? 'Running Test...' : 'Launch Experiment'}</span>
          </button>
        </div>
      </div>

      {/* Historical Experiment Results */}
      <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Benchmark Results Archive</h3>
        <div className="space-y-3">
          {experiments.map((exp) => (
            <div key={exp.experiment_id} className="p-4 bg-[#0E1017] rounded-xl border border-cyber-border space-y-2 text-xs">
              <div className="flex justify-between items-center font-bold">
                <span className="text-purple-300 font-mono">{exp.name}</span>
                <span className="text-emerald-400 font-mono">{exp.status}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-slate-400 text-[11px] pt-2 border-t border-cyber-border/60">
                <div>Latency: <span className="text-white font-bold">{exp.metrics.avg_latency_ms} ms</span></div>
                <div>Throughput: <span className="text-white font-bold">{exp.metrics.throughput_mbps} Mbps</span></div>
                <div>Packet Loss: <span className="text-white font-bold">{exp.metrics.packet_loss_pct}%</span></div>
                <div>Recovery Time: <span className="text-emerald-400 font-bold">{exp.metrics.recovery_time_ms} ms</span></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
