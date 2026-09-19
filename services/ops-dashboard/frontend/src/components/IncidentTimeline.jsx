import React from 'react';
import { ExternalLink, AlertCircle, Activity, CheckCircle2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '../lib/utils';

function IncidentTimeline({ incidents, onIncidentClick }) {
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'border-l-red-500 bg-red-500/5';
      case 'high':
        return 'border-l-orange-500 bg-orange-500/5';
      case 'medium':
        return 'border-l-blue-500 bg-blue-500/5';
      case 'low':
        return 'border-l-green-500 bg-green-500/5';
      default:
        return 'border-l-gray-500 bg-gray-500/5';
    }
  };

  const getSeverityBadgeColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500 text-white';
      case 'high':
        return 'bg-orange-500 text-white';
      case 'medium':
        return 'bg-blue-500 text-white';
      case 'low':
        return 'bg-green-500 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'resolved':
        return 'bg-green-500/20 text-green-400';
      case 'in_progress':
        return 'bg-blue-500/20 text-blue-400';
      case 'open':
        return 'bg-yellow-500/20 text-yellow-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  if (!incidents || incidents.length === 0) {
    return (
      <div className="glass rounded-2xl p-8 text-center">
        <CheckCircle2 className="h-12 w-12 text-green-400 mx-auto mb-3" />
        <p className="text-white/80 text-lg">No incidents detected. System is healthy!</p>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl max-h-[600px] overflow-auto">
      <div className="divide-y divide-white/10">
        {incidents.map((incident, index) => (
          <div
            key={incident.incident_id || index}
            className={cn(
              "p-4 border-l-4 hover:bg-white/5 cursor-pointer transition-all",
              getSeverityColor(incident.severity)
            )}
            onClick={() => onIncidentClick && onIncidentClick(incident.incident_id)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <h3 className="text-white font-semibold">{incident.title}</h3>
                  <span className={cn(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold",
                    getSeverityBadgeColor(incident.severity)
                  )}>
                    {incident.severity}
                  </span>
                  <span className={cn(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold",
                    getStatusBadgeColor(incident.status)
                  )}>
                    {incident.status || 'open'}
                  </span>
                </div>

                <p className="text-white/60 text-sm mb-1">
                  Service: {incident.service} | Metric: {incident.metric}
                </p>
                
                <p className="text-white/50 text-xs">
                  {incident.timestamp
                    ? formatDistanceToNow(new Date(incident.timestamp), { addSuffix: true })
                    : 'Just now'}
                </p>

                {incident.value !== undefined && incident.threshold !== undefined && (
                  <p className="text-white/50 text-xs mt-1">
                    Value: {incident.value} (Threshold: {incident.threshold})
                  </p>
                )}
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onIncidentClick && onIncidentClick(incident.incident_id);
                }}
                className="p-2 rounded-full hover:bg-white/10 transition-colors"
              >
                <ExternalLink className="h-4 w-4 text-white/60" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default IncidentTimeline;
