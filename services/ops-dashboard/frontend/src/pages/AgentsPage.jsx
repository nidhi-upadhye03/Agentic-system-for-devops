import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Database, Zap, Bell, Brain, ArrowLeft, Server } from 'lucide-react';
import AgentWorkflow from '../components/AgentWorkflow';
import wsService from '../services/websocket';
import { apiService } from '../services/api';
import Beams from '../components/ui/beams';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { cn } from '../lib/utils';

function AgentsPage() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [stats, setStats] = useState({
    totalIncidents: 0,
    resolvedIncidents: 0,
    avgResponseTime: 0,
    activeAgents: 0
  });

  useEffect(() => {
    loadAgents();
    loadStats();

    // Real-time agent updates
    const handleAgentStatus = (data) => {
      setAgents(prev =>
        prev.map(agent =>
          agent.name === data.agent_name ? { ...agent, ...data } : agent
        )
      );
    };

    wsService.socket?.on('agent_status', handleAgentStatus);
    return () => {
      wsService.socket?.off('agent_status', handleAgentStatus);
    };
  }, []);

  const loadAgents = async () => {
    try {
      const response = await apiService.getAgents();
      const agentsData = response.data || response; // Handle both wrapped and unwrapped responses
      setAgents(agentsData);
      setStats(prev => ({ ...prev, activeAgents: agentsData.filter(a => a.status === 'healthy').length }));
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await apiService.getIncidents();
      const incidents = response.data || response; // Handle both wrapped and unwrapped responses
      const resolved = incidents.filter(i => i.status === 'resolved').length;
      const total = incidents.length;
      
      // Calculate average response time from resolved incidents
      const resolvedIncidents = incidents.filter(i => i.status === 'resolved' && i.resolved_at);
      const avgTime = resolvedIncidents.length > 0
        ? resolvedIncidents.reduce((sum, inc) => {
            const start = new Date(inc.detected_at);
            const end = new Date(inc.resolved_at);
            return sum + (end - start);
          }, 0) / resolvedIncidents.length / 1000 // Convert to seconds
        : 0;

      setStats(prev => ({
        ...prev,
        totalIncidents: total,
        resolvedIncidents: resolved,
        avgResponseTime: Math.round(avgTime)
      }));
    } catch (error) {
      console.error('Failed to load stats:', error);
      // Set default stats on error to prevent crash
      setStats(prev => ({
        ...prev,
        totalIncidents: 0,
        resolvedIncidents: 0,
        avgResponseTime: 0
      }));
    }
  };

  const agentPipeline = [
    {
      name: 'Monitoring Agent',
      icon: Activity,
      color: 'blue',
      description: 'Continuously monitors Prometheus metrics and detects anomalies',
      responsibilities: [
        'Scrapes metrics from Prometheus',
        'Detects threshold breaches',
        'Identifies anomalies using ML',
        'Publishes incident events to RabbitMQ'
      ]
    },
    {
      name: 'Analyzer Agent',
      icon: Server,
      color: 'purple',
      description: 'Analyzes incidents using LLM to determine root cause',
      responsibilities: [
        'Receives incident events from queue',
        'Queries historical data from PostgreSQL',
        'Analyzes patterns using Gemini/Claude',
        'Determines severity and root cause'
      ]
    },
    {
      name: 'Auto-Response Agent',
      icon: Zap,
      color: 'green',
      description: 'Generates and executes automated remediation actions',
      responsibilities: [
        'Receives analyzed incidents',
        'Generates remediation plan using LLM',
        'Executes safe automated actions',
        'Triggers approval workflow for risky actions'
      ]
    },
    {
      name: 'Notifier Agent',
      icon: Bell,
      color: 'yellow',
      description: 'Sends real-time notifications to dashboards and external systems',
      responsibilities: [
        'Publishes to WebSocket for real-time UI',
        'Sends alerts to external channels',
        'Maintains notification history',
        'Handles notification preferences'
      ]
    },
    {
      name: 'Memory Agent',
      icon: Brain,
      color: 'pink',
      description: 'Stores incident knowledge for learning and future reference',
      responsibilities: [
        'Stores incident data in vector DB',
        'Enables semantic search across incidents',
        'Provides historical context to other agents',
        'Learns from past resolutions'
      ]
    }
  ];

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

      {/* Content */}
      <div className="relative z-10">
        {/* Glassmorphic Navbar */}
        <nav className="glass border-b border-white/10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-4">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/')}
                  className="text-white hover:bg-white/10"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Dashboard
                </Button>
                <h1 className="text-xl font-semibold text-white ml-4">
                  Agent Workflow Pipeline
                </h1>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="success" className="px-3 py-1">
                  {stats.activeAgents} Active
                </Badge>
                <Badge className="px-3 py-1 bg-blue-500/20 text-blue-400 border-blue-500/30">
                  Live
                </Badge>
              </div>
            </div>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Stats Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card className="glass border-l-4 border-l-blue-500">
              <CardContent className="p-4">
                <div className="text-sm text-gray-400 mb-1">Total Incidents</div>
                <div className="text-3xl font-bold text-white">{stats.totalIncidents}</div>
              </CardContent>
            </Card>
            <Card className="glass border-l-4 border-l-green-500">
              <CardContent className="p-4">
                <div className="text-sm text-gray-400 mb-1">Resolved</div>
                <div className="text-3xl font-bold text-white">{stats.resolvedIncidents}</div>
              </CardContent>
            </Card>
            <Card className="glass border-l-4 border-l-purple-500">
              <CardContent className="p-4">
                <div className="text-sm text-gray-400 mb-1">Avg Response Time</div>
                <div className="text-3xl font-bold text-white">{stats.avgResponseTime}s</div>
              </CardContent>
            </Card>
            <Card className="glass border-l-4 border-l-yellow-500">
              <CardContent className="p-4">
                <div className="text-sm text-gray-400 mb-1">Active Agents</div>
                <div className="text-3xl font-bold text-white">{stats.activeAgents}/5</div>
              </CardContent>
            </Card>
          </div>

          {/* Animated Workflow Visualization */}
          <Card className="glass p-8 mb-8 text-center">
            <h2 className="text-3xl font-semibold text-white mb-6">
              Event-Driven Architecture
            </h2>
            <AgentWorkflow
              circleText="AI"
              badgeTexts={{
                first: "Monitor",
                second: "Analyze",
                third: "Respond",
                fourth: "Notify"
              }}
              buttonTexts={{
                first: "DevOps Agent",
                second: "v1.0.0"
              }}
              title="Autonomous Agent Workflow - Event-Driven Incident Response"
              lightColor="#3b82f6"
            />
            <p className="text-gray-400 mt-4 text-sm">
              Agents communicate via RabbitMQ message broker for real-time event processing
            </p>
          </Card>

          {/* Agent Pipeline Details */}
          <h2 className="text-2xl font-semibold text-white mb-4">
            Agent Pipeline Details
          </h2>
          <div className="space-y-4">
            {agentPipeline.map((agent, index) => {
              const agentStatus = agents.find(a => a.name?.toLowerCase().includes(agent.name.split(' ')[0].toLowerCase()));
              const Icon = agent.icon;
              const colorClasses = {
                blue: 'border-l-blue-500 bg-blue-500/10 text-blue-400',
                purple: 'border-l-purple-500 bg-purple-500/10 text-purple-400',
                green: 'border-l-green-500 bg-green-500/10 text-green-400',
                yellow: 'border-l-yellow-500 bg-yellow-500/10 text-yellow-400',
                pink: 'border-l-pink-500 bg-pink-500/10 text-pink-400'
              };
              
              return (
                <Card
                  key={agent.name}
                  className={cn(
                    "glass border-l-4 transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl",
                    `border-l-${agent.color}-500`
                  )}
                >
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-start gap-4 flex-1">
                        <div className={cn("p-3 rounded-xl", colorClasses[agent.color])}>
                          <Icon size={24} />
                        </div>
                        <div className="flex-1">
                          <h3 className="text-xl font-semibold text-white mb-1">
                            {index + 1}. {agent.name}
                          </h3>
                          <p className="text-sm text-gray-400">
                            {agent.description}
                          </p>
                        </div>
                      </div>
                      {agentStatus && (
                        <Badge
                          variant={agentStatus.status === 'healthy' ? 'success' : 'destructive'}
                          className="ml-4"
                        >
                          {agentStatus.status}
                        </Badge>
                      )}
                    </div>
                    <div className="h-px bg-white/10 my-4" />
                    <div className={cn("text-sm font-medium mb-3", `text-${agent.color}-400`)}>
                      Key Responsibilities:
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {agent.responsibilities.map((resp, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <div className={cn(
                            "w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0",
                            `bg-${agent.color}-500`
                          )} />
                          <span className="text-sm text-gray-300">{resp}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Technology Stack */}
          <Card className="glass p-6 mt-8">
            <h3 className="text-xl font-semibold text-white mb-4">
              Technology Stack
            </h3>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="px-3 py-1.5 border-white/20 text-gray-300">
                <Database className="w-4 h-4 mr-2" />
                PostgreSQL
              </Badge>
              <Badge variant="outline" className="px-3 py-1.5 border-white/20 text-gray-300">
                <Activity className="w-4 h-4 mr-2" />
                RabbitMQ
              </Badge>
              <Badge variant="outline" className="px-3 py-1.5 border-white/20 text-gray-300">
                <Zap className="w-4 h-4 mr-2" />
                Prometheus
              </Badge>
              <Badge variant="outline" className="px-3 py-1.5 border-white/20 text-gray-300">
                <Server className="w-4 h-4 mr-2" />
                Redis
              </Badge>
              <Badge variant="outline" className="px-3 py-1.5 border-white/20 text-gray-300">
                <Brain className="w-4 h-4 mr-2" />
                Gemini AI
              </Badge>
              <Badge variant="outline" className="px-3 py-1.5 border-white/20 text-gray-300">
                <Brain className="w-4 h-4 mr-2" />
                Vector DB
              </Badge>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default AgentsPage;

