import React from 'react';
import { Box, CssBaseline, Typography, Grid, Toolbar, ThemeProvider } from '@mui/material';
import Sidebar from '../components/SideBar';
import OverviewSection from '../components/OverviewSection';
import HistoricalTrends from '../components/HistoricalTrends';
import GaugeInsightsSection from '../components/GaugeInsightsSection';
import DeviceManagement from '../components/DeviceManagement';
import ManualControl from '../components/ManualControl';
import theme from '../theme';

// const overviewData = [
//   { id: 1, temp: 25.3, humidity: 70, light: 750, fan: true, led: true },
//   { id: 2, temp: 27.6, humidity: 50, light: 450, fan: false, led: false },
//   { id: 3, temp: 24.8, humidity: 72, light: 722, fan: true, led: true },
//   { id: 4, temp: 27.3, humidity: 65, light: 610, fan: false, led: false }
// ];

const historyData = [
  { timestamp: '08:00', val1: 22, val2: 24, val3: 20 },
  { timestamp: '10:00', val1: 23, val2: 25, val3: 21 },
  { timestamp: '12:00', val1: 24, val2: 26, val3: 22 },
  { timestamp: '14:00', val1: 23, val2: 27, val3: 21 }
];

const devices = [
  { id: 1, status: 'Online', last: '10:45 AM', ip: '192.160.1.10' },
  { id: 2, status: 'Offline', last: '10:35 AM', ip: '192.18.1.5' },
  { id: 3, status: 'Online', last: '10:50 AM', ip: '192.10.2.7' }
];

const insight = {
  temperature: 25.3,
  summary: '降湿至<70% 牺牲：10%光合效率',
  reasoning: '蒸腾加速，湿热易致病害，根系耗氧↑ ↔ 光合↑，可能灯带发热',
  risk_level: 'high',
  control_priority: '避免病害风险 & 防热损伤',
  action_priority: ['风扇至100%强通风', 'LED略调低至9,000 Lux'],
  suggestion_time: new Date().toLocaleString()
};

const target = {
  day_temperature: [18, 20],
  night_temperature: [16, 18],
  humidity: [60, 70],
  PPFD: [200, 250],
  DLI: [12, 14],
  Photoperiod: [{ period: '12 hr', light_intensity: 30000 }, { period: '12 hr', light_intensity: 1000 }],
  data_source: [{ name: 'Hortscience', link: 'https://example.com/hortscience' }]
};

export default function DashboardPage () {
  const drawerWidth = 200;
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
          <Typography variant="h4" gutterBottom>System Overview</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <OverviewSection />
              <Box sx={{ mt: 2 }}><HistoricalTrends data={historyData} /></Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <GaugeInsightsSection insight={insight} target={target} />
            </Grid>
          </Grid>
          <Grid container spacing={2} sx={{ mt: -1 }}>
            <Grid item xs={12} md={6}><DeviceManagement devices={devices} /></Grid>
            <Grid item xs={12} md={6}><ManualControl /></Grid>
          </Grid>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
