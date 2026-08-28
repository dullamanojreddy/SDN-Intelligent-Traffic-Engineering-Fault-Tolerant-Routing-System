import React, { useState } from 'react';
import { Settings as SettingsIcon, Sliders, Save, RefreshCw } from 'lucide-react';

export const Settings: React.FC = () => {
  const [monitorInterval, setMonitorInterval] = useState('2.0');
  const [utilThreshold, setUtilThreshold] = useState('85.0');
  const [persistenceCycles, setPersistenceCycles] = useState('3');
  const [latencyWeight, setLatencyWeight] = useState('0.4');
  const [utilWeight, setUtilWeight] = useState('0.4');
  const [lossWeight, setLossWeight] = useState('0.2');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Controller & Algorithm Settings</h2>
        <p className="text-sm text-slate-400">Configure real-time monitoring loops, hysteresis triggers, and multi-metric cost weights.</p>
      </div>

      <div className="glass-panel p-6 rounded-2xl border border-cyber-border space-y-6">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-purple-400" />
          <span>Traffic Engineering Parameters</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-slate-300 font-medium">Monitoring Interval (Seconds)</label>
            <input
              value={monitorInterval}
              onChange={(e) => setMonitorInterval(e.target.value)}
              className="w-full bg-[#0E1017] border border-cyber-border rounded-xl px-3.5 py-2.5 text-white font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-300 font-medium">Congestion Threshold (%)</label>
            <input
              value={utilThreshold}
              onChange={(e) => setUtilThreshold(e.target.value)}
              className="w-full bg-[#0E1017] border border-cyber-border rounded-xl px-3.5 py-2.5 text-white font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-300 font-medium">Persistence Confirmation (Cycles)</label>
            <input
              value={persistenceCycles}
              onChange={(e) => setPersistenceCycles(e.target.value)}
              className="w-full bg-[#0E1017] border border-cyber-border rounded-xl px-3.5 py-2.5 text-white font-mono"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-cyber-border/60">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4">Cost Function Weights (α + β + γ = 1.0)</h4>
          <div className="grid grid-cols-3 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">Latency Weight (α)</label>
              <input
                value={latencyWeight}
                onChange={(e) => setLatencyWeight(e.target.value)}
                className="w-full bg-[#0E1017] border border-cyber-border rounded-xl px-3.5 py-2.5 text-white font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">Utilization Weight (β)</label>
              <input
                value={utilWeight}
                onChange={(e) => setUtilWeight(e.target.value)}
                className="w-full bg-[#0E1017] border border-cyber-border rounded-xl px-3.5 py-2.5 text-white font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">Loss Weight (γ)</label>
              <input
                value={lossWeight}
                onChange={(e) => setLossWeight(e.target.value)}
                className="w-full bg-[#0E1017] border border-cyber-border rounded-xl px-3.5 py-2.5 text-white font-mono"
              />
            </div>
          </div>
        </div>

        <div className="pt-2">
          <button
            onClick={handleSave}
            className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-5 py-2.5 rounded-xl flex items-center space-x-2 transition shadow-lg shadow-purple-600/30 text-xs"
          >
            <Save className="w-4 h-4" />
            <span>{saved ? 'Settings Saved!' : 'Apply Global Configuration'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
