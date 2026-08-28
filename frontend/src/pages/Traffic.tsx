import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { NetworkMetrics } from '../types/network';
import { Activity, Play, Square, TrendingUp, Zap } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

const SAMPLE_CHART_DATA = [
  { time: '00:00', s2_s5: 35, s3_s6: 20, latency: 6 },
  { time: '00:05', s2_s5: 42, s3_s6: 18, latency: 6 },
  { time: '00:10', s2_s5: 78, s3_s6: 22, latency: 9 },
  { time: '00:15', s2_s5: 94, s3_s6: 25, latency: 18 },
  { time: '00:20', s2_s5: 25, s3_s6: 82, latency: 7 }, // Reroute effect
  { time: '00:25', s2_s5: 30, s3_s6: 76, latency: 7 },
];

export const Traffic: React.FC = () => {
  const [metrics, setMetrics] = useState<NetworkMetrics | null>(null);
  const [rate, setRate] = useState(80);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.getMetrics().then((res) => setMetrics(res.data));
  }, []);

  const handleStartTraffic = () => {
    setRunning(true);
    api.startTraffic({
      src_host: '10.0.0.1',
      dst_host: '10.0.0.8',
      rate_mbps: rate,
      duration_sec: 60
    });
  };

  const handleStopTraffic = () => {
    setRunning(false);
    api.stopTraffic();
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Traffic Monitoring & Telemetry</h2>
          <p className="text-sm text-slate-400">Time-series bandwidth utilization, queuing latency, and synthetic traffic generation.</p>
        </div>
      </div>

      {/* Traffic Generator Controls */}
      <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
          <Zap className="w-4 h-4 text-purple-400" />
          <span>Synthetic iperf3 Traffic Generator</span>
        </h3>

        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="space-y-1">
            <label className="text-slate-400 font-mono">Source Host</label>
            <input disabled value="H1 (10.0.0.1)" className="bg-[#0E1017] border border-cyber-border rounded-xl px-3 py-2 text-slate-300 font-mono" />
          </div>
          <div className="space-y-1">
            <label className="text-slate-400 font-mono">Destination Host</label>
            <input disabled value="H8 (10.0.0.8)" className="bg-[#0E1017] border border-cyber-border rounded-xl px-3 py-2 text-slate-300 font-mono" />
          </div>
          <div className="space-y-1">
            <label className="text-slate-400 font-mono">Target Rate (Mbps)</label>
            <input
              type="number"
              value={rate}
              onChange={(e) => setRate(Number(e.target.value))}
              className="bg-[#0E1017] border border-cyber-border rounded-xl px-3 py-2 text-white font-mono w-28"
            />
          </div>

          <div className="pt-4 flex items-center space-x-3">
            {!running ? (
              <button
                onClick={handleStartTraffic}
                className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl flex items-center space-x-2 shadow-lg shadow-purple-600/30"
              >
                <Play className="w-4 h-4" />
                <span>Inject Traffic Flow</span>
              </button>
            ) : (
              <button
                onClick={handleStopTraffic}
                className="bg-red-600 hover:bg-red-500 text-white font-semibold px-4 py-2 rounded-xl flex items-center space-x-2 shadow-lg shadow-red-600/30"
              >
                <Square className="w-4 h-4" />
                <span>Stop Traffic</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="glass-panel p-5 rounded-2xl border border-cyber-border space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
          Link Utilization Over Time (Primary S2-S5 vs Alternate S3-S6)
        </h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={SAMPLE_CHART_DATA}>
              <defs>
                <linearGradient id="colorS2S5" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorS3S6" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#232738" />
              <XAxis dataKey="time" stroke="#64748B" fontSize={11} />
              <YAxis stroke="#64748B" fontSize={11} domain={[0, 100]} unit="%" />
              <Tooltip contentStyle={{ backgroundColor: '#12141D', borderColor: '#232738', borderRadius: '12px' }} />
              <Area type="monotone" dataKey="s2_s5" name="S2-S5 Utilization" stroke="#8B5CF6" fillOpacity={1} fill="url(#colorS2S5)" />
              <Area type="monotone" dataKey="s3_s6" name="S3-S6 Utilization" stroke="#10B981" fillOpacity={1} fill="url(#colorS3S6)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
