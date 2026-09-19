import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

function MetricsChart({ metrics }) {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="glass rounded-2xl p-8 text-center">
        <TrendingUp className="h-12 w-12 text-white/40 mx-auto mb-3" />
        <p className="text-white/60">No metrics data available</p>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-6">
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={metrics}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis 
            dataKey="timestamp" 
            stroke="rgba(255,255,255,0.6)"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="rgba(255,255,255,0.6)"
            style={{ fontSize: '12px' }}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'rgba(0,0,0,0.8)', 
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '12px',
              backdropFilter: 'blur(12px)'
            }}
            labelStyle={{ color: '#fff' }}
          />
          <Legend 
            wrapperStyle={{ color: '#fff' }}
          />
          <Line 
            type="monotone" 
            dataKey="cpu" 
            stroke="#3b82f6" 
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 3 }}
          />
          <Line 
            type="monotone" 
            dataKey="memory" 
            stroke="#8b5cf6" 
            strokeWidth={2}
            dot={{ fill: '#8b5cf6', r: 3 }}
          />
          <Line 
            type="monotone" 
            dataKey="errors" 
            stroke="#ef4444" 
            strokeWidth={2}
            dot={{ fill: '#ef4444', r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MetricsChart;
