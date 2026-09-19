import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Typography,
  Box,
  AppBar,
  Toolbar,
  Button,
  Chip,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

import IncidentTimeline from '../components/IncidentTimeline';
import AgentStatusCards from '../components/AgentStatusCards';
import MetricsChart from '../components/MetricsChart';
import SystemHealthIndicator from '../components/SystemHealthIndicator';
import wsService from '../services/websocket';
import { apiService } from '../services/api';

function DashboardPage() {
  const [incidents, setIncidents] = useState([]);
  const [agents, setAgents] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [systemHealth, setSystemHealth] = useState({ status: 'loading' });
  const [connected, setConnected] = useState(false);
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

    // Refresh data periodically
    const interval = setInterval(() => {
      loadAgents();
      loadSystemHealth();
    }, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, []);

  // Real-time incident updates
  useEffect(() => {
    const handleNewIncident = (data) => {
      console.log('New incident:', data);
      setIncidents(prev => [data, ...prev]);
      toast.error(`New ${data.severity} incident detected: ${data.title}`, {
        autoClose: 10000,
      });
    };

    const handleIncidentUpdate = (data) => {
      console.log('Incident updated:', data);
      setIncidents(prev =>
        prev.map(inc => (inc.incident_id === data.incident_id ? { ...inc, ...data } : inc))
      );
    };

    const handleAnalysis = (data) => {
      console.log('Analysis complete:', data);
      toast.info(`Analysis complete for incident: ${data.incident_id}`);
      loadIncidents(); // Refresh to get updated analysis
    };

    const handleAction = (data) => {
      console.log('Action executed:', data);
      toast.success(`Action executed: ${data.action.type}`);
    };

    const handleAgentStatus = (data) => {
      console.log('Agent status update:', data);
      setAgents(prev =>
        prev.map(agent =>
          agent.name === data.agent_name ? { ...agent, ...data } : agent
        )
      );
    };

    const handleMetrics = (data) => {
      console.log('Metrics update:', data);
      setMetrics(prev => [...prev.slice(-99), data]); // Keep last 100 points
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
      // Use mock data for development
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
      // Use mock data
      setAgents([
        { name: 'monitoring-agent', status: 'healthy', last_seen: new Date().toISOString() },
        { name: 'analyzer-agent', status: 'healthy', last_seen: new Date().toISOString() },
        { name: 'autoresponse-agent', status: 'healthy', last_seen: new Date().toISOString() },
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

  // Incident control functions
  const [triggeringIncident, setTriggeringIncident] = useState(false);
  const [stoppingIncident, setStoppingIncident] = useState(false);
  const [incidentInterval, setIncidentInterval] = useState(null);

  const handleStartIncident = async () => {
    setTriggeringIncident(true);
    
    // Array of different chaos scenarios for variety
    const chaosScenarios = [
      { name: 'CPU spike', endpoint: '/api/chaos/trigger-cpu' },
      { name: 'Memory leak', endpoint: '/api/chaos/trigger-memory' },
      { name: 'HTTP errors', endpoint: '/api/chaos/trigger-errors' }
    ];
    
    let currentIndex = 0;
    
    // Trigger first incident immediately
    try {
      const scenario = chaosScenarios[currentIndex];
      await fetch(`http://localhost:8001${scenario.endpoint}`, { method: 'POST' });
      toast.success(`${scenario.name} incident triggered!`, { autoClose: 3000 });
      currentIndex = (currentIndex + 1) % chaosScenarios.length;
    } catch (error) {
      console.error('Failed to trigger incident:', error);
      toast.error('Failed to trigger incident: ' + error.message);
    }
    
    // Then trigger different scenarios every 45 seconds (safe interval)
    const interval = setInterval(async () => {
      try {
        const scenario = chaosScenarios[currentIndex];
        await fetch(`http://localhost:8001${scenario.endpoint}`, { method: 'POST' });
        toast.success(`${scenario.name} incident triggered!`, { autoClose: 3000 });
        currentIndex = (currentIndex + 1) % chaosScenarios.length;
      } catch (error) {
        console.error('Failed to trigger incident:', error);
      }
    }, 45000); // 45 seconds interval
    
    setIncidentInterval(interval);
    setTriggeringIncident(false);
  };

  const handleStopIncident = async () => {
    setStoppingIncident(true);
    
    // Clear the interval to stop generating new incidents
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

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            DevOps Copilot - Operations Dashboard
          </Typography>
          <SystemHealthIndicator health={systemHealth} />
          <Chip
            label={connected ? 'Live' : 'Disconnected'}
            color={connected ? 'success' : 'error'}
            size="small"
            sx={{ ml: 2 }}
          />
          <Button
            color="error"
            variant="contained"
            onClick={handleStartIncident}
            disabled={triggeringIncident}
            sx={{ ml: 2 }}
          >
            {triggeringIncident ? 'Starting...' : 'Start Incident'}
          </Button>
          <Button
            color="warning"
            variant="outlined"
            onClick={handleStopIncident}
            disabled={stoppingIncident}
            sx={{ ml: 1 }}
          >
            {stoppingIncident ? 'Stopping...' : 'Stop Incident'}
          </Button>

          <Chip
            label={`Live Incidents: ${incidents.filter(i => i.status !== 'resolved' && i.status !== 'closed').length}`}
            color={incidents.filter(i => i.status !== 'resolved' && i.status !== 'closed').length > 0 ? 'error' : 'default'}
            variant="outlined"
            sx={{ ml: 2, fontWeight: 'bold' }}
          />

          <Button color="inherit" onClick={() => navigate('/agents')} sx={{ ml: 2 }}>
            Agents
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Grid container spacing={3}>
          {/* Agent Status Cards */}
          <Grid item xs={12}>
            <Typography variant="h5" gutterBottom>
              Agent Status
            </Typography>
            <AgentStatusCards agents={agents} />
          </Grid>

          {/* Incident Timeline */}
          <Grid item xs={12} md={8}>
            <Typography variant="h5" gutterBottom>
              Incident Timeline
            </Typography>
            <IncidentTimeline incidents={incidents} onIncidentClick={(id) => navigate(`/incidents/${id}`)} />
          </Grid>

          {/* Metrics Chart */}
          <Grid item xs={12} md={4}>
            <Typography variant="h5" gutterBottom>
              System Metrics
            </Typography>
            <MetricsChart metrics={metrics} />
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

export default DashboardPage;
