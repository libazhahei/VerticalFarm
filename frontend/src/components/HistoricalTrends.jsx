// src/components/HistoricalTrends.jsx
import React, { useState, useEffect } from 'react';
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
import { sendRequest } from '../Request';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' },
}));

export default function HistoricalTrends () {
  const theme = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchHistory () {
      try {
        // pick a random offset up to one day (in seconds)
        const ONE_DAY = 24 * 60 * 60;
        const randomOffset = Math.floor(Math.random() * ONE_DAY);

        const history = await sendRequest(
          `ap/history/all?unit=sec&start_from=${randomOffset}`,
          'GET'
        );

        const mapped = history.map(item => ({
          timestamp: item.timestamp,
          temperature: item.temperature,
          humidity: item.humidity,
          light: item.light_intensity
        }));
        setData(mapped);
      } catch (err) {
        console.error('Failed to load history:', err);
        setError(err.message);
      }
    }
    fetchHistory();
  }, []);

  if (error) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="error">Error loading history: {error}</Typography>
      </GlassCard>
    );
  }
  if (!data) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading trends…</Typography>
      </GlassCard>
    );
  }

  // format ISO to HH:mm:ss
  const formatTime = iso =>
    new Date(iso).toLocaleTimeString(undefined, {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>Historical Trends</Typography>
      <ResponsiveContainer width="100%" height={625}>
        <ComposedChart
          data={data}
          margin={{ top: 10, right: 40, bottom: 60, left: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />

          <XAxis
            dataKey="timestamp"
            stroke={theme.palette.text.secondary}
            tickFormatter={formatTime}
            tick={{ angle: -45, textAnchor: 'end', fill: theme.palette.text.secondary }}
            height={60}
            label={{
              value: 'Time (HH:mm:ss)',
              position: 'insideBottomRight',
              offset: -5,
              fill: theme.palette.text.secondary
            }}
          />

          <YAxis
            yAxisId="left"
            orientation="left"
            stroke={theme.palette.text.secondary}
            label={{
              value: '°C / %',
              angle: -90,
              position: 'insideLeft',
              fill: theme.palette.text.secondary
            }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke={theme.palette.success.main}
            label={{
              value: 'Light (lx)',
              angle: 90,
              position: 'insideRight',
              fill: theme.palette.success.main
            }}
          />

          <Tooltip
            labelFormatter={formatTime}
            contentStyle={{ backgroundColor: theme.palette.background.paper }}
            labelStyle={{ color: theme.palette.text.primary }}
          />

          <Legend verticalAlign="top" height={36} />

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
          <Bar
            yAxisId="right"
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
