import React from 'react';
import { Box, Grid, Typography, Chip, Card } from '@mui/material';
import SensorsIcon from '@mui/icons-material/Sensors';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function BoardCard ({ board }) {
  const metrics = [
    { label: 'Temp', value: `${board.temp}°C` },
    { label: 'Humidity', value: `${board.humidity}%` },
    { label: 'Light', value: `${board.light}lx` }
  ];
  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Box display="flex" alignItems="center" mb={1}>
        <SensorsIcon color="primary" sx={{ mr: 1, fontSize: 36 }} />
        <Typography variant="h6">Board {board.id}</Typography>
      </Box>
      <Grid container spacing={1}>
        {metrics.map(item => (
          <React.Fragment key={item.label}>
            <Grid item xs={4}>
              <Typography variant="body2" color="text.secondary">{item.label}</Typography>
            </Grid>
            <Grid item xs={8}>
              <Typography variant="body1">{item.value}</Typography>
            </Grid>
          </React.Fragment>
        ))}
        {['fan', 'led'].map(key => (
          <React.Fragment key={key}>
            <Grid item xs={4}>
              <Typography variant="body2" color="text.secondary">{key.toUpperCase()}</Typography>
            </Grid>
            <Grid item xs={8}>
              <Chip
                label={board[key] ? 'On' : 'Off'}
                color={board[key] ? 'primary' : 'default'}
                sx={{ fontWeight: 600 }}
              />
            </Grid>
          </React.Fragment>
        ))}
      </Grid>
    </GlassCard>
  );
}
