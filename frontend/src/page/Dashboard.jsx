import React, { useEffect, useState } from 'react';
import { Box, CssBaseline, Typography, Grid, Toolbar, ThemeProvider, Button, Paper } from '@mui/material';
import Sidebar from '../components/SideBar';
import OverviewSection from '../components/OverviewSection';
import HistoricalTrends from '../components/HistoricalTrends';
import GaugeInsightsSection from '../components/GaugeInsightsSection';
import DeviceManagement from '../components/DeviceManagement';
import ManualControl from '../components/ManualControl';
import theme from '../theme';
import PlantInfoDialog from '../components/PlantInfoDialog';

const fakeData = {
  timestamp: '2025-07-16T10:00:00Z',
  boards: [
    { board_id: 1, temperature: 24.5, humidity: 70, light: 500, fan: 1, led: 0, online: true },
    { board_id: 2, temperature: 26.1, humidity: 65, light: 450, fan: 0, led: 1, online: true },
    { board_id: 3, temperature: 23.8, humidity: 72, light: 610, fan: 1, led: 1, online: false },
    { board_id: 4, temperature: 23.8, humidity: 72, light: 610, fan: 1, led: 1, online: false }
  ]
};

const historyData = [
  { timestamp: '08:00', val1: 22, val2: 24, val3: 20 },
  { timestamp: '10:00', val1: 23, val2: 25, val3: 21 },
  { timestamp: '12:00', val1: 24, val2: 26, val3: 22 },
  { timestamp: '14:00', val1: 23, val2: 27, val3: 21 }
];

export default function DashboardPage () {
  const drawerWidth = 200;
  const [boards, setBoards] = useState([]);
  const [timestamp, setTimestamp] = useState('');
  const [plantDialogOpen, setPlantDialogOpen] = useState(false);
  const [plantInfo, setPlantInfo] = useState(null);

  useEffect(() => {
    // Normally: fetch realtime from backend
    // const fetchRealtime = async () => {
    //   const data = await sendRequest('api/realtime', 'GET');
    //   setTimestamp(data.timestamp);
    //   setBoards(data.boards);
    // };
    // fetchRealtime();

    // Using fake data for now
    setTimestamp(fakeData.timestamp);
    setBoards(fakeData.boards);

    // sendRequest('api/user/plant_info', 'GET')
    //   .then(data => setPlantInfo(data))
    //   .catch(() => setPlantInfo({
    //     name: 'Lettuce',
    //     stage: 'vegetative',
    //     remark: 'Leaf slightly yellow, need to observe'
    //   }));
    setPlantInfo({
      name: 'Lettuce',
      stage: 'vegetative',
      remark: 'Leaf slightly yellow, need to observe'
    });
  }, []);
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
              System Overview
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <Button
                variant="outlined"
                size="small"
                sx={{ ml: 2 }}
                onClick={() => setPlantDialogOpen(true)}
              >
                Record Plant Information
              </Button>
              {plantInfo && (
                <Paper elevation={0} sx={{ p: 1, bgcolor: 'grey.100', minWidth: 180 }}>
                  <Typography variant="caption" color="text.secondary">current plant</Typography>
                  <Typography variant="body2" noWrap>
                    {plantInfo.name || '-'} / {plantInfo.stage || '-'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {plantInfo.remark || '-'}
                  </Typography>
                </Paper>
              )}
            </Box>
          </Box>
          {timestamp && (
            <Typography variant="caption">Last updated: {timestamp}</Typography>
          )}

          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={8}>
              <OverviewSection boards={boards} />
              <Box sx={{ mt: 2 }}>
                <HistoricalTrends data={historyData} />
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              {/* Only pass target; GaugeInsightsSection fetches its own data */}
              <GaugeInsightsSection />
            </Grid>
          </Grid>

<Grid
  container
  spacing={2}
  sx={{
    mt: 1,
    alignItems: 'stretch' // make children stretch to same height
  }}
>
  <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
    <DeviceManagement sx={{ flexGrow: 1 }} />
  </Grid>
  <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
    <ManualControl sx={{ flexGrow: 1 }} />
  </Grid>
</Grid>
        </Box>
      </Box>
      <PlantInfoDialog open={plantDialogOpen} onClose={() => setPlantDialogOpen(false)} />
    </ThemeProvider>
  );
}
