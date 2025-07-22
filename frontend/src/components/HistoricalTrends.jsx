// src/components/HistoricalTrends.jsx
import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Card, Typography } from '@mui/material';
import { styled, useTheme } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' },
}));

export default function HistoricalTrends ({ data }) {
  const theme = useTheme();

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Historical Trends
      </Typography>
      <ResponsiveContainer width="100%" height={625}>
        <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
          <XAxis
            dataKey="timestamp"
            stroke={theme.palette.text.secondary}
            label={{ value: 'Time', position: 'insideBottomRight', offset: -5, fill: theme.palette.text.secondary }}
          />
          <YAxis
            yAxisId="left"
            orientation="left"
            stroke={theme.palette.text.secondary}
            label={{ value: '°C / %', angle: -90, position: 'insideLeft', fill: theme.palette.text.secondary }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: theme.palette.background.paper }}
            labelStyle={{ color: theme.palette.text.primary }}
          />
          <Legend verticalAlign="top" height={36} />

          {/* Temperature line */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="temperature"
            name="Temperature (°C)"
            stroke={theme.palette.primary.main}
            dot={{ r: 3 }}
            activeDot={{ r: 6 }}
            strokeWidth={2}
          />

          {/* Humidity area */}
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="humidity"
            name="Humidity (%)"
            fill={theme.palette.secondary.main}
            fillOpacity={0.2}
            stroke={theme.palette.secondary.main}
            strokeWidth={1.5}
          />

          {/* Light bar */}
          <Bar
            yAxisId="left"
            dataKey="light"
            name="Light (lx)"
            barSize={20}
            fill={theme.palette.success.main}
            opacity={0.6}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}
