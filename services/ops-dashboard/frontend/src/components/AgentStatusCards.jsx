import React from 'react';
import { CheckCircle, AlertCircle, AlertTriangle, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '../lib/utils';

function AgentStatusCards({ agents }) {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'degraded':
        return <AlertTriangle className="h-5 w-5 text-yellow-400" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-400" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getBorderColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'border-l-green-400';
      case 'degraded':
        return 'border-l-yellow-400';
      case 'error':
        return 'border-l-red-400';
      default:
        return 'border-l-gray-400';
    }
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500/20 text-green-400';
      case 'degraded':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'error':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  if (!agents || agents.length === 0) {
    return (
      <div className="glass rounded-2xl p-6 text-center">
        <p className="text-white/60">No agents found</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {agents.map((agent) => (
        <div
          key={agent.name}
          className={cn(
            "glass rounded-2xl p-4 border-l-4 glass-hover transition-all",
            getBorderColor(agent.status)
          )}
        >
          <div className="flex items-center gap-2 mb-3">
            {getStatusIcon(agent.status)}
            <h3 className="text-white font-medium text-sm capitalize">
              {agent.name.replace('-agent', '').replace('-', ' ')}
            </h3>
          </div>

          <span className={cn(
            "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold mb-2",
            getStatusBadgeColor(agent.status)
          )}>
            {agent.status || 'unknown'}
          </span>

          {agent.last_seen && (
            <p className="text-white/60 text-xs">
              Last seen: {formatDistanceToNow(new Date(agent.last_seen), { addSuffix: true })}
            </p>
          )}

          {agent.tasks_processed !== undefined && (
            <p className="text-white/60 text-xs mt-1">
              Tasks: {agent.tasks_processed}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default AgentStatusCards;
