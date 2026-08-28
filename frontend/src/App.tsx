import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { Topology } from './pages/Topology';
import { Traffic } from './pages/Traffic';
import { Flows } from './pages/Flows';
import { Routing } from './pages/Routing';
import { Alerts } from './pages/Alerts';
import { Experiments } from './pages/Experiments';
import { Settings } from './pages/Settings';
import { api } from './services/api';
import { wsClient } from './services/websocket';
import { SystemStatus } from './types/network';

export const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    // Initial status fetch
    api.getSystemStatus()
      .then((res) => setStatus(res.data))
      .catch((err) => console.warn('Backend unavailable, running in preview mode:', err));

    // Connect WebSocket
    wsClient.connect();
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-[#0B0C10] text-slate-100 flex flex-col">
        <Navbar status={status} />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/topology" element={<Topology />} />
              <Route path="/traffic" element={<Traffic />} />
              <Route path="/flows" element={<Flows />} />
              <Route path="/routing" element={<Routing />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/experiments" element={<Experiments />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;
