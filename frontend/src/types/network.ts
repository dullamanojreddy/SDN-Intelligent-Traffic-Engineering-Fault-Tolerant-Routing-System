export type LinkStatus = 'normal' | 'moderate' | 'high' | 'critical' | 'failed';

export interface SwitchPort {
  port_no: number;
  name?: string;
  hw_addr?: string;
  config?: number;
  state?: number;
  curr_speed?: number;
  max_speed?: number;
}

export interface SwitchNode {
  dpid: string;
  dpid_int: number;
  name: string;
  ports: SwitchPort[];
  ip?: string;
  connected: boolean;
  active_flows: number;
}

export interface HostNode {
  mac: string;
  ip: string;
  connected_switch: string;
  connected_port: number;
  name?: string;
}

export interface LinkEdge {
  link_id: string;
  src_dpid: string;
  src_port: number;
  dst_dpid: string;
  dst_port: number;
  capacity_mbps: number;
  current_rate_mbps: number;
  utilization_pct: number;
  latency_ms: number;
  packet_loss_pct: number;
  status: LinkStatus;
  is_active: boolean;
}

export interface TopologyData {
  switches: SwitchNode[];
  hosts: HostNode[];
  links: LinkEdge[];
  timestamp: string;
}

export interface SystemStatus {
  status: string;
  version: string;
  environment: string;
  controller_connected: boolean;
  database_connected: boolean;
  database_mode: string;
  active_switches: number;
  active_hosts: number;
  active_links: number;
  active_flows: number;
  uptime_sec: number;
}

export interface NetworkMetrics {
  timestamp: string;
  total_switches: number;
  total_hosts: number;
  total_links: number;
  active_flows: number;
  total_bandwidth_mbps: number;
  avg_utilization_pct: number;
  max_utilization_pct: number;
  congested_links_count: number;
  failed_links_count: number;
  avg_latency_ms: number;
}

export interface FlowEntry {
  flow_id: string;
  dpid: string;
  table_id: number;
  priority: number;
  match: {
    ipv4_src?: string;
    ipv4_dst?: string;
    ip_proto?: number;
    in_port?: number;
  };
  instructions: {
    type: string;
    actions: string[];
  }[];
  packet_count: number;
  byte_count: number;
  duration_sec: number;
  status: string;
}

export interface RoutingDecision {
  decision_id: string;
  timestamp: string;
  source_ip: string;
  dest_ip: string;
  old_path: string[];
  new_path: string[];
  reason: string;
  old_cost: number;
  new_cost: number;
  latency_ms: number;
  utilization_pct: number;
  packet_loss_pct: number;
  qos_class: string;
}

export interface AlertItem {
  timestamp: string;
  type: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  source: string;
  message: string;
  status: string;
}

export interface ExperimentItem {
  experiment_id: string;
  name: string;
  type: string;
  status: string;
  metrics: {
    avg_latency_ms: number;
    throughput_mbps: number;
    packet_loss_pct: number;
    recovery_time_ms: number;
  };
}
