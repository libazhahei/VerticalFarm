import React from 'react';
import { Chip, alpha } from '@mui/material';

const StatusChip = ({ status, icon: Icon }) => {
  const getStatusColor = (status) => {
    const colors = {
      Good: '#4caf50',
      Warning: '#ff9800',
      Critical: '#f44336',
      Excellent: '#2196f3'
    };
    return colors[status] || '#607d8b';
  };

  const color = getStatusColor(status);

  return (
    <Chip
      icon={Icon && <Icon fontSize="small" />}
      label={status}
      size="medium"
      sx={{
        bgcolor: alpha(color, 0.1),
        color,
        border: `1px solid ${alpha(color, 0.3)}`,
        fontWeight: 600,
        fontSize: '0.875rem'
      }}
    />
  );
};

export default StatusChip;
