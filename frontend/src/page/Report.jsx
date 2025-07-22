
import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  CssBaseline,
  Toolbar,
  ThemeProvider,
  Paper,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  Chip,
  Avatar,
  useTheme,
  alpha,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Assignment as TaskIcon,
  VerifiedUser as VerificationIcon,
  Psychology as StrategyIcon,
  CheckCircle as CheckIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  Lightbulb as LightbulbIcon
} from '@mui/icons-material';
import Sidebar from '../components/SideBar';
import theme from '../theme';
import { sendRequest } from '../Request';

const StatusChip = ({ status, icon: Icon }) => {
  const getStatusColor = (status) => {
    const colors = {
      Good: '#4caf50',
      Warning: '#ff9800',
      Critical: '#f44336',
      Excellent: '#2196f3'
    };
    return colors[status] || '#607d8b';
  };

  const color = getStatusColor(status);

  return (
    <Chip
      icon={Icon && <Icon fontSize="small" />}
      label={status}
      size="medium"
      sx={{
        bgcolor: alpha(color, 0.1),
        color,
        border: `1px solid ${alpha(color, 0.3)}`,
        fontWeight: 600,
        fontSize: '0.875rem'
      }}
    />
  );
};

const SectionCard = ({ title, icon: Icon, color, children, loading, error, isEmpty, emptyMessage }) => {
  const materialTheme = useTheme();

  return (
    <Card
      elevation={3}
      sx={{
        height: '100%',
        borderRadius: 3,
        boxShadow: materialTheme.shadows[4],
        border: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`,
        transition: 'all 0.2s ease',
        '&:hover': {
          boxShadow: materialTheme.shadows[6],
          transform: 'translateY(-1px)'
        }
      }}
    >
      <CardContent sx={{ p: 3, '&:last-child': { pb: 3 } }}>
        {/* Section Header */}
        <Box display="flex" alignItems="center" gap={2} mb={3}>
          <Avatar
            sx={{
              bgcolor: alpha(color, 0.1),
              color,
              width: 48,
              height: 48
            }}
          >
            <Icon fontSize="medium" />
          </Avatar>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary' }}>
              {title}
            </Typography>
          </Box>
        </Box>

        {/* Content */}
        {loading && (
          <Box display="flex" alignItems="center" gap={2} py={2}>
            <CircularProgress size={20} sx={{ color }} />
            <Typography variant="body2" color="text.secondary">
              Loading...
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && !error && isEmpty && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              fontStyle: 'italic',
              textAlign: 'center',
              py: 2
            }}
          >
            {emptyMessage}
          </Typography>
        )}

        {!loading && !error && !isEmpty && children}
      </CardContent>
    </Card>
  );
};

const TaskItem = ({ task, todo, type = 'task' }) => {
  const materialTheme = useTheme();

  return (
    <Paper
      elevation={1}
      sx={{
        p: 2,
        mb: 2,
        bgcolor: alpha(materialTheme.palette.primary.main, 0.02),
        border: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`,
        borderLeft: `4px solid ${materialTheme.palette.primary.main}`,
        borderRadius: 2,
        '&:last-child': { mb: 0 }
      }}
    >
      <Box display="flex" alignItems="flex-start" gap={2}>
        <CheckIcon
          fontSize="small"
          sx={{
            color: materialTheme.palette.success.main,
            mt: 0.25,
            flexShrink: 0
          }}
        />
        <Box flex={1}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.primary' }}>
            {task || 'Task'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.5 }}>
            {todo || ''}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default function ReportPage () {
  const materialTheme = useTheme();
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

  useEffect(() => {
    // 1) Fetch summary (if you have an endpoint for this)
    //    Otherwise keep static as here:
    setReport('The overall environmental control today is good. It is recommended to maintain the current strategy.');
    setError('');
    setLoading(false);

    // 2) Fetch human tasks
    setTaskLoading(true);
    sendRequest('api/ai/human_task', 'GET')
      .then(data => {
        // expecting an array
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
              <SectionCard
                title="Human Tasks"
                icon={TaskIcon}
                color={materialTheme.palette.warning.main}
                loading={taskLoading}
                error={taskError}
                isEmpty={humanTasks.length === 0}
                emptyMessage="No human tasks required"
              >
                {humanTasks.map((task, idx) => (
                  <TaskItem key={idx} task={task.task} todo={task.todo} />
                ))}
              </SectionCard>
            </Grid>

            {/* Verification List */}
            <Grid item xs={12} lg={6}>
              <SectionCard
                title="Verification Criteria"
                icon={VerificationIcon}
                color={materialTheme.palette.info.main}
                loading={verificationLoading}
                error={verificationError}
                isEmpty={verification.length === 0}
                emptyMessage="No verification items"
              >
                {verification.map((item, idx) => (
                  <TaskItem key={idx} task={item.task} todo={item.todo} type="verification" />
                ))}
              </SectionCard>
            </Grid>
          </Grid>

          {/* AI Strategies Table - Full Width */}
          <Card
            elevation={3}
            sx={{
              mb: 4,
              borderRadius: 3,
              boxShadow: materialTheme.shadows[4],
              border: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`,
              transition: 'all 0.2s ease',
              '&:hover': {
                boxShadow: materialTheme.shadows[6],
                transform: 'translateY(-1px)'
              }
            }}
          >
            <CardContent sx={{ p: 3, '&:last-child': { pb: 3 } }}>
              {/* Section Header */}
              <Box display="flex" alignItems="center" gap={2} mb={3}>
                <Avatar
                  sx={{
                    bgcolor: alpha(materialTheme.palette.secondary.main, 0.1),
                    color: materialTheme.palette.secondary.main,
                    width: 48,
                    height: 48
                  }}
                >
                  <StrategyIcon fontSize="medium" />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary' }}>
                    AI Strategies
                  </Typography>
                </Box>
              </Box>

              {/* Content */}
              {strategiesLoading && (
                <Box display="flex" alignItems="center" gap={2} py={2}>
                  <CircularProgress size={20} sx={{ color: materialTheme.palette.secondary.main }} />
                  <Typography variant="body2" color="text.secondary">
                    Loading strategies...
                  </Typography>
                </Box>
              )}

              {strategiesError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {strategiesError}
                </Alert>
              )}

              {!strategiesLoading && !strategiesError && strategies.length === 0 && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    fontStyle: 'italic',
                    textAlign: 'center',
                    py: 2
                  }}
                >
                  No strategies recommended
                </Typography>
              )}

              {!strategiesLoading && !strategiesError && strategies.length > 0 && (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell
                          sx={{
                            fontWeight: 700,
                            bgcolor: alpha(materialTheme.palette.secondary.main, 0.05),
                            borderBottom: `2px solid ${materialTheme.palette.secondary.main}`,
                            width: '25%'
                          }}
                        >
                          Condition & Summary
                        </TableCell>
                        <TableCell
                          sx={{
                            fontWeight: 700,
                            bgcolor: alpha(materialTheme.palette.secondary.main, 0.05),
                            borderBottom: `2px solid ${materialTheme.palette.secondary.main}`,
                            width: '35%'
                          }}
                        >
                          Reasoning
                        </TableCell>
                        <TableCell
                          sx={{
                            fontWeight: 700,
                            bgcolor: alpha(materialTheme.palette.secondary.main, 0.05),
                            borderBottom: `2px solid ${materialTheme.palette.secondary.main}`,
                            width: '15%'
                          }}
                        >
                          Risk Level
                        </TableCell>
                        <TableCell
                          sx={{
                            fontWeight: 700,
                            bgcolor: alpha(materialTheme.palette.secondary.main, 0.05),
                            borderBottom: `2px solid ${materialTheme.palette.secondary.main}`,
                            width: '25%'
                          }}
                        >
                          Action Priority
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {strategies.map((item, idx) => (
                        <TableRow
                          key={item.id || idx}
                          sx={{
                            '&:nth-of-type(odd)': {
                              bgcolor: alpha(materialTheme.palette.secondary.main, 0.02)
                            },
                            '&:hover': {
                              bgcolor: alpha(materialTheme.palette.secondary.main, 0.08)
                            }
                          }}
                        >
                          <TableCell sx={{ verticalAlign: 'top' }}>
                            <Box display="flex" alignItems="flex-start" gap={1}>
                              <LightbulbIcon
                                fontSize="small"
                                sx={{
                                  color: materialTheme.palette.secondary.main,
                                  mt: 0.25,
                                  flexShrink: 0
                                }}
                              />
                              <Typography
                                variant="body2"
                                sx={{ fontWeight: 600, color: 'text.primary', fontSize: '0.8rem' }}
                              >
                                {item.summary || 'Strategy'}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell sx={{ verticalAlign: 'top' }}>
                            <Typography
                              variant="body2"
                              color="text.secondary"
                              sx={{ lineHeight: 1.5, fontSize: '0.8rem' }}
                            >
                              {item.reasoning || ''}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ verticalAlign: 'top' }}>
                            {item['risk level'] && (
                              <Chip
                                label={item['risk level']}
                                size="small"
                                sx={{
                                  bgcolor: item['risk level'] === 'High'
                                    ? alpha('#f44336', 0.1)
                                    : item['risk level'] === 'Medium'
                                      ? alpha('#ff9800', 0.1)
                                      : alpha('#4caf50', 0.1),
                                  color: item['risk level'] === 'High'
                                    ? '#f44336'
                                    : item['risk level'] === 'Medium'
                                      ? '#ff9800'
                                      : '#4caf50',
                                  border: `1px solid ${item['risk level'] === 'High'
? alpha('#f44336', 0.3)
                                                      : item['risk level'] === 'Medium'
? alpha('#ff9800', 0.3)
                                                      : alpha('#4caf50', 0.3)}`,
                                  fontWeight: 600,
                                  fontSize: '0.7rem'
                                }}
                              />
                            )}
                          </TableCell>
                          <TableCell sx={{ verticalAlign: 'top' }}>
                            <Typography
                              variant="body2"
                              color="text.primary"
                              sx={{ fontSize: '0.8rem', fontWeight: 500 }}
                            >
                              {item.action_priority
                                ? item.action_priority.split(',').map((action, i) => (
                                  <Box key={i} component="div" sx={{ mb: i < item.action_priority.split(',').length - 1 ? 0.5 : 0 }}>
                                    • {action.trim()}
                                  </Box>
                                ))
                                : 'No action specified'
                              }
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          {/* Daily System Assessment Below Grid */}
          <Card
            elevation={4}
            sx={{
              mt: 4,
              borderRadius: 3,
              background: `linear-gradient(135deg, ${alpha(materialTheme.palette.primary.main, 0.08)} 0%, ${alpha(materialTheme.palette.secondary.main, 0.04)} 100%)`,
              border: `1px solid ${alpha(materialTheme.palette.primary.main, 0.12)}`
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <Avatar
                  sx={{
                    bgcolor: materialTheme.palette.primary.main,
                    width: 48,
                    height: 48,
                    boxShadow: materialTheme.shadows[2]
                  }}
                >
                  <AssessmentIcon fontSize="medium" />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    Daily System Assessment
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Comprehensive environmental analysis
                  </Typography>
                </Box>
              </Box>

              {loading && (
                <Box>
                  <LinearProgress sx={{ mb: 2 }} />
                  <Typography variant="body2" color="text.secondary">
                    Analyzing system data...
                  </Typography>
                </Box>
              )}

              {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

              {!loading && !error && (
                <Typography
                  variant="body1"
                  sx={{
                    whiteSpace: 'pre-line',
                    lineHeight: 1.6,
                    fontSize: '1.1rem',
                    color: 'text.primary'
                  }}
                >
                  {report || 'No report content available'}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
