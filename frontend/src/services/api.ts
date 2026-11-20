import axios from 'axios';
import {
  TopologyData,
  SystemStatus,
  NetworkMetrics,
  FlowEntry,
  RoutingDecision,
  AlertItem,
  ExperimentItem,
  ControllerStatus,
  NetworkStatus,
  RouteVerification,
  RouteExplanation,
} from '../types/network';

const API_BASE = '/api';

export const api = {
  getSystemStatus: () => axios.get<SystemStatus>(`${API_BASE}/system/status`),
  getTopology: () => axios.get<TopologyData>(`${API_BASE}/topology`),
  getSwitches: () => axios.get(`${API_BASE}/switches`),
  getLinks: () => axios.get(`${API_BASE}/links`),
  getHosts: () => axios.get(`${API_BASE}/hosts`),
  createSwitch: (name: string) => axios.post(`${API_BASE}/switches`, { name }),
  deleteSwitch: (name: string) => axios.delete(`${API_BASE}/switches/${encodeURIComponent(name)}`),
  createHost: (data: { name: string; ip: string; mac?: string; connected_switch: string }) =>
    axios.post(`${API_BASE}/hosts`, data),
  deleteHost: (name: string) => axios.delete(`${API_BASE}/hosts/${encodeURIComponent(name)}`),
  createLink: (data: { src: string; dst: string; capacity_mbps?: number; latency_ms?: number }) =>
    axios.post(`${API_BASE}/links`, data),
  deleteLink: (src: string, dst: string) =>
    axios.delete(`${API_BASE}/links/${encodeURIComponent(src)}/${encodeURIComponent(dst)}`),
  getMetrics: () => axios.get<NetworkMetrics>(`${API_BASE}/metrics`),
  getFlows: () => axios.get<FlowEntry[]>(`${API_BASE}/flows`),
  getRoutingDecisions: () => axios.get<RoutingDecision[]>(`${API_BASE}/routing/decisions`),
  getAlerts: () => axios.get<AlertItem[]>(`${API_BASE}/alerts`),
  getControllerStatus: () => axios.get<ControllerStatus>(`${API_BASE}/controller/status`),
  updateLink: (src: string, dst: string, data: { capacity_mbps?: number; latency_ms?: number; loss_pct?: number }) =>
    axios.patch(`${API_BASE}/links/${encodeURIComponent(src)}/${encodeURIComponent(dst)}`, data),
  getNetworkStatus: () => axios.get<NetworkStatus>(`${API_BASE}/network/status`),
  reconcileNetwork: (mode: 'report' | 'adopt') => axios.post(`${API_BASE}/network/reconcile`, null, { params: { mode } }),
  verifyRoute: (source_ip: string, dest_ip: string) =>
    axios.get<RouteVerification>(`${API_BASE}/routing/verify`, { params: { source_ip, dest_ip } }),
  getExperiments: () => axios.get<ExperimentItem[]>(`${API_BASE}/experiments`),
  
  // Controls
  recalculateRoute: (data: { source_ip: string; dest_ip: string; qos_class?: string; max_candidates?: number }) =>
    axios.post<RouteExplanation>(`${API_BASE}/routing/recalculate`, data),
  installRoute: (data: { installation_id: string; source_ip: string; dest_ip: string; path: string[] }) =>
    axios.post(`${API_BASE}/routing/install`, data),
  startTraffic: (data: { src_host: string; dst_host: string; rate_mbps: number; duration_sec: number; protocol?: string }) =>
    axios.post(`${API_BASE}/network/traffic/start`, data),
  stopTraffic: () => axios.post(`${API_BASE}/network/traffic/stop`),
  simulateFailure: (data: { src_switch: string; dst_switch: string; action: 'UP' | 'DOWN' }) =>
    axios.post(`${API_BASE}/network/failure/simulate`, data),
  startExperiment: (data: { name: string; type: string; topology?: string; traffic_rate_mbps?: number; duration_sec?: number }) =>
    axios.post(`${API_BASE}/experiments/start`, data),
  stopExperiment: () => axios.post(`${API_BASE}/experiments/stop`),
};
