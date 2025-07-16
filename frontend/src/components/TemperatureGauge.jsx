import React from 'react';
import { Box, Typography, Card } from '@mui/material';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({ /* same styles */ }));

export default function TemperatureGauge ({ temperature = 25.3 }) {
  const size = 240;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (temperature / 40) * circumference;

  return (
    <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
      <Box position="relative" mx="auto" width={size} height={size}>
        <svg viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#e0e0e0" strokeWidth={strokeWidth} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1976d2" strokeWidth={strokeWidth}
                  strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" />
        </svg>
        <Box position="absolute" top={0} left={0} width="100%" height="100%" display="flex" alignItems="center" justifyContent="center">
          <Typography variant="h4">{temperature}°C</Typography>
        </Box>
      </Box>
      <Typography variant="caption">Last control at 10:48 AM</Typography>
    </GlassCard>
  );
}
