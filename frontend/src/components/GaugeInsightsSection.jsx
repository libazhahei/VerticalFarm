// src/components/GaugeInsightsSection.jsx
import React from 'react';
import { Grid } from '@mui/material';
import TemperatureGauge from './TemperatureGauge';
import AIInsights from './AIInsights';
import AITarget from './AITarget';

export default function GaugeInsightsSection () {
  return (
    <Grid container spacing={2} direction="column">
      {/* TemperatureGauge now fetches internally */}
      <Grid item>
        <TemperatureGauge
          city="Sydney,AU"
          apiKey="a1ea5d212b5f49e7841125640251607"
        />
      </Grid>

      {/* AIInsights now fetches internally */}
      <Grid item>
        <AIInsights />
      </Grid>

      {/* AITarget still takes its static config */}
      <Grid item>
        <AITarget />
      </Grid>
    </Grid>
  );
}
