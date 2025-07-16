import React from 'react';
import { Card, Table, TableHead, TableRow, TableCell, TableBody, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function DeviceManagement ({ devices }) {
  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>Device Management</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Last Seen</TableCell>
            <TableCell>IP</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {devices.map(d => (
            <TableRow key={d.id}>
              <TableCell>{d.id}</TableCell>
              <TableCell>{d.status}</TableCell>
              <TableCell>{d.last}</TableCell>
              <TableCell>{d.ip}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </GlassCard>
  );
}
