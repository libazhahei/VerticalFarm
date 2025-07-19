// src/components/AITarget.jsx
import React, { useState, useEffect } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Grid,
  Typography,
  Divider,
  Box,
  Link,
  Chip
} from '@mui/material';
import { styled } from '@mui/material/styles';
// import { sendRequest } from '../api/Request'; // keep for real API

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  borderRadius: theme.shape.borderRadius,
}));

export default function AITarget () {
  const [target, setTarget] = useState(null);

  useEffect(() => {
    // Real API call (commented until ready):
    // async function fetchTarget() {
    //   const data = await sendRequest('api/ai/target', 'GET');
    //   setTarget(data);
    // }
    // fetchTarget();

    // —— Fake data for now ——
    setTarget({
      day_temperature: [18, 20],
      night_temperature: [16, 18],
      humidity: [60, 70],
      PPFD: [200, 250],
      DLI: [12, 14],
      Photoperiod: [
        { period: '12 hr', light_intensity: 30000 },
        { period: '12 hr', light_intensity: 1000 }
      ],
      data_source: [{ name: 'Hortscience', link: 'https://example.com/hortscience' }]
    });
  }, []);

  if (!target) {
    return (
      <GlassCard elevation={1}>
        <CardContent sx={{ py: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Loading AI Target…
          </Typography>
        </CardContent>
      </GlassCard>
    );
  }

  return (
    <GlassCard elevation={1}>
      <CardHeader
        title="AI Target"
        titleTypographyProps={{ variant: 'h6', fontWeight: 700 }}
        sx={{ pb: 0 }}
      />
      <Divider />
      <CardContent sx={{ pt: 1, pb: 2 }}>
        <Grid container spacing={1}>
          {[
            { label: 'Day Temp', value: `${target.day_temperature[0]}–${target.day_temperature[1]}°C` },
            { label: 'Night Temp', value: `${target.night_temperature[0]}–${target.night_temperature[1]}°C` },
            { label: 'Humidity', value: `${target.humidity[0]}–${target.humidity[1]}%` },
            { label: 'PPFD', value: `${target.PPFD[0]}–${target.PPFD[1]} µmol/m²/s` },
            { label: 'DLI', value: `${target.DLI[0]}–${target.DLI[1]} mol/m²/day` }
          ].map((item) => (
            <Grid item xs={6} key={item.label}>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontWeight: 600 }}
              >
                {item.label}
              </Typography>
              <Typography
                variant="body2"
                sx={{ fontWeight: 700, mt: 0.25 }}
              >
                {item.value}
              </Typography>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 1 }} />

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontWeight: 600, mb: 0.5 }}
        >
          Photoperiod
        </Typography>
        <Box component="ul" sx={{ pl: 2, mb: 1, mt: 0 }}>
          {target.Photoperiod.map((p, i) => (
            <li key={i}>
              <Typography variant="body2">
                <strong>{p.period}:</strong> {p.light_intensity.toLocaleString()} Lux
              </Typography>
            </li>
          ))}
        </Box>

        <Divider sx={{ my: 1 }} />

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontWeight: 600, mb: 0.5 }}
        >
          Data Source
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {target.data_source.map((src, i) => (
            <Chip
              key={i}
              label={src.name}
              size="small"
              component={Link}
              href={src.link}
              clickable
              variant="outlined"
              sx={{ fontWeight: 600 }}
            />
          ))}
        </Box>
      </CardContent>
    </GlassCard>
  );
}
