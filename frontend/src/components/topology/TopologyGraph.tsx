import React, { useState } from 'react';
import { TopologyData, SwitchNode, HostNode, LinkEdge } from '../../types/network';
import { Server, Monitor, Activity, ArrowRight, Zap, AlertCircle } from 'lucide-react';

interface TopologyGraphProps {
  topology: TopologyData | null;
  onSelectNode?: (node: SwitchNode | HostNode | null) => void;
  onSelectLink?: (link: LinkEdge | null) => void;
}

export const TopologyGraph: React.FC<TopologyGraphProps> = ({
  topology,
  onSelectNode,
  onSelectLink,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedLinkId, setSelectedLinkId] = useState<string | null>(null);

  if (!topology || topology.switches.length === 0) {
    return (
      <div className="h-96 glass-panel rounded-2xl flex flex-col items-center justify-center text-slate-500 space-y-2">
        <Activity className="w-8 h-8 animate-spin text-purple-500" />
        <p className="text-sm font-mono">Discovering OpenFlow Switches & Topologies...</p>
      </div>
    );
  }

  // Pre-computed graphical coordinates for standard 7-switch mesh
  const nodePositions: Record<string, { x: number; y: number; label: string; type: 'switch' | 'host' }> = {
    // Hosts
    'h1': { x: 50, y: 150, label: 'H1 (10.0.0.1)', type: 'host' },
    'h2': { x: 50, y: 350, label: 'H2 (10.0.0.2)', type: 'host' },
    'h7': { x: 750, y: 150, label: 'H7 (10.0.0.7)', type: 'host' },
    'h8': { x: 750, y: 350, label: 'H8 (10.0.0.8)', type: 'host' },
    // Switches
    's1': { x: 180, y: 250, label: 'S1 Ingress', type: 'switch' },
    's2': { x: 330, y: 140, label: 'S2 Core-T', type: 'switch' },
    's3': { x: 330, y: 360, label: 'S3 Core-B', type: 'switch' },
    's4': { x: 440, y: 250, label: 'S4 Center', type: 'switch' },
    's5': { x: 550, y: 140, label: 'S5 Agg-T', type: 'switch' },
    's6': { x: 550, y: 360, label: 'S6 Agg-B', type: 'switch' },
    's7': { x: 670, y: 250, label: 'S7 Egress', type: 'switch' },
  };

  const getLinkColor = (link: LinkEdge) => {
    if (!link.is_active || link.status === 'failed') return '#EF4444'; // red
    if (link.utilization_pct >= 90) return '#EF4444'; // critical red
    if (link.utilization_pct >= 80) return '#F97316'; // orange
    if (link.utilization_pct >= 60) return '#F59E0B'; // yellow
    return '#10B981'; // nominal green
  };

  return (
    <div className="relative glass-panel rounded-2xl p-4 overflow-hidden border border-cyber-border/70">
      {/* Legend & Stats Overlay */}
      <div className="absolute top-4 left-4 z-10 flex items-center space-x-3 bg-cyber-card/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-cyber-border text-xs font-mono">
        <span className="text-slate-400">Utilization:</span>
        <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span><span className="text-slate-300">&lt;60%</span></span>
        <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded-full bg-amber-500"></span><span className="text-slate-300">60-80%</span></span>
        <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded-full bg-orange-500"></span><span className="text-slate-300">80-90%</span></span>
        <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span><span className="text-slate-300">&gt;90%</span></span>
      </div>

      <svg viewBox="0 0 800 500" className="w-full h-[420px] select-none">
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Links */}
        {topology.links.map((link) => {
          const src = nodePositions[link.src_dpid];
          const dst = nodePositions[link.dst_dpid];
          if (!src || !dst) return null;

          const color = getLinkColor(link);
          const isSelected = selectedLinkId === link.link_id;

          // Midpoint for label
          const midX = (src.x + dst.x) / 2;
          const midY = (src.y + dst.y) / 2;

          return (
            <g
              key={link.link_id}
              onClick={() => {
                setSelectedLinkId(link.link_id);
                onSelectLink?.(link);
              }}
              className="cursor-pointer group"
            >
              <line
                x1={src.x}
                y1={src.y}
                x2={dst.x}
                y2={dst.y}
                stroke={color}
                strokeWidth={isSelected ? 4 : 2.5}
                strokeDasharray={!link.is_active ? '5,5' : 'none'}
                filter={isSelected ? 'url(#glow)' : undefined}
                className="transition-all duration-200 group-hover:stroke-purple-400 group-hover:stroke-[3.5]"
              />
              {/* Utilization Tag */}
              <rect
                x={midX - 18}
                y={midY - 9}
                width="36"
                height="16"
                rx="4"
                fill="#0E1017"
                stroke={color}
                strokeWidth="1"
              />
              <text
                x={midX}
                y={midY + 3}
                fill="#E2E8F0"
                fontSize="9"
                fontFamily="monospace"
                textAnchor="middle"
                fontWeight="bold"
              >
                {link.utilization_pct.toFixed(0)}%
              </text>
            </g>
          );
        })}

        {/* Nodes (Switches & Hosts) */}
        {Object.entries(nodePositions).map(([id, pos]) => {
          const isSwitch = pos.type === 'switch';
          const isSelected = selectedNodeId === id;

          return (
            <g
              key={id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => {
                setSelectedNodeId(id);
                const sw = topology.switches.find((s) => s.dpid === id);
                const h = topology.hosts.find((host) => host.name?.toLowerCase().includes(id) || host.mac.includes(id));
                onSelectNode?.(sw || h || null);
              }}
              className="cursor-pointer group"
            >
              <circle
                r={isSwitch ? 22 : 16}
                fill={isSwitch ? '#181B26' : '#12141D'}
                stroke={isSelected ? '#8B5CF6' : isSwitch ? '#6366F1' : '#10B981'}
                strokeWidth={isSelected ? 3 : 2}
                filter={isSelected ? 'url(#glow)' : undefined}
                className="transition duration-150 group-hover:stroke-purple-400"
              />
              <text
                y={isSwitch ? 4 : 3}
                fill="#FFFFFF"
                fontSize={isSwitch ? '11' : '9'}
                fontWeight="bold"
                fontFamily="sans-serif"
                textAnchor="middle"
              >
                {id.toUpperCase()}
              </text>
              <text
                y={isSwitch ? 36 : 28}
                fill="#94A3B8"
                fontSize="10"
                fontFamily="sans-serif"
                textAnchor="middle"
              >
                {pos.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
