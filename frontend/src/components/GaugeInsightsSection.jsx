import React from 'react';
import { Grid } from '@mui/material';
import TemperatureGauge from './TemperatureGauge';
import AIInsights from './AIInsights';
import AITarget from './AITarget';

export default function GaugeInsightsSection ({ insight, target }) {
  return (
    <Grid container spacing={2} direction="column">
      <Grid item><TemperatureGauge temperature={insight.temperature} /></Grid>
      <Grid item><AIInsights insight={insight} /></Grid>
      <Grid item><AITarget target={target} /></Grid>
    </Grid>
  );
}
