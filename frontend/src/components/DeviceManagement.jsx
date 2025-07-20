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
// import { sendRequest } from '../Request';

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
  //   const [error, setError] = useState(null);

  useEffect(() => {
    // Real API call (commented until ready):
    // const fetchDevices = async () => {
    //   try {
    //     const data = await sendRequest('api/devices', 'GET');
    //     setDevices(data.devices);
    //   } catch (err) {
    //     console.error(err);
    //     setError(err.message);
    //   }
    // };
    // fetchDevices();

    // Fake data for layout
    setDevices([
      { board_id: 1, status: 'online', last_seen: '10:45 AM', uuid: 'A1B2-C3D4-E5F6' },
      { board_id: 2, status: 'offline', last_seen: '10:35 AM', uuid: 'B2C3-D4E5-F6A1' },
      { board_id: 3, status: 'online', last_seen: '10:50 AM', uuid: 'C3D4-E5F6-A1B2' }
    ]);
  }, []);

  //   if (error) {
  //     return (
  //       <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
  //         <Typography color="error">Error loading devices: {error}</Typography>
  //       </GlassCard>
  //     );
  //   }
  if (!devices) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading devices…</Typography>
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
        height: '100%', // fill the parent
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
              <TableCell sx={{ fontWeight: 'bold' }}>UUID</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {devices.map((d) => (
              <TableRow
                key={d.board_id}
                sx={{
                  '&:nth-of-type(odd)': { backgroundColor: 'rgba(255,255,255,0.02)' }
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
                <TableCell>{d.last_seen}</TableCell>
                <TableCell>{d.uuid}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </GlassCard>
  );
}
