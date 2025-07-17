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
          </Paper>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
