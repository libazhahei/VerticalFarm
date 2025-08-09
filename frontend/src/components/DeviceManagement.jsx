// src/components/DeviceManagement.jsx
import React, { useState, useEffect } from 'react';
import {
  Card,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  Typography,
  Paper
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { sendRequest } from '../Request';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function DeviceManagement (props) {
  const [devices, setDevices] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const data = await sendRequest('api/devices', 'GET');

        // handle both shapes: Array or { devices: Array }
        const list = Array.isArray(data)
          ? data
          : Array.isArray(data.devices)
            ? data.devices
            : [];

        setDevices(list);
      } catch (err) {
        console.error(err);
        setError(err.message || 'Unknown error');
      }
    };
    fetchDevices();
  }, []);

  if (error) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="error">
          Error loading devices: {error}
        </Typography>
      </GlassCard>
    );
  }

  if (devices === null) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading devices…</Typography>
      </GlassCard>
    );
  }

  if (devices.length === 0) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>No devices found.</Typography>
      </GlassCard>
    );
  }

  return (
    <GlassCard
      elevation={1}
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        ...props.sx
      }}
    >
      <Typography variant="h6" gutterBottom>
        Device Management
      </Typography>

      <TableContainer
        component={Paper}
        elevation={0}
        sx={{ background: 'transparent', mt: 1 }}
      >
        <Table size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
              <TableCell sx={{ fontWeight: 'bold' }}>Board ID</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Last Seen</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>MAC Address</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {devices.map((d) => (
              <TableRow
                key={d.board_id}
                sx={{
                  '&:nth-of-type(odd)': {
                    backgroundColor: 'rgba(255,255,255,0.02)'
                  }
                }}
              >
                <TableCell>{d.board_id}</TableCell>
                <TableCell>
                  <Chip
                    label={d.status}
                    size="small"
                    color={d.status === 'online' ? 'success' : 'default'}
                    sx={{ textTransform: 'capitalize', fontWeight: 600 }}
                  />
                </TableCell>
                <TableCell>
                  {/* convert Unix timestamp (seconds) to human time */}
                  {new Date(d.last_seen * 1000).toLocaleString()}
                </TableCell>
                <TableCell>{d.ip_address}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </GlassCard>
  );
}
