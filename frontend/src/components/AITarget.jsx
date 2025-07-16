import React from 'react';
import { Box, Typography, Grid, Link, Card } from '@mui/material';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function AITarget ({ target }) {
  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>AI Target</Typography>
      <Grid container spacing={1}>
        <Grid item xs={12} sm={6}>
          <Typography variant="body2"><strong>Day Temp:</strong> {target.day_temperature[0]}–{target.day_temperature[1]}°C</Typography>
          <Typography variant="body2"><strong>Night Temp:</strong> {target.night_temperature[0]}–{target.night_temperature[1]}°C</Typography>
          <Typography variant="body2"><strong>Humidity:</strong> {target.humidity[0]}–{target.humidity[1]}%</Typography>
        </Grid>
        <Grid item xs={12} sm={6}>
          <Typography variant="body2"><strong>PPFD:</strong> {target.PPFD[0]}–{target.PPFD[1]} µmol/m²/s</Typography>
          <Typography variant="body2"><strong>DLI:</strong> {target.DLI[0]}–{target.DLI[1]} mol/m²/day</Typography>
          <Typography variant="body2"><strong>Photoperiod:</strong></Typography>
          <Box component="ul" sx={{ pl: 2, my: 0 }}>
            {target.Photoperiod.map((p, i) => (
              <li key={i}>
                <Typography variant="body2">{p.period} at {p.light_intensity.toLocaleString()} Lux</Typography>
              </li>
            ))}
          </Box>
        </Grid>
      </Grid>
      <Box sx={{ mt: 1 }}>
        <Typography variant="body2" fontWeight="bold">Data Source:</Typography>
        {target.data_source.map((src, i) => (
          <Link key={i} href={src.link} target="_blank" rel="noopener" variant="body2" display="block" sx={{ mt: 0.5 }}>
            {src.name}
          </Link>
        ))}
      </Box>
    </GlassCard>
  );
}
