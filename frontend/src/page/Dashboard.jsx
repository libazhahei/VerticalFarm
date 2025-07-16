import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CssBaseline,
  Link,
  Chip,
  Switch,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Divider,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Toolbar
} from '@mui/material';
import {
  createTheme,
  ThemeProvider,
  styled
} from '@mui/material/styles';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip
} from 'recharts';
import HomeIcon from '@mui/icons-material/Home';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ChatIcon from '@mui/icons-material/Chat';
import SettingsIcon from '@mui/icons-material/Settings';
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
    // Base font size
    fontSize: 18,
    // Page title
    h4: { fontSize: '3rem', fontWeight: 700 },
    // Section titles
    subtitle1: { fontSize: '1.75rem', fontWeight: 600 },
    // Card headings
    h6: { fontSize: '1.5rem', fontWeight: 600 },
    // Body text / labels
    body1: { fontSize: '1.125rem', fontWeight: 500 },
    body2: { fontSize: '1rem', fontWeight: 500 },
    // Captions
    caption: { fontSize: '0.95rem', fontWeight: 500 },
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
      {/* Board title, larger & bold */}
      <Box display="flex" alignItems="center" mb={1}>
        <SensorsIcon color="primary" sx={{ mr: 1, fontSize: 36 }} />
        <Typography variant="h6" fontWeight="700">
          Board {board.id}
        </Typography>
      </Box>

      <Grid container spacing={1}>
        {[
          { label: 'Temp', value: `${board.temp}°C`, unit: true },
          { label: 'Humidity', value: `${board.humidity}%`, unit: true },
          { label: 'Light', value: `${board.light}lx`, unit: true }
        ].map((item) => (
          <React.Fragment key={item.label}>
            <Grid item xs={4}>
              <Typography variant="body2" color="text.secondary" fontWeight="500">
                {item.label}
              </Typography>
            </Grid>
            <Grid item xs={8}>
              {/* value in body1 (bigger) */}
              <Typography variant="body1" fontWeight="600">
                {item.value}
              </Typography>
            </Grid>
          </React.Fragment>
        ))}
        {['Fan', 'LED'].map((label) => {
          const status = board[label.toLowerCase()];
          return (
            <React.Fragment key={label}>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary" fontWeight="500">
                  {label}
                </Typography>
              </Grid>
              <Grid item xs={8}>
                <Chip
                  label={status ? 'On' : 'Off'}
                  size="medium"
                  color={status ? 'primary' : 'default'}
                  sx={{ fontWeight: 600 }}
                />
              </Grid>
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
  const size = 240;
  const strokeWidth = 20;
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
      { period: '12 hr', light_intensity: 30000 },
      { period: '12 hr', light_intensity: 1000 }
    ],
    data_source: [
      { name: 'Hortscience', link: 'https://example.com/hortscience' }
    ]
  };

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        AI Target
      </Typography>

      <Grid container spacing={1}>
        {/* Left column */}
        <Grid item xs={12} sm={6}>
          <Typography variant="body2"><strong>Day Temp:</strong> {target.day_temperature[0]}–{target.day_temperature[1]}°C</Typography>
          <Typography variant="body2"><strong>Night Temp:</strong> {target.night_temperature[0]}–{target.night_temperature[1]}°C</Typography>
          <Typography variant="body2"><strong>Humidity:</strong> {target.humidity[0]}–{target.humidity[1]}%</Typography>
        </Grid>

        {/* Right column */}
        <Grid item xs={12} sm={6}>
          <Typography variant="body2"><strong>PPFD:</strong> {target.PPFD[0]}–{target.PPFD[1]} µmol/m²/s</Typography>
          <Typography variant="body2"><strong>DLI:</strong> {target.DLI[0]}–{target.DLI[1]} mol/m²/day</Typography>
          <Typography variant="body2"><strong>Photoperiod:</strong></Typography>
          <Box component="ul" sx={{ pl: 2, my: 0 }}>
            {target.Photoperiod.map((p, i) => (
              <li key={i}>
                <Typography variant="body2">
                  {p.period} at {p.light_intensity.toLocaleString()}Lux
                </Typography>
              </li>
            ))}
          </Box>
        </Grid>
      </Grid>

      {/* Data source */}
      <Box sx={{ mt: 1 }}>
        <Typography variant="body2" fontWeight="bold">
          Data Source:
        </Typography>
        {target.data_source.map((src, i) => (
          <Link
            key={i}
            href={src.link}
            target="_blank"
            rel="noopener"
            variant="body2"
            display="block"
            sx={{ mt: 0.5 }}
          >
            {src.name}
          </Link>
        ))}
      </Box>
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

export function HistoricalTrends () {
  const historyData = [
    { timestamp: '08:00', val1: 22, val2: 24, val3: 20 },
    { timestamp: '10:00', val1: 23, val2: 25, val3: 21 },
    { timestamp: '12:00', val1: 24, val2: 26, val3: 22 },
    { timestamp: '14:00', val1: 23, val2: 27, val3: 21 }
  ];

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Historical Trends
      </Typography>
      <ResponsiveContainer width="100%" height={335}>
        <LineChart data={historyData}>
          {/* Use primary, secondary and success palette colors */}
          <Line
            type="monotone"
            dataKey="val1"
            stroke={theme.palette.primary.main}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="val2"
            stroke={theme.palette.secondary.main}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="val3"
            stroke={theme.palette.success.main}
            dot={false}
          />
          <XAxis
            dataKey="timestamp"
            stroke={theme.palette.text.secondary}
          />
          <YAxis
            stroke={theme.palette.text.secondary}
          />
          <Tooltip
            contentStyle={{ backgroundColor: theme.palette.background.paper }}
            labelStyle={{ color: theme.palette.text.primary }}
          />
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

const drawerWidth = 200;

export default function DashboardPage () {
  return (
    <ThemeProvider theme={theme}>
      {/* resets browser margins & sets body bgcolor */}
      <CssBaseline />

      {/* outer flex container with dark background */}
      <Box
        sx={{
          display: 'flex',
          minHeight: '100vh',
          bgcolor: 'background.default'
        }}
      >
        {/* ← permanent sidebar */}
        <Drawer
          variant="permanent"
          anchor="left"
          PaperProps={{
            sx: {
              width: drawerWidth,
              bgcolor: 'background.default',
              color: 'text.primary',
              borderRight: 'none'
            }
          }}
        >
          <Toolbar /> {/* spacer to match any AppBar height */}
          <List>
            <ListItem button>
              <ListItemIcon><HomeIcon /></ListItemIcon>
              <ListItemText primary="Overview" />
            </ListItem>
            <ListItem button>
              <ListItemIcon><DashboardIcon /></ListItemIcon>
              <ListItemText primary="Boards" />
            </ListItem>
            <ListItem button>
              <ListItemIcon><ChatIcon /></ListItemIcon>
              <ListItemText primary="Messages" />
            </ListItem>
            <ListItem button>
              <ListItemIcon><SettingsIcon /></ListItemIcon>
              <ListItemText primary="Settings" />
            </ListItem>
          </List>
        </Drawer>

        {/* → main content, shifted right & narrowed */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            ml: `${drawerWidth}px`, // push to the right
            width: `calc(100% - ${drawerWidth}px)`, // prevent overlap
            p: 3,
            bgcolor: 'background.default'
          }}
        >
          <Toolbar /> {/* optional spacer */}
          <Typography variant="h4" gutterBottom>
            System Overview
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <OverviewSection />
              <Box sx={{ mt: 2 }}>
                <HistoricalTrends />
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <GaugeInsightsSection />
            </Grid>
          </Grid>

          <Grid container spacing={2} sx={{ mt: -1 }}>
            <Grid item xs={12} md={6}>
              <DeviceManagement />
            </Grid>
            <Grid item xs={12} md={6}>
              <ManualControl />
            </Grid>
          </Grid>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
