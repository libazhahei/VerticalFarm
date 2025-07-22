// src/pages/DashboardPage.jsx
import React, { useEffect, useState } from 'react';
import {
  Box,
  CssBaseline,
  Typography,
  Grid,
  Toolbar,
  ThemeProvider,
  Button,
  Paper,
  Chip,
  Avatar,
  Divider,
  useTheme,
  alpha
} from '@mui/material';
import {
  Edit as EditIcon,
  LocalFlorist as LocalFloristIcon,
  Timeline as StageIcon,
  AccessTime as TimeIcon
} from '@mui/icons-material';
import Sidebar from '../components/SideBar';
import OverviewSection from '../components/OverviewSection';
import HistoricalTrends from '../components/HistoricalTrends';
import GaugeInsightsSection from '../components/GaugeInsightsSection';
import DeviceManagement from '../components/DeviceManagement';
import ManualControl from '../components/ManualControl';
import PlantInfoDialog from '../components/PlantInfoDialog';
import theme from '../theme';

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
  { timestamp: '06:00', temperature: 20.1, humidity: 80, light: 150 },
  { timestamp: '07:00', temperature: 21.3, humidity: 78, light: 300 },
  { timestamp: '08:00', temperature: 22.5, humidity: 75, light: 450 },
  { timestamp: '09:00', temperature: 23.8, humidity: 72, light: 600 },
  { timestamp: '10:00', temperature: 25.2, humidity: 68, light: 750 },
  { timestamp: '11:00', temperature: 26.0, humidity: 65, light: 900 },
  { timestamp: '12:00', temperature: 27.1, humidity: 62, light: 1050 },
  { timestamp: '13:00', temperature: 27.8, humidity: 60, light: 1150 },
  { timestamp: '14:00', temperature: 27.5, humidity: 61, light: 1100 },
  { timestamp: '15:00', temperature: 26.9, humidity: 63, light: 950 },
  { timestamp: '16:00', temperature: 26.2, humidity: 66, light: 800 },
  { timestamp: '17:00', temperature: 25.0, humidity: 70, light: 600 },
  { timestamp: '18:00', temperature: 23.7, humidity: 75, light: 400 }
];

const getStageColor = (stage) => {
  const stageColors = {
    Seedling: '#4caf50',
    Vegetative: '#8bc34a',
    Flowering: '#ff9800',
    Fruiting: '#f44336',
    'Harvest Ready': '#9c27b0',
    Dormant: '#607d8b'
  };
  return stageColors[stage] || '#2196f3';
};

export default function DashboardPage () {
  const materialTheme = useTheme();
  const drawerWidth = 200;
  const [boards, setBoards] = useState([]);
  const [timestamp, setTimestamp] = useState('');
  const [plantDialogOpen, setPlantDialogOpen] = useState(false);
  const [plantInfo, setPlantInfo] = useState({
    name: 'Lettuce',
    stage: 'Vegetative',
    remark: 'Slightly yellow leaves – monitoring closely.'
  });

  useEffect(() => {
    setTimestamp(fakeData.timestamp);
    setBoards(fakeData.boards);
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
        <Sidebar drawerWidth={drawerWidth} />

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            ml: `${drawerWidth}px`,
            width: `calc(100% - ${drawerWidth}px)`,
            p: 3
          }}
        >
          <Toolbar />

          {/* ENHANCED HEADER */}
          <Box display="flex" alignItems="stretch" justifyContent="space-between" mb={3} gap={3}>
            <Box display="flex" flexDirection="column" justifyContent="center">
              <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                System Overview
              </Typography>
              {timestamp && (
                <Box display="flex" alignItems="center" gap={1}>
                  <TimeIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="text.secondary">
                    Last updated: {new Date(timestamp).toLocaleString()}
                  </Typography>
                </Box>
              )}
            </Box>

            {/* ENHANCED PLANT INFO CARD */}
            <Paper
              elevation={3}
              sx={{
                display: 'flex',
                alignItems: 'stretch',
                bgcolor: 'background.paper',
                borderRadius: 3,
                overflow: 'hidden',
                minWidth: 320,
                boxShadow: materialTheme.shadows[4],
                border: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`,
                transition: 'all 0.2s ease',
                '&:hover': {
                  boxShadow: materialTheme.shadows[8],
                  transform: 'translateY(-2px)'
                }
              }}
            >
              {/* Plant Avatar Section */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 80,
                  background: `linear-gradient(135deg, ${alpha(materialTheme.palette.primary.main, 0.1)} 0%, ${alpha(materialTheme.palette.secondary.main, 0.1)} 100%)`,
                  borderRight: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`
                }}
              >
                <Avatar
                  sx={{
                    bgcolor: materialTheme.palette.primary.main,
                    width: 48,
                    height: 48,
                    boxShadow: materialTheme.shadows[2]
                  }}
                >
                  <LocalFloristIcon fontSize="medium" />
                </Avatar>
              </Box>

              {/* Plant Info Section */}
              <Box sx={{ flex: 1, p: 2, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500, mb: 0.5 }}>
                  Current Plant
                </Typography>

                <Typography variant="h6" sx={{ fontWeight: 700, mb: 1, color: 'text.primary' }}>
                  {plantInfo.name}
                </Typography>

                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <StageIcon fontSize="small" sx={{ color: getStageColor(plantInfo.stage) }} />
                  <Chip
                    label={plantInfo.stage}
                    size="small"
                    sx={{
                      bgcolor: alpha(getStageColor(plantInfo.stage), 0.1),
                      color: getStageColor(plantInfo.stage),
                      border: `1px solid ${alpha(getStageColor(plantInfo.stage), 0.3)}`,
                      fontWeight: 600,
                      fontSize: '0.75rem'
                    }}
                  />
                </Box>

                {plantInfo.remark && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      fontStyle: 'italic',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '200px'
                    }}
                  >
                    {plantInfo.remark}
                  </Typography>
                )}
              </Box>

              <Divider orientation="vertical" flexItem sx={{ opacity: 0.3 }} />

              {/* Edit Button Section */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 70,
                  bgcolor: alpha(materialTheme.palette.action.hover, 0.02)
                }}
              >
                <Button
                  variant="text"
                  size="small"
                  onClick={() => setPlantDialogOpen(true)}
                  sx={{
                    minWidth: 'auto',
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    color: materialTheme.palette.primary.main,
                    '&:hover': {
                      bgcolor: alpha(materialTheme.palette.primary.main, 0.08),
                      transform: 'scale(1.05)'
                    }
                  }}
                >
                  <EditIcon fontSize="small" />
                </Button>
              </Box>
            </Paper>
          </Box>

          {/* MAIN GRID */}
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={8}>
              <OverviewSection boards={boards} />
              <Box sx={{ mt: 2 }}>
                <HistoricalTrends data={historyData} />
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <GaugeInsightsSection />
            </Grid>
          </Grid>

          <Grid container spacing={2} sx={{ mt: 1, alignItems: 'stretch' }}>
            <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
              <DeviceManagement sx={{ flexGrow: 1 }} />
            </Grid>
            <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
              <ManualControl sx={{ flexGrow: 1 }} />
            </Grid>
          </Grid>
        </Box>
      </Box>

      <PlantInfoDialog
        open={plantDialogOpen}
        initialInfo={plantInfo}
        onClose={() => setPlantDialogOpen(false)}
        onSave={newInfo => setPlantInfo(newInfo)}
      />
    </ThemeProvider>
  );
}
