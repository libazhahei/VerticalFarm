// src/components/AITarget.jsx
import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Link,
  Card,
  CardHeader,
  Divider,
  Chip
} from '@mui/material';
import { styled } from '@mui/material/styles';
// import { sendRequest } from '../Request';
// import { sendRequest } from '../api/Request';  // keep for real API

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function AITarget () {
  const [target, setTarget] = useState(null);

  useEffect(() => {
    const fake = {
      day_temperature: [18, 20],
      night_temperature: [16, 18],
      humidity: [60, 70],
      PPFD: [200, 250],
      DLI: [12, 14],
      Photoperiod: [
        { period: '12 hr', light_intensity: 30000 },
        { period: '12 hr', light_intensity: 1000 }
      ],
      data_source: [
        { name: 'Hortscience', link: 'https://example.com/hortscience' }
      ]
    };
    setTarget(fake);
  }, []);

  if (!target) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading AI target…</Typography>
      </GlassCard>
    );
  }

  return (
    <GlassCard elevation={1}>
      <CardHeader
        title="AI Target"
        titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
        sx={{ pb: 0 }}
      />
      <Divider />
      <Box sx={{ p: 2 }}>
        {/** Temperature & Humidity Section **/}
        {[
          { label: 'Day Temp', value: `${target.day_temperature[0]}–${target.day_temperature[1]} °C` },
          { label: 'Night Temp', value: `${target.night_temperature[0]}–${target.night_temperature[1]} °C` },
          { label: 'Humidity', value: `${target.humidity[0]}–${target.humidity[1]} %` },
        ].map(item => (
          <Box key={item.label} display="flex" justifyContent="space-between" mb={1}>
            <Typography variant="body1" fontWeight="bold">{item.label}</Typography>
            <Typography variant="body1">{item.value}</Typography>
          </Box>
        ))}

        <Divider sx={{ my: 1 }} />

        {/** Light & DLI Section **/}
        {[
          { label: 'PPFD', value: `${target.PPFD[0]}–${target.PPFD[1]} µmol/m²/s` },
          { label: 'DLI', value: `${target.DLI[0]}–${target.DLI[1]} mol/m²/day` },
        ].map(item => (
          <Box key={item.label} display="flex" justifyContent="space-between" mb={1}>
            <Typography variant="body1" fontWeight="bold">{item.label}</Typography>
            <Typography variant="body1">{item.value}</Typography>
          </Box>
        ))}

        <Divider sx={{ my: 1 }} />

        {/** Photoperiod Section **/}
        <Typography variant="body1" fontWeight="bold" gutterBottom>
          Photoperiod
        </Typography>
        <Box component="ul" sx={{ pl: 2, mb: 1 }}>
          {target.Photoperiod.map((p, i) => (
            <li key={i}>
              <Typography variant="body2">
                <strong>{p.period}:</strong> {p.light_intensity.toLocaleString()} Lux
              </Typography>
            </li>
          ))}
        </Box>

        <Divider sx={{ my: 1 }} />

        {/** Data Source Section **/}
        <Typography variant="body1" fontWeight="bold" gutterBottom>
          Data Source
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {target.data_source.map((src, i) => (
            <Chip
              key={i}
              label={src.name}
              component={Link}
              href={src.link}
              clickable
              underline="none"
            />
          ))}
        </Box>
      </Box>
    </GlassCard>
  );
}
