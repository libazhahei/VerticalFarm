import React from 'react';
import { Grid } from '@mui/material';
import BoardCard from './BoardCard';

const overviewData = [
  { id: 1, temp: 25.3, humidity: 70, light: 750, fan: true, led: true },
  { id: 2, temp: 27.6, humidity: 50, light: 450, fan: false, led: false },
  { id: 3, temp: 24.8, humidity: 72, light: 722, fan: true, led: true },
  { id: 4, temp: 27.3, humidity: 65, light: 610, fan: false, led: false }
];

export default function OverviewSection () {
  return (
    <Grid container spacing={2}>
      {overviewData.map(b => (
        <Grid item xs={12} sm={6} key={b.id}>
          <BoardCard board={b} />
        </Grid>
      ))}
    </Grid>
  );
}
