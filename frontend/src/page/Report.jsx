import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  CssBaseline,
  Toolbar,
  ThemeProvider,
  Grid
} from '@mui/material';
import {
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import Sidebar from '../components/SideBar';
import theme from '../theme';
import { sendRequest } from '../Request';

// Import the separated components
import StatusChip from '../components/StatusChip';
import HumanTasks from '../components/HumanTasks';
import VerificationCriteria from '../components/VerificationCriteria';
import AIStrategies from '../components/AIStrategies';
import DailyAssessment from '../components/DailyAssessment';

export default function ReportPage () {
  const drawerWidth = 200;

  // Summary
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Human tasks
  const [humanTasks, setHumanTasks] = useState([]);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskError, setTaskError] = useState('');

  // Verification
  const [verification, setVerification] = useState([]);
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [verificationError, setVerificationError] = useState('');

  // Strategies
  const [strategies, setStrategies] = useState([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [strategiesError, setStrategiesError] = useState('');

  const [timestamp] = useState(new Date().toISOString());

  const handleUpdateStrategy = (index, updatedStrategy) => {
    setStrategies(prev => {
      const newStrategies = [...prev];
      newStrategies[index] = updatedStrategy;
      return newStrategies;
    });

    // Optional: Send update to backend
    // sendRequest('api/ai/strategies', 'PUT', { index, strategy: updatedStrategy })
    //   .then(() => console.log('Strategy updated'))
    //   .catch(err => console.error('Failed to update strategy:', err));
  };

  useEffect(() => {
    // 1) Fetch summary
    setReport('The overall environmental control today is good. It is recommended to maintain the current strategy.');
    setError('');
    setLoading(false);

    // 2) Fetch human tasks
    setTaskLoading(true);
    sendRequest('api/ai/human_task', 'GET')
      .then(data => {
        setHumanTasks(Array.isArray(data) ? data : []);
      })
      .catch(err => {
        console.error(err);
        setTaskError(err.message);
      })
      .finally(() => setTaskLoading(false));

    // 3) Fetch verification tasks
    setVerificationLoading(true);
    sendRequest('api/ai/verification', 'GET')
      .then(data => {
        setVerification(Array.isArray(data) ? data : []);
      })
      .catch(err => {
        console.error(err);
        setVerificationError(err.message);
      })
      .finally(() => setVerificationLoading(false));

    // 4) Fetch strategies
    setStrategiesLoading(true);
    sendRequest('api/ai/strategies', 'GET')
      .then(data => {
        setStrategies(Array.isArray(data) ? data : []);
      })
      .catch(err => {
        console.error(err);
        setStrategiesError(err.message);
      })
      .finally(() => setStrategiesLoading(false));
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

          {/* Enhanced Header */}
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={4}>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                AI Report
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Box display="flex" alignItems="center" gap={1}>
                  <ScheduleIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="text.secondary">
                    Generated: {new Date(timestamp).toLocaleString()}
                  </Typography>
                </Box>
                <StatusChip status="Good" icon={TrendingUpIcon} />
              </Box>
            </Box>
          </Box>

          {/* Two Column Grid - Human Tasks and Verification */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {/* Human Tasks */}
            <Grid item xs={12} lg={6}>
              <HumanTasks
                tasks={humanTasks}
                loading={taskLoading}
                error={taskError}
              />
            </Grid>

            {/* Verification List */}
            <Grid item xs={12} lg={6}>
              <VerificationCriteria
                verification={verification}
                loading={verificationLoading}
                error={verificationError}
              />
            </Grid>
          </Grid>

          {/* AI Strategies Table - Full Width */}
          <AIStrategies
            strategies={strategies}
            loading={strategiesLoading}
            error={strategiesError}
            onUpdateStrategy={handleUpdateStrategy}
          />

          {/* Daily System Assessment Below Grid */}
          <DailyAssessment
            report={report}
            loading={loading}
            error={error}
          />
        </Box>
      </Box>
    </ThemeProvider>
  );
}
