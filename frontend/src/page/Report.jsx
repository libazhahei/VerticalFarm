import React, { useEffect, useState } from 'react';
import { Box, Typography, CssBaseline, Toolbar, ThemeProvider, Paper, CircularProgress, Alert } from '@mui/material';
import Sidebar from '../components/SideBar';
import theme from '../theme';
import { sendRequest } from '../Request';

export default function ReportPage () {
  const drawerWidth = 200;
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [humanTasks, setHumanTasks] = useState([]);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskError, setTaskError] = useState('');
  const [verification, setVerification] = useState([]);
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [verificationError, setVerificationError] = useState('');
  const [strategies, setStrategies] = useState([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [strategiesError, setStrategiesError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    sendRequest('api/ai/report', 'GET')
      .then(data => setReport(data.report || ''))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));

    setTaskLoading(true);
    setTaskError('');
    sendRequest('api/ai/human_task', 'GET')
      .then(data => setHumanTasks(Array.isArray(data) ? data : (data.tasks || [])))
      .catch(err => setTaskError(err.message))
      .finally(() => setTaskLoading(false));

    setVerificationLoading(true);
    setVerificationError('');
    sendRequest('api/ai/verification', 'GET')
      .then(data => setVerification(Array.isArray(data) ? data : (data.verification || [])))
      .catch(err => setVerificationError(err.message))
      .finally(() => setVerificationLoading(false));

    setStrategiesLoading(true);
    setStrategiesError('');
    sendRequest('api/ai/short/strategies', 'GET')
      .then(data => setStrategies(Array.isArray(data) ? data : (data.strategies || [])))
      .catch(err => setStrategiesError(err.message))
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
          <Typography variant="h4" gutterBottom>
            Report
          </Typography>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>AI Daily Report</Typography>
            {loading && <Box display="flex" alignItems="center"><CircularProgress size={20} sx={{ mr: 2 }} /> Loading...</Box>}
            {error && <Alert severity="error">{error}</Alert>}
            {!loading && !error && (
              report
                ? <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>{report}</Typography>
                : <Typography color="text.secondary">No report content</Typography>
            )}
          </Paper>

          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>Human Tasks</Typography>
            {taskLoading && <Box display="flex" alignItems="center"><CircularProgress size={20} sx={{ mr: 2 }} /> Loading...</Box>}
            {taskError && <Alert severity="error">{taskError}</Alert>}
            {!taskLoading && !taskError && (
              humanTasks.length > 0
                ? (
                    <Box component="ul" sx={{ pl: 3, mb: 0 }}>
                      {humanTasks.map((task, idx) => (
                        <li key={idx}>
                          <Typography variant="body1">
                            <strong>{task.task || 'Task'}:</strong> {task.todo || ''}
                          </Typography>
                        </li>
                      ))}
                    </Box>
                  )
                : (
                    <Typography color="text.secondary">No human tasks</Typography>
                  )
            )}

            <Box mt={4}>
              <Typography variant="body1" gutterBottom>Verification List</Typography>
              {verificationLoading && <Box display="flex" alignItems="center"><CircularProgress size={20} sx={{ mr: 2 }} /> Loading...</Box>}
              {verificationError && <Alert severity="error">{verificationError}</Alert>}
              {!verificationLoading && !verificationError && (
                verification.length > 0
                  ? (
                      <Box component="ul" sx={{ pl: 3, mb: 0 }}>
                        {verification.map((item, idx) => (
                          <li key={idx}>
                            <Typography variant="body1">
                              <strong>{item.task || 'Task'}:</strong> {item.todo || ''}
                            </Typography>
                          </li>
                        ))}
                      </Box>
                    )
                  : (
                      <Typography color="text.secondary">No verification items</Typography>
                    )
              )}
            </Box>
            <Box mt={4}>
              <Typography variant="body1" gutterBottom>AI Strategies List</Typography>
              {strategiesLoading && <Box display="flex" alignItems="center"><CircularProgress size={20} sx={{ mr: 2 }} /> Loading...</Box>}
              {strategiesError && <Alert severity="error">{strategiesError}</Alert>}
              {!strategiesLoading && !strategiesError && (
                strategies.length > 0
                  ? (
                      <Box component="ul" sx={{ pl: 3, mb: 0 }}>
                        {strategies.map((item, idx) => (
                          <li key={idx}>
                            <Typography variant="body1">
                              <strong>{item.summary || 'Summary'}:</strong> {item.reasoning || ''}
                            </Typography>
                          </li>
                        ))}
                      </Box>
                    )
                  : (
                      <Typography color="text.secondary">No strategies</Typography>
                    )
              )}
            </Box>
          </Paper>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
