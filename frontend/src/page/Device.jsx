import React, { useEffect, useState } from 'react';
import { Box, Typography, Paper, Button, Chip, CircularProgress, Alert, CssBaseline, Toolbar, ThemeProvider } from '@mui/material';
import Sidebar from '../components/SideBar';
import theme from '../theme';

export default function DevicePage () {
  const drawerWidth = 200;
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchDevices = async () => {
    setLoading(true);
    setError('');
    setDevices([
      { board_id: 1, status: 'online', last_seen: '10:45 AM', uuid: 'A1B2-C3D4-E5F6' },
      { board_id: 2, status: 'offline', last_seen: '10:35 AM', uuid: 'B2C3-D4E5-F6A1' },
      { board_id: 3, status: 'online', last_seen: '10:50 AM', uuid: 'C3D4-E5F6-A1B2' }
    ]);
    setLoading(false);
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const offlineCount = devices.filter(d => d.status === 'offline').length;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
        <Sidebar />
        <Box
          component="main"
          sx={{ flexGrow: 1, ml: `${drawerWidth}px`, width: `calc(100% - ${drawerWidth}px)`, p: 3 }}
        >
          <Toolbar />
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
            <Typography variant="h4" gutterBottom>
              Device Management
            </Typography>
            <Button variant="outlined" onClick={fetchDevices} disabled={loading}>
              {loading ? <CircularProgress size={20} /> : 'Refresh'}
            </Button>
          </Box>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {offlineCount > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {offlineCount} devices are offline, please check!
            </Alert>
          )}
          <Paper sx={{ p: 2 }}>
            <Box display="flex" fontWeight={600} mb={1}>
              <Box width={100}>Board ID</Box>
              <Box width={100}>Status</Box>
              <Box width={180}>Last Seen</Box>
              <Box width={160}>UUID</Box>
            </Box>
            {devices.length === 0
              ? <Typography color="text.secondary">No devices</Typography>
              : devices.map(d => (
                <Box key={d.board_id} display="flex" alignItems="center" mb={1}>
                  <Box width={100}>{d.board_id}</Box>
                  <Box width={100}>
                    <Chip
                      label={d.status}
                      size="small"
                      color={d.status === 'online' ? 'success' : 'default'}
                      sx={{ textTransform: 'capitalize', fontWeight: 600 }}
                    />
                  </Box>
                  <Box width={180}>{d.last_seen || '-'}</Box>
                  <Box width={160}>{d.uuid || '-'}</Box>
                </Box>
              ))}
          </Paper>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
