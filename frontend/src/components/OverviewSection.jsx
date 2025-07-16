import React from 'react';
import { Grid, Typography } from '@mui/material';
import BoardCard from './BoardCard';

export default function OverviewSection ({ boards }) {
  if (!boards) return <Typography>Loading...</Typography>;
  return (
    <Grid container spacing={2}>
      {boards.map(b => (
        <Grid item xs={12} sm={6} key={b.board_id}>
          <BoardCard board={b} />
        </Grid>
      ))}
    </Grid>
  );
}
