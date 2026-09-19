import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { ArrowRight, Activity, AlertCircle, CheckCircle2, Clock, Github, Star } from 'lucide-react';

import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Beams } from '../components/ui/beams';
import wsService from '../services/websocket';
import { apiService } from '../services/api';
import { cn } from '../lib/utils';

// Import existing components that we'll keep
import IncidentTimeline from '../components/IncidentTimeline';
import AgentStatusCards from '../components/AgentStatusCards';
import MetricsChart from '../components/MetricsChart';

function DashboardPage() {
  const [incidents, setIncidents] = useState([]);
  const [agents, setAgents] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [systemHealth, setSystemHealth] = useState({ status: 'loading' });
  const [connected, setConnected] = useState(false);
  const [triggeringIncident, setTriggeringIncident] = useState(false);
  const [stoppingIncident, setStoppingIncident] = useState(false);
  const [incidentInterval, setIncidentInterval] = useState(null);
  const navigate = useNavigate();

  // Initialize WebSocket connection
  useEffect(() => {
    wsService.connect();
    setConnected(wsService.isConnected());

    const handleConnect = () => setConnected(true);
    const handleDisconnect = () => setConnected(false);

    wsService.socket?.on('connect', handleConnect);
    wsService.socket?.on('disconnect', handleDisconnect);

    return () => {
      wsService.socket?.off('connect', handleConnect);
      wsService.socket?.off('disconnect', handleDisconnect);
    };
  }, []);

  // Load initial data
  useEffect(() => {
    loadIncidents();
    loadAgents();
    loadMetrics();
    loadSystemHealth();

    const interval = setInterval(() => {
      loadAgents();
      loadSystemHealth();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Real-time updates
  useEffect(() => {
    const handleNewIncident = (data) => {
      setIncidents(prev => [data, ...prev]);
      toast.error(`New ${data.severity} incident detected: ${data.title}`, { autoClose: 10000 });
    };

    const handleIncidentUpdate = (data) => {
      setIncidents(prev =>
        prev.map(inc => (inc.incident_id === data.incident_id ? { ...inc, ...data } : inc))
      );
    };

    const handleAnalysis = (data) => {
      toast.info(`Analysis complete for incident: ${data.incident_id}`);
      loadIncidents();
    };

    const handleAction = (data) => {
      toast.success(`Action executed: ${data.action.type}`);
    };

    const handleAgentStatus = (data) => {
      setAgents(prev =>
        prev.map(agent =>
          agent.name === data.agent_name ? { ...agent, ...data } : agent
        )
      );
    };

    const handleMetrics = (data) => {
      setMetrics(prev => [...prev.slice(-99), data]);
    };

    wsService.on('incident', handleNewIncident);
    wsService.on('incident_update', handleIncidentUpdate);
    wsService.on('analysis', handleAnalysis);
    wsService.on('action', handleAction);
    wsService.on('agent_status', handleAgentStatus);
    wsService.on('metrics', handleMetrics);

    return () => {
      wsService.off('incident', handleNewIncident);
      wsService.off('incident_update', handleIncidentUpdate);
      wsService.off('analysis', handleAnalysis);
      wsService.off('action', handleAction);
      wsService.off('agent_status', handleAgentStatus);
      wsService.off('metrics', handleMetrics);
    };
  }, []);

  const loadIncidents = async () => {
    try {
      const response = await apiService.getIncidents({ limit: 50 });
      setIncidents(response.data);
    } catch (error) {
      console.error('Failed to load incidents:', error);
      setIncidents([
        {
          incident_id: 'INC-001',
          title: 'High CPU Usage on web-server-3',
          severity: 'high',
          status: 'open',
          service: 'web-server',
          timestamp: new Date().toISOString(),
          metric: 'cpu_usage',
          value: 95,
          threshold: 80,
        },
      ]);
    }
  };

  const loadAgents = async () => {
    try {
      const response = await apiService.getAgents();
      setAgents(response.data);
    } catch (error) {
      console.error('Failed to load agents:', error);
      setAgents([
        { name: 'monitoring-agent', status: 'healthy', last_seen: new Date().toISOString() },
        { name: 'analyzer-agent', status: 'healthy', last_seen: new Date().toISOString() },
        { name: 'auto-response-agent', status: 'healthy', last_seen: new Date().toISOString() },
        { name: 'notifier-agent', status: 'healthy', last_seen: new Date().toISOString() },
        { name: 'approval-service', status: 'healthy', last_seen: new Date().toISOString() },
      ]);
    }
  };

  const loadMetrics = async () => {
    try {
      const response = await apiService.getMetrics({ limit: 100 });
      setMetrics(response.data);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  };

  const loadSystemHealth = async () => {
    try {
      const response = await apiService.getSystemHealth();
      setSystemHealth(response.data);
    } catch (error) {
      console.error('Failed to load system health:', error);
      setSystemHealth({ status: 'degraded', message: 'Unable to fetch health' });
    }
  };

  const handleStartIncident = async () => {
    setTriggeringIncident(true);
    
    const chaosScenarios = [
      { name: 'CPU spike', endpoint: '/api/chaos/trigger-cpu' },
      { name: 'Memory leak', endpoint: '/api/chaos/trigger-memory' },
      { name: 'HTTP errors', endpoint: '/api/chaos/trigger-errors' }
    ];
    
    let currentIndex = 0;
    
    try {
      const scenario = chaosScenarios[currentIndex];
      await fetch(`http://localhost:8001${scenario.endpoint}`, { method: 'POST' });
      toast.success(`${scenario.name} incident triggered!`, { autoClose: 3000 });
      currentIndex = (currentIndex + 1) % chaosScenarios.length;
    } catch (error) {
      console.error('Failed to trigger incident:', error);
      toast.error('Failed to trigger incident: ' + error.message);
    }
    
    const interval = setInterval(async () => {
      try {
        const scenario = chaosScenarios[currentIndex];
        await fetch(`http://localhost:8001${scenario.endpoint}`, { method: 'POST' });
        toast.success(`${scenario.name} incident triggered!`, { autoClose: 3000 });
        currentIndex = (currentIndex + 1) % chaosScenarios.length;
      } catch (error) {
        console.error('Failed to trigger incident:', error);
      }
    }, 45000);
    
    setIncidentInterval(interval);
    setTriggeringIncident(false);
  };

  const handleStopIncident = async () => {
    setStoppingIncident(true);
    
    if (incidentInterval) {
      clearInterval(incidentInterval);
      setIncidentInterval(null);
    }
    
    try {
      await fetch('http://localhost:8001/api/chaos/reset', { method: 'POST' });
      toast.info('All incidents stopped - chaos scenarios reset', { autoClose: 3000 });
    } catch (error) {
      console.error('Failed to stop incidents:', error);
      toast.error('Failed to stop incidents: ' + error.message);
    } finally {
      setStoppingIncident(false);
    }
  };

  const liveIncidentCount = incidents.filter(i => i.status !== 'resolved' && i.status !== 'closed').length;

  return (
    <div className="relative min-h-screen w-full bg-black">
      {/* Beams Background - Fixed to cover entire viewport */}
      <div className="fixed inset-0 z-0">
        <Beams
          beamWidth={2.5}
          beamHeight={18}
          beamNumber={15}
          lightColor="#ffffff"
          speed={2.5}
          noiseIntensity={2}
          scale={0.15}
          rotation={43}
        />
      </div>
      
      {/* Gradient Overlay - Fixed to cover entire viewport */}
      <div className="fixed inset-0 z-0 bg-gradient-to-t from-black/50 via-transparent to-black/30 pointer-events-none" />

      {/* Glassmorphic Navbar */}
      <nav className="relative z-20 w-full">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center">
              <span className="text-xl font-bold text-white">DevOps Copilot</span>
            </div>

            <div className="hidden md:flex items-center space-x-1 rounded-full glass p-1 -mr-6">
              <a href="/" className="rounded-full px-4 py-2 text-sm font-medium text-white bg-white/10">
                Dashboard
              </a>
              <a 
                href="/agents" 
                onClick={(e) => { e.preventDefault(); navigate('/agents'); }}
                className="rounded-full px-4 py-2 text-sm font-medium text-white/90 glass-hover"
              >
                Agents
              </a>
            </div>

            <div className="flex items-center space-x-4">
              <Badge variant={connected ? 'success' : 'destructive'}>
                {connected ? 'Live' : 'Disconnected'}
              </Badge>
              <Badge variant={liveIncidentCount > 0 ? 'destructive' : 'default'}>
                Live Incidents: {liveIncidentCount}
              </Badge>
              <Badge variant={systemHealth.status === 'healthy' ? 'success' : 'warning'}>
                {systemHealth.status}
              </Badge>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10 min-h-[calc(100vh-4rem)]">
        <div className="mx-auto max-w-7xl px-6 lg:px-8 py-8">
          {/* Hero Section */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-4xl font-bold text-white mb-2">
                  Operations Dashboard
                </h1>
                <p className="text-white/70 text-lg">
                  Monitor incidents, agents, and system health in real-time
                </p>
              </div>
              
              <div className="flex gap-3">
                <Button 
                  variant="destructive"
                  size="lg"
                  onClick={handleStartIncident}
                  disabled={triggeringIncident}
                  className="shimmer"
                >
                  <Activity className="mr-2 h-5 w-5" />
                  {triggeringIncident ? 'Starting...' : 'Start Incident'}
                </Button>
                <Button 
                  variant="outline"
                  size="lg"
                  onClick={handleStopIncident}
                  disabled={stoppingIncident}
                >
                  {stoppingIncident ? 'Stopping...' : 'Stop Incident'}
                </Button>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Total Incidents</p>
                      <p className="text-3xl font-bold text-white">{incidents.length}</p>
                    </div>
                    <AlertCircle className="h-10 w-10 text-white/40" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Active</p>
                      <p className="text-3xl font-bold text-red-400">{liveIncidentCount}</p>
                    </div>
                    <Activity className="h-10 w-10 text-red-400/60" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Resolved</p>
                      <p className="text-3xl font-bold text-green-400">
                        {incidents.filter(i => i.status === 'resolved' || i.status === 'closed').length}
                      </p>
                    </div>
                    <CheckCircle2 className="h-10 w-10 text-green-400/60" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Healthy Agents</p>
                      <p className="text-3xl font-bold text-white">
                        {agents.filter(a => a.status === 'healthy').length}/{agents.length}
                      </p>
                    </div>
                    <CheckCircle2 className="h-10 w-10 text-white/40" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Agent Status */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">Agent Status</h2>
            <AgentStatusCards agents={agents} />
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Incident Timeline */}
            <div className="lg:col-span-2">
              <h2 className="text-2xl font-bold text-white mb-4">Incident Timeline</h2>
              <IncidentTimeline 
                incidents={incidents} 
                onIncidentClick={(id) => navigate(`/incidents/${id}`)} 
              />
            </div>

            {/* Metrics Chart */}
            <div className="lg:col-span-1">
              <h2 className="text-2xl font-bold text-white mb-4">System Metrics</h2>
              <MetricsChart metrics={metrics} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
