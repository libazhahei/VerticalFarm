// src/components/TemperatureGauge.jsx
import React from 'react';
import { Box, Typography, Card } from '@mui/material';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function TemperatureGauge ({
  city = 'Sydney,AU',
  maxTemp = 40,
  fakeTemperature = 14.3 // You can change this to any static or random value
}) {
  const temperature = Math.round(fakeTemperature * 10) / 10;
  const size = 240;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (temperature / maxTemp) * circumference;

  return (
    <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
      <Typography variant="subtitle1" gutterBottom>
        {city.split(',')[0]} Temperature
      </Typography>
      <Box position="relative" mx="auto" width={size} height={size}>
        <svg viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="#e0e0e0" strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="#1976d2" strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <Box
          position="absolute"
          top={0} left={0}
          width="100%" height="100%"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Typography variant="h4">{temperature}°C</Typography>
        </Box>
      </Box>
      <Typography variant="caption">
        Last updated: Just now
      </Typography>
    </GlassCard>
  );
}
