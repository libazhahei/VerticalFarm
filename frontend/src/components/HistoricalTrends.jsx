// src/components/HistoricalTrends.jsx
import React from 'react';
import { useTheme, styled } from '@mui/material/styles';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import { Card, Typography } from '@mui/material';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function HistoricalTrends ({ data }) {
  const theme = useTheme();
  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>Historical Trends</Typography>
      <ResponsiveContainer width="100%" height={600}>
        <LineChart data={data}>
          <Line type="monotone" dataKey="val1" stroke={theme.palette.primary.main} dot={false} />
          <Line type="monotone" dataKey="val2" stroke={theme.palette.secondary.main} dot={false} />
          <Line type="monotone" dataKey="val3" stroke={theme.palette.success.main} dot={false} />
          <XAxis dataKey="timestamp" stroke={theme.palette.text.secondary} />
          <YAxis stroke={theme.palette.text.secondary} />
          <Tooltip
            contentStyle={{ backgroundColor: theme.palette.background.paper }}
            labelStyle={{ color: theme.palette.text.primary }}
          />
        </LineChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}
