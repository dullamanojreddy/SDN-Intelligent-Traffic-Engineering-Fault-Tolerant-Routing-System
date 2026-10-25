import React, { useEffect, useState } from 'react';
import { FlaskConical, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { ExperimentItem } from '../types/network';

const SCENARIOS = ['Normal Traffic', 'Congestion', 'Link Failure', 'Static vs Dynamic Routing'];

export const Experiments: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [selected, setSelected] = useState('Normal Traffic');

  const refresh = () => api.getExperiments().then((res) => setExperiments(res.data)).catch(console.error);
  useEffect(() => { refresh(); }, []);

  const selectedResults = experiments.filter((experiment) =>
    `${experiment.name} ${experiment.type}`.toLowerCase().includes(selected.toLowerCase().replace(' ', ''))
      || selected.toLowerCase().includes(experiment.type.toLowerCase().replace('_test', '').replace('_', ' '))
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Experiments</h2>
          <p className="text-sm text-slate-400">Measured results returned by the existing experiment API.</p>
        </div>
        <button onClick={refresh} className="button-secondary"><RefreshCw className="w-4 h-4" /> Refresh</button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {SCENARIOS.map((scenario) => (
          <button
            key={scenario}
            onClick={() => setSelected(scenario)}
            className={`p-4 rounded-xl border text-left text-sm transition ${
              selected === scenario ? 'border-purple-500/50 bg-purple-500/10 text-purple-200' : 'border-cyber-border bg-cyber-card text-slate-400'
            }`}
          >
            <FlaskConical className="w-4 h-4 mb-2 text-purple-400" />
            {scenario}
          </button>
        ))}
      </div>

      <div className="glass-panel rounded-2xl border border-cyber-border p-5">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4">{selected} results</h3>
        {selectedResults.length ? selectedResults.map((experiment) => (
          <div key={experiment.experiment_id} className="p-4 rounded-xl bg-[#0E1017] border border-cyber-border text-xs">
            <div className="flex justify-between font-bold">
              <span className="text-purple-300">{experiment.name}</span>
              <span className="text-emerald-400">{experiment.status}</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-slate-400">
              <span>Throughput: <b className="text-white">{experiment.metrics.throughput_mbps} Mbps</b></span>
              <span>Latency: <b className="text-white">{experiment.metrics.avg_latency_ms} ms</b></span>
              <span>Packet loss: <b className="text-white">{experiment.metrics.packet_loss_pct}%</b></span>
              <span>Recovery: <b className="text-white">{experiment.metrics.recovery_time_ms} ms</b></span>
            </div>
          </div>
        )) : <p className="text-sm text-slate-500">N/A — no measured result is available for this scenario.</p>}
      </div>
    </div>
  );
};
