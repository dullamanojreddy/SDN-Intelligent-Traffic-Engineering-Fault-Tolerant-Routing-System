import axios from 'axios';
import {
  TopologyData,
  SystemStatus,
  NetworkMetrics,
  FlowEntry,
  RoutingDecision,
  AlertItem,
  ExperimentItem
} from '../types/network';

const API_BASE = '/api';

export const api = {
  getSystemStatus: () => axios.get<SystemStatus>(`${API_BASE}/system/status`),
  getTopology: () => axios.get<TopologyData>(`${API_BASE}/topology`),
  getSwitches: () => axios.get(`${API_BASE}/switches`),
  getLinks: () => axios.get(`${API_BASE}/links`),
  getHosts: () => axios.get(`${API_BASE}/hosts`),
  getMetrics: () => axios.get<NetworkMetrics>(`${API_BASE}/metrics`),
  getFlows: () => axios.get<FlowEntry[]>(`${API_BASE}/flows`),
  getRoutingDecisions: () => axios.get<RoutingDecision[]>(`${API_BASE}/routing/decisions`),
  getAlerts: () => axios.get<AlertItem[]>(`${API_BASE}/alerts`),
  getExperiments: () => axios.get<ExperimentItem[]>(`${API_BASE}/experiments`),
  
  // Controls
  recalculateRoute: (data: { source_ip: string; dest_ip: string; qos_class?: string }) =>
    axios.post(`${API_BASE}/routing/recalculate`, data),
  startTraffic: (data: { src_host: string; dst_host: string; rate_mbps: number; duration_sec: number; protocol?: string }) =>
    axios.post(`${API_BASE}/network/traffic/start`, data),
  stopTraffic: () => axios.post(`${API_BASE}/network/traffic/stop`),
  simulateFailure: (data: { src_switch: string; dst_switch: string; action: 'UP' | 'DOWN' }) =>
    axios.post(`${API_BASE}/network/failure/simulate`, data),
  startExperiment: (data: { name: string; type: string; topology?: string; traffic_rate_mbps?: number; duration_sec?: number }) =>
    axios.post(`${API_BASE}/experiments/start`, data),
  stopExperiment: () => axios.post(`${API_BASE}/experiments/stop`),
};
