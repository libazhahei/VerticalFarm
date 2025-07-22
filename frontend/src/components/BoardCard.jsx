// src/components/BoardCard.jsx
import React from 'react';
import { Box, Grid, Typography, Chip, Card } from '@mui/material';
import SensorsIcon from '@mui/icons-material/Sensors';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme, offline }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)', // always default
  boxShadow: '0 4px 12px rgba(0,0,0,0.08)', // always default
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  opacity: offline ? 0.6 : 1, // only opacity changes
  '&:hover': { transform: 'scale(1.04)' }
}));

export default function BoardCard ({ board }) {
  const isOffline = !board.online;

  const metrics = [
    { label: 'Temp', value: isOffline || board.temperature == null ? '—' : `${board.temperature}°C` },
    { label: 'Humidity', value: isOffline || board.humidity == null ? '—' : `${board.humidity}%` },
    { label: 'Light', value: isOffline || board.light == null ? '—' : `${board.light} lx` }
  ];

  const controls = ['fan', 'led'].map(key => ({
    label: key.toUpperCase(),
    status: isOffline || board[key] == null ? null : board[key]
  }));

  return (
    <GlassCard elevation={1} offline={isOffline} sx={{ p: 3, minHeight: 200 }}>
      <Box display="flex" alignItems="center" mb={2}>
        <SensorsIcon
          color={isOffline ? 'disabled' : 'primary'} // dim the icon
          sx={{ mr: 1, fontSize: 36 }}
        />
        <Typography variant="h6">Board {board.board_id}</Typography>
        {isOffline && (
          <Chip
            label="Offline"
            color="default" // keep chip neutral, or use 'warning'
            size="small"
            sx={{ ml: 1 }}
          />
        )}
      </Box>

      <Grid container spacing={1}>
        {metrics.map(({ label, value }) => (
          <React.Fragment key={label}>
            <Grid item xs={4}>
              <Typography variant="body2" color="text.secondary">
                {label}
              </Typography>
            </Grid>
            <Grid item xs={8}>
              <Typography variant="body1">{value}</Typography>
            </Grid>
          </React.Fragment>
        ))}

        {controls.map(({ label, status }) => (
          <React.Fragment key={label}>
            <Grid item xs={4}>
              <Typography variant="body2" color="text.secondary">
                {label}
              </Typography>
            </Grid>
            <Grid item xs={8}>
              <Chip
                label={status === 1 ? 'On' : status === 0 ? 'Off' : '—'}
                color={status === 1 ? 'primary' : 'default'}
                sx={{ fontWeight: 600 }}
              />
            </Grid>
          </React.Fragment>
        ))}
      </Grid>
    </GlassCard>
  );
}
