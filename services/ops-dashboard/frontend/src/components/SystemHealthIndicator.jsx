import React from 'react';
import { Chip } from '@mui/material';
import { CheckCircle, Error, Warning } from '@mui/icons-material';

function SystemHealthIndicator({ health }) {
  const getHealthIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle fontSize="small" />;
      case 'degraded':
        return <Warning fontSize="small" />;
      case 'error':
        return <Error fontSize="small" />;
      default:
        return null;
    }
  };

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Chip
      icon={getHealthIcon(health?.status)}
      label={`System ${health?.status || 'Unknown'}`}
      color={getHealthColor(health?.status)}
      size="small"
    />
  );
}

export default SystemHealthIndicator;
