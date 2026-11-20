import React, { useEffect, useState } from 'react';
import { TopologyData, SwitchNode, HostNode, LinkEdge } from '../../types/network';
import { Activity } from 'lucide-react';

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

  const defaultPositions: Record<string, { x: number; y: number }> = {
    // Hosts
    'h1': { x: 50, y: 150 }, 'h2': { x: 50, y: 350 },
    'h7': { x: 750, y: 150 }, 'h8': { x: 750, y: 350 },
    // Switches
    's1': { x: 180, y: 250 }, 's2': { x: 330, y: 140 },
    's3': { x: 330, y: 360 }, 's4': { x: 440, y: 250 },
    's5': { x: 550, y: 140 }, 's6': { x: 550, y: 360 }, 's7': { x: 670, y: 250 },
  };
  const [positions, setPositions] = useState(defaultPositions);
  useEffect(() => {
    const next = { ...positions };
    topology.switches.forEach((sw, index) => {
      if (!next[sw.dpid]) next[sw.dpid] = { x: 180 + (index % 5) * 125, y: 100 + (Math.floor(index / 5) % 3) * 150 };
    });
    topology.hosts.forEach((host, index) => {
      const id = (host.name || host.ip).toLowerCase().replace(/[^a-z0-9]/g, '');
      if (!next[id]) next[id] = { x: 70, y: 80 + (index % 5) * 85 };
    });
    setPositions(next);
  }, [topology]);

  const nodePositions: Record<string, { x: number; y: number; label: string; type: 'switch' | 'host' }> = {};
  topology.switches.forEach((sw) => {
    const position = positions[sw.dpid];
    if (position) nodePositions[sw.dpid] = { ...position, label: sw.name, type: 'switch' };
  });
  topology.hosts.forEach((host) => {
    const id = (host.name || host.ip).toLowerCase().replace(/[^a-z0-9]/g, '');
    const position = positions[id];
    if (position) nodePositions[id] = { ...position, label: `${host.name || id} (${host.ip})`, type: 'host' };
  });

  return (
    <div className="relative glass-panel rounded-2xl p-4 overflow-hidden border border-cyber-border/70">
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

          const color = link.is_active ? '#10B981' : '#EF4444';
          const isSelected = selectedLinkId === link.link_id;

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
                strokeDasharray={link.is_active ? undefined : '8 5'}
                filter={isSelected ? 'url(#glow)' : undefined}
                className="transition-all duration-200 group-hover:stroke-purple-400 group-hover:stroke-[3.5]"
              />
            </g>
          );
        })}
        {topology.hosts.map((host) => {
          const hostId = (host.name || host.ip).toLowerCase().replace(/[^a-z0-9]/g, '');
          const src = nodePositions[hostId];
          const dst = nodePositions[host.connected_switch];
          if (!src || !dst) return null;
          return <line key={`${hostId}-${host.connected_switch}`} x1={src.x} y1={src.y} x2={dst.x} y2={dst.y}
            stroke="#10B981" strokeWidth="2" strokeDasharray="4 3" />;
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
              onMouseDown={(event) => {
                const start = { x: event.clientX, y: event.clientY };
                const original = { x: pos.x, y: pos.y };
                const move = (moveEvent: MouseEvent) => setPositions((current) => ({
                  ...current,
                  [id]: { x: Math.max(20, Math.min(780, original.x + moveEvent.clientX - start.x)), y: Math.max(20, Math.min(480, original.y + moveEvent.clientY - start.y)) },
                }));
                const stop = () => {
                  window.removeEventListener('mousemove', move);
                  window.removeEventListener('mouseup', stop);
                };
                window.addEventListener('mousemove', move);
                window.addEventListener('mouseup', stop);
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
