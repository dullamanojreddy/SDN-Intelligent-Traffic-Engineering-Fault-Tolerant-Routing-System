import React, { useEffect, useRef, useState } from 'react';
import { TopologyData, SwitchNode, HostNode, LinkEdge } from '../../types/network';
import { Activity } from 'lucide-react';

interface TopologyGraphProps {
  topology: TopologyData | null;
  onSelectNode?: (node: SwitchNode | HostNode | null) => void;
  onSelectLink?: (link: LinkEdge | null) => void;
  /** Switch ids of a route to draw highlighted, in order. */
  highlightPath?: string[] | null;
  /** Names of the source and destination hosts of that route. */
  highlightHosts?: string[];
}

export const TopologyGraph: React.FC<TopologyGraphProps> = ({
  topology,
  onSelectNode,
  onSelectLink,
  highlightPath,
  highlightHosts,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedLinkId, setSelectedLinkId] = useState<string | null>(null);

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
  // Switches placed before they had any link; re-placed once they are connected.
  const placedLinkless = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!topology) return;
    const next = { ...positions };
    // New nodes go to the first free grid slot so they never sit on top of existing ones.
    const freeSlot = (candidates: Array<{ x: number; y: number }>) =>
      candidates.find((c) => Object.values(next).every((p) => Math.hypot(p.x - c.x, p.y - c.y) > 70))
      ?? candidates[candidates.length - 1];
    const switchGrid = Array.from({ length: 60 }, (_, i) => ({ x: 120 + (i % 6) * 110, y: 70 + Math.floor(i / 6) * 90 }));
    const hostGrid = Array.from({ length: 40 }, (_, i) => ({ x: 40 + Math.floor(i / 8) * 60, y: 60 + (i % 8) * 55 }));
    // Distance from point p to segment a-b (to keep new links from running through nodes).
    const segDist = (p: { x: number; y: number }, a: { x: number; y: number }, b: { x: number; y: number }) => {
      const dx = b.x - a.x, dy = b.y - a.y;
      const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1)));
      return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
    };
    topology.switches.forEach((sw) => {
      const neighbours = Array.from(new Set(topology.links
        .filter((l) => l.src_dpid === sw.dpid || l.dst_dpid === sw.dpid)
        .map((l) => (l.src_dpid === sw.dpid ? l.dst_dpid : l.src_dpid))))
        .map((id) => next[id]).filter(Boolean);
      const replace = placedLinkless.current.has(sw.dpid) && neighbours.length > 0;
      if (next[sw.dpid] && !replace) return;
      if (replace) delete next[sw.dpid];
      if (neighbours.length) placedLinkless.current.delete(sw.dpid); else placedLinkless.current.add(sw.dpid);
      const free = switchGrid.filter((c) => Object.values(next).every((p) => Math.hypot(p.x - c.x, p.y - c.y) > 70));
      // Best slot: close to its neighbours, and no link to them passes near another node.
      const scored = free.map((c) => {
        const crossings = neighbours.reduce((n, nb) =>
          n + Object.values(next).filter((p) => p !== nb && segDist(p, c, nb) < 28).length, 0);
        const length = neighbours.reduce((sum, nb) => sum + Math.hypot(nb.x - c.x, nb.y - c.y), 0);
        // Never sit on top of an existing link either (it would look like a hop on that link).
        const onLinks = topology.links.filter((l) => l.src_dpid < l.dst_dpid).reduce((n, l) => {
          const a = next[l.src_dpid], b = next[l.dst_dpid];
          return n + (a && b && segDist(c, a, b) < 45 ? 1 : 0);
        }, 0);
        return { c, score: crossings * 1000 + onLinks * 1500 + length };
      }).sort((a, b) => a.score - b.score);
      next[sw.dpid] = scored.length ? scored[0].c : freeSlot(switchGrid);
    });
    topology.hosts.forEach((host) => {
      const id = (host.name || host.ip).toLowerCase().replace(/[^a-z0-9]/g, '');
      if (!next[id]) {
        // Prefer a spot right next to the switch the host hangs off.
        const sw = next[host.connected_switch];
        const around = sw ? [[-70, -45], [-70, 45], [70, -45], [70, 45], [0, -80], [0, 80]]
          .map(([dx, dy]) => ({ x: sw.x + dx, y: sw.y + dy })) : [];
        next[id] = freeSlot([...around, ...hostGrid]);
      }
    });
    setPositions(next);
  }, [topology]);

  if (!topology || topology.switches.length === 0) {
    return (
      <div className="h-96 glass-panel rounded-2xl flex flex-col items-center justify-center text-slate-500 space-y-2">
        <Activity className="w-8 h-8 animate-spin text-purple-500" />
        <p className="text-sm font-mono">Discovering OpenFlow Switches & Topologies...</p>
      </div>
    );
  }

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
        {highlightPath && highlightPath.length > 1 && highlightPath.slice(1).map((dstId, i) => {
          const a = nodePositions[highlightPath[i]];
          const b = nodePositions[dstId];
          if (!a || !b) return null;
          return (
            <line key={`route-${i}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#FBBF24"
              strokeWidth={6} strokeLinecap="round" filter="url(#glow)" pointerEvents="none" />
          );
        })}
        {topology.hosts.map((host) => {
          const hostId = (host.name || host.ip).toLowerCase().replace(/[^a-z0-9]/g, '');
          const src = nodePositions[hostId];
          const dst = nodePositions[host.connected_switch];
          if (!src || !dst) return null;
          const onRoute = !!highlightPath && (highlightHosts ?? []).includes(host.name ?? '');
          return <line key={`${hostId}-${host.connected_switch}`} x1={src.x} y1={src.y} x2={dst.x} y2={dst.y}
            stroke={onRoute ? '#FBBF24' : '#10B981'} strokeWidth={onRoute ? 5 : 2} strokeDasharray={onRoute ? undefined : '4 3'} />;
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
