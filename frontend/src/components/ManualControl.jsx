import React, { useState } from 'react';
import { Card, Table, TableBody, TableRow, TableCell, Typography, Box, Switch, Divider } from '@mui/material';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function ManualControl () {
  const [mode, setMode] = useState('auto');
  const [fan, setFan] = useState('off');
  const [led, setLed] = useState('off');

  return (
    <GlassCard elevation={1} sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box p={2}>
        <Typography variant="subtitle1" gutterBottom>Manual Control</Typography>
        <Table size="small">
          <TableBody>
            {[
              { label: 'Mode', value: mode, setter: setMode, options: ['auto', 'manual'] },
              { label: 'Fan', value: fan, setter: setFan, options: ['off', 'on'] },
              { label: 'LED', value: led, setter: setLed, options: ['off', 'on'] }
            ].map(({ label, value, setter, options }) => (
              <TableRow key={label}>
                <TableCell>{label}</TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography sx={{ cursor: 'pointer', color: value === options[0] ? 'text.secondary' : 'text.primary' }} onClick={() => setter(options[0])}>
                      {options[0]}
                    </Typography>
                    <Switch size="small" checked={value === options[1]} onChange={() => setter(value === options[1] ? options[0] : options[1])} />
                    <Typography sx={{ cursor: 'pointer', color: value === options[1] ? 'text.primary' : 'text.secondary' }} onClick={() => setter(options[1])}>
                      {options[1]}
                    </Typography>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      <Divider />
      <Box p={1}>
        <Typography variant="caption">
          Status: {mode === 'auto' ? 'Automatic' : 'Manual'} | Fan: {fan} | LED: {led}
        </Typography>
      </Box>
    </GlassCard>
  );
}
