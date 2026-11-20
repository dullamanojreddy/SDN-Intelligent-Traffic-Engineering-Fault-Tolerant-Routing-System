/**
 * SDN-ITE Real-Time Operations UI & Telemetry Dashboard (Final Draft)
 */
import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { Topology } from './pages/Topology';
import { Traffic } from './pages/Traffic';
import { Flows } from './pages/Flows';
import { Routing } from './pages/Routing';
import { Experiments } from './pages/Experiments';
import { Alerts } from './pages/Alerts';
import { api } from './services/api';
import { wsClient } from './services/websocket';
import { SystemStatus, ControllerStatus } from './types/network';

export const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [controller, setController] = useState<ControllerStatus | null>(null);

  useEffect(() => {
    const refresh = () => {
      api.getSystemStatus()
        .then((res) => setStatus(res.data))
        .catch((err) => console.warn('Backend unavailable, running in preview mode:', err));
      api.getControllerStatus()
        .then((res) => setController(res.data))
        .catch(() => setController(null));
    };
    refresh();
    const interval = setInterval(refresh, 3000);

    // Controller state changes are pushed over the WebSocket for instant feedback.
    wsClient.connect();
    const unsubscribe = wsClient.subscribe((message) => {
      if (message?.type === 'CONTROLLER_STATUS') refresh();
    });

    return () => {
      clearInterval(interval);
      unsubscribe();
      wsClient.disconnect();
    };
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-[#0B0C10] text-slate-100 flex flex-col">
        <Navbar status={status} controller={controller} />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
            {controller && controller.status !== 'UP' && (
              <div className="mb-6 rounded-xl border border-red-500/40 bg-red-950/30 p-4 text-xs text-red-200">
                <p className="font-semibold">
                  {controller.status === 'DOWN' ? 'Controller unavailable' : 'Waiting for controller'}
                  {controller.status === 'DOWN' && ` - ${controller.consecutive_failures}/${controller.failure_threshold}+ missed heartbeats`}
                </p>
                <p className="mt-1 text-red-300/80">
                  Existing switch flows keep forwarding. Topology edits are accepted and queued
                  {controller.pending_sync ? ' (changes pending)' : ''}; they sync automatically on recovery.
                  {controller.last_error ? ` Last error: ${controller.last_error}` : ''}
                </p>
              </div>
            )}
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/topology" element={<Topology />} />
              <Route path="/traffic" element={<Traffic />} />
              <Route path="/flows" element={<Flows />} />
              <Route path="/routing" element={<Routing />} />
              <Route path="/experiments" element={<Experiments />} />
              <Route path="/alerts" element={<Alerts />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;
