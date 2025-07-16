import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Switch,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Divider
} from '@mui/material';
import { createTheme, ThemeProvider, styled } from '@mui/material/styles';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import SensorsIcon from '@mui/icons-material/Sensors';

// Custom theme with larger font sizes
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#00e5ff' },
    secondary: { main: '#d500f9' },
    background: { default: '#0d0d1a', paper: 'rgba(255,255,255,0.05)' },
    text: { primary: '#ffffff', secondary: 'rgba(255,255,255,0.7)' }
  },
  typography: {
    fontSize: 16,
    h4: { fontSize: '2.5rem' },
    h6: { fontSize: '1.75rem' },
    subtitle1: { fontSize: '1.25rem' },
    body1: { fontSize: '1rem' },
    body2: { fontSize: '0.95rem' },
    caption: { fontSize: '0.85rem' }
  },
  shape: { borderRadius: 8 }
});

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0, 0, 0, 0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

const overviewData = [
  { id: 1, temp: 25.3, humidity: 70, light: 750, fan: true, led: true },
  { id: 2, temp: 27.6, humidity: 50, light: 450, fan: false, led: false },
  { id: 3, temp: 24.8, humidity: 72, light: 722, fan: true, led: true },
  { id: 4, temp: 27.3, humidity: 65, light: 610, fan: false, led: false }
];

function BoardCard ({ board }) {
  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Box display="flex" alignItems="center" mb={1}>
        <SensorsIcon color="primary" sx={{ mr: 1, fontSize: 32 }} />
        <Typography variant="h6">Board {board.id}</Typography>
      </Box>
      <Grid container spacing={1}>
        {[
          { label: 'Temp', value: `${board.temp}°C` },
          { label: 'Humidity', value: `${board.humidity}%` },
          { label: 'Light', value: `${board.light} lx` }
        ].map((item) => (
          <React.Fragment key={item.label}>
            <Grid item xs={4}><Typography variant="body1" color="textSecondary">{item.label}</Typography></Grid>
            <Grid item xs={8}><Typography variant="body1">{item.value}</Typography></Grid>
          </React.Fragment>
        ))}
        {['Fan', 'LED'].map((label) => {
          const status = board[label.toLowerCase()];
          return (
            <React.Fragment key={label}>
              <Grid item xs={4}><Typography variant="body1" color="textSecondary">{label}</Typography></Grid>
              <Grid item xs={8}><Chip label={status ? 'On' : 'Off'} size="small" color={status ? 'primary' : 'default'} /></Grid>
            </React.Fragment>
          );
        })}
      </Grid>
    </GlassCard>
  );
}

function OverviewSection () {
  return (
    <Grid container spacing={2}>
      {overviewData.map((b) => (
        <Grid item xs={12} sm={6} md={6} key={b.id}><BoardCard board={b} /></Grid>
      ))}
    </Grid>
  );
}

function TemperatureGauge () {
  const temperature = 25.3;
  const size = 180;
  const strokeWidth = 16;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (temperature / 40) * circumference;

  return (
    <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
      <Box position="relative" mx="auto" width={size} height={size}>
        <svg viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#e0e0e0" strokeWidth={strokeWidth} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1976d2" strokeWidth={strokeWidth}
                  strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" />
        </svg>
        <Box position="absolute" top={0} left={0} width="100%" height="100%" display="flex" alignItems="center" justifyContent="center">
          <Typography variant="h4">{temperature}°C</Typography>
        </Box>
      </Box>
      <Typography variant="caption">Last control at 10:48 AM</Typography>
    </GlassCard>
  );
}

function AIInsights () {
  const insight = {
    summary: '降湿至<70% 牺牲：10%光合效率',
    reasoning: '蒸腾加速，湿热易致病害，根系耗氧↑ ↔ 光合↑，可能灯带发热',
    risk_level: 'high',
    control_priority: '避免病害风险 & 防热损伤',
    action_priority: [
      '风扇至100%强通风',
      'LED略调低至9,000 Lux'
    ],
    suggestion_time: new Date().toLocaleString()
  };

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>AI Insights</Typography>
      <Typography variant="body1"><strong>Summary:</strong> {insight.summary}</Typography>
      <Typography variant="body1" sx={{ mt: 0.5 }}><strong>Reasoning:</strong> {insight.reasoning}</Typography>
      <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="body1"><strong>Risk Level:</strong></Typography>
        <Chip label={insight.risk_level.toUpperCase()} color={insight.risk_level === 'high' ? 'secondary' : 'default'} />
      </Box>
      <Typography variant="body1" sx={{ mt: 1 }}><strong>Control Priority:</strong> {insight.control_priority}</Typography>
      <Typography variant="body1" sx={{ mt: 1 }}><strong>Action Priority:</strong></Typography>
      <ol>
        {insight.action_priority.map((act, idx) => (
          <li key={idx}><Typography variant="body2">{act}</Typography></li>
        ))}
      </ol>
      <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>Suggestion Time: {insight.suggestion_time}</Typography>
    </GlassCard>
  );
}

function AITarget () {
  const target = {
    day_temperature: [18, 20],
    night_temperature: [16, 18],
    humidity: [60, 70],
    PPFD: [200, 250],
    DLI: [12, 14],
    Photoperiod: [
      { period: '12 hr', light_intensity: 30000 },
      { period: '12 hr', light_intensity: 1000 }
    ],
    data_source: [
      { name: 'Hortscience', link: 'https://example.com/hortscience' }
    ]
  };
  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>AI Target</Typography>
      <Grid container spacing={1}>
        {Object.entries(target).map(([key, val]) => (
          <Grid item xs={12} sm={6} key={key}>
            <Typography variant="body1"><strong>{key.replace('_', ' ').toUpperCase()}:</strong> {Array.isArray(val) ? JSON.stringify(val) : val.toString()}</Typography>
          </Grid>
        ))}
      </Grid>
    </GlassCard>
  );
}

function GaugeInsightsSection () {
  return (
    <Grid container spacing={2} direction="column">
      <Grid item><TemperatureGauge /></Grid>
      <Grid item><AIInsights /></Grid>
      <Grid item><AITarget /></Grid>
    </Grid>
  );
}

function HistoricalTrends () {
  const historyData = [
    { timestamp: '08:00', val1: 22, val2: 24, val3: 20 },
    { timestamp: '10:00', val1: 23, val2: 25, val3: 21 },
    { timestamp: '12:00', val1: 24, val2: 26, val3: 22 },
    { timestamp: '14:00', val1: 23, val2: 27, val3: 21 }
  ];

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>Historical Trends</Typography>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={historyData}>
          <Line type="monotone" dataKey="val1" stroke="#1976d2" dot={false} />
          <Line type="monotone" dataKey="val2" stroke="#d32f2f" dot={false} />
          <Line type="monotone" dataKey="val3" stroke="#388e3c" dot={false} />
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip />
        </LineChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}

function DeviceManagement () {
  const devices = [
    { id: 1, status: 'Online', last: '10:45 AM', ip: '192.160.1.10' },
    { id: 2, status: 'Offline', last: '10:35 AM', ip: '192.18.1.5' },
    { id: 3, status: 'Online', last: '10:50 AM', ip: '192.10.2.7' }
  ];

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
          {devices.map((d) => (
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

function ManualControl () {
  const [mode, setMode] = useState('auto');
  const [fan, setFan] = useState('off');
  const [led, setLed] = useState('off');

  return (
    <GlassCard elevation={1} sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <CardContent>
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
                    <Typography
                      sx={{ cursor: 'pointer', color: value === options[0] ? 'textSecondary' : 'textPrimary' }}
                      onClick={() => setter(options[0])}
                    >{options[0].charAt(0).toUpperCase() + options[0].slice(1)}</Typography>
                    <Switch size="small" checked={value === options[1]} onChange={() => setter(value === options[1] ? options[0] : options[1])}/>
                    <Typography
                      sx={{ cursor: 'pointer', color: value === options[1] ? 'textPrimary' : 'textSecondary' }}
                      onClick={() => setter(options[1])}
                    >{options[1].charAt(0).toUpperCase() + options[1].slice(1)}</Typography>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
      <Divider />
      <Box sx={{ p: 1 }}>
        <Typography variant="caption">Status: {mode === 'auto' ? 'Automatic' : 'Manual'} | Fan: {fan} | LED: {led}</Typography>
      </Box>
    </GlassCard>
  );
}

export default function DashboardPage () {
  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ p: 3, bgcolor: 'background.default', minHeight: '100vh' }}>
        <Typography variant="h4" gutterBottom color="text.primary">
          System Overview
        </Typography>

        {/* Top & History: boards + history on left, gauge/insights/target on right */}
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <OverviewSection />
            <Box sx={{ mt: 2 }}><HistoricalTrends /></Box>
          </Grid>
          <Grid item xs={12} md={4}><GaugeInsightsSection /></Grid>
        </Grid>

        {/* Device Management & Manual Control side‑by‑side */}
        <Grid container spacing={2} sx={{ mt: 2 }}>
          <Grid item xs={12} md={6}><DeviceManagement /></Grid>
          <Grid item xs={12} md={6}><ManualControl /></Grid>
        </Grid>
      </Box>
    </ThemeProvider>
  );
}
