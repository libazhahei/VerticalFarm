import React from 'react';
import { Grid } from '@mui/material';
import TemperatureGauge from './TemperatureGauge';
import AIInsights from './AIInsights';
import AITarget from './AITarget';

export default function GaugeInsightsSection ({ insight, target }) {
  return (
    <Grid container spacing={2} direction="column">
      {/* TemperatureGauge now uses WeatherAPI.com */}
      <Grid item>
        <TemperatureGauge
          city="Sydney,AU"
          apiKey="a1ea5d212b5f49e7841125640251607"
        />
      </Grid>

      {/* the rest of your AI panels */}
      <Grid item>
        <AIInsights insight={insight} />
      </Grid>
      <Grid item>
        <AITarget target={target} />
      </Grid>
    </Grid>
  );
}
