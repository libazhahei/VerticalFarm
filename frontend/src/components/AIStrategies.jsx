import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Avatar,
  useTheme,
  alpha,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip
} from '@mui/material';
import {
  Psychology as StrategyIcon,
  Lightbulb as LightbulbIcon
} from '@mui/icons-material';

const AIStrategies = ({ strategies, loading, error }) => {
  const materialTheme = useTheme();

  return (
    <Card
      elevation={3}
      sx={{
        mb: 4,
        borderRadius: 3,
        boxShadow: materialTheme.shadows[4],
        border: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`,
        transition: 'all 0.2s ease',
        '&:hover': { boxShadow: materialTheme.shadows[6], transform: 'translateY(-1px)' }
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
          <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary' }}>
            AI Strategies
          </Typography>
        </Box>

        {/* Content */}
        {loading && (
          <Box display="flex" alignItems="center" gap={2} py={2}>
            <CircularProgress size={20} sx={{ color: materialTheme.palette.secondary.main }} />
            <Typography variant="body2" color="text.secondary">Loading strategies...</Typography>
          </Box>
        )}

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {!loading && !error && strategies.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', textAlign: 'center', py: 2 }}>
            No strategies recommended
          </Typography>
        )}

        {!loading && !error && strategies.length > 0 && (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, bgcolor: alpha(materialTheme.palette.secondary.main, 0.05), borderBottom: `2px solid ${materialTheme.palette.secondary.main}`, width: '25%' }}>
                    Condition & Summary
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, bgcolor: alpha(materialTheme.palette.secondary.main, 0.05), borderBottom: `2px solid ${materialTheme.palette.secondary.main}`, width: '35%' }}>
                    Reasoning
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, bgcolor: alpha(materialTheme.palette.secondary.main, 0.05), borderBottom: `2px solid ${materialTheme.palette.secondary.main}`, width: '15%' }}>
                    Risk Level
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, bgcolor: alpha(materialTheme.palette.secondary.main, 0.05), borderBottom: `2px solid ${materialTheme.palette.secondary.main}`, width: '25%' }}>
                    Action Priority
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {strategies.map((item, idx) => (
                  <TableRow
                    key={item.id || idx}
                    sx={{
                      '&:nth-of-type(odd)': { bgcolor: alpha(materialTheme.palette.secondary.main, 0.02) },
                      '&:hover': { bgcolor: alpha(materialTheme.palette.secondary.main, 0.08) }
                    }}
                  >
                    <TableCell sx={{ verticalAlign: 'top' }}>
                      <Box display="flex" alignItems="flex-start" gap={1}>
                        <LightbulbIcon fontSize="small" sx={{ color: materialTheme.palette.secondary.main, mt: 0.25, flexShrink: 0 }} />
                        <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', fontSize: '0.8rem' }}>
                          {item.summary || 'Strategy'}
                        </Typography>
                      </Box>
                    </TableCell>

                    <TableCell sx={{ verticalAlign: 'top' }}>
                      <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.5, fontSize: '0.8rem' }}>
                        {item.reasoning || ''}
                      </Typography>
                    </TableCell>

                    <TableCell sx={{ verticalAlign: 'top' }}>
                      {item['risk level'] && (
                        <Chip
                          label={item['risk level']}
                          size="small"
                          sx={{
                            bgcolor:
                              item['risk level'] === 'High'
                                ? alpha('#f44336', 0.1)
                                : item['risk level'] === 'Medium'
                                  ? alpha('#ff9800', 0.1)
                                  : alpha('#4caf50', 0.1),
                            color:
                              item['risk level'] === 'High'
                                ? '#f44336'
                                : item['risk level'] === 'Medium'
                                  ? '#ff9800'
                                  : '#4caf50',
                            border: `1px solid ${
                              item['risk level'] === 'High'
? alpha('#f44336', 0.3)
                              : item['risk level'] === 'Medium'
? alpha('#ff9800', 0.3)
                              : alpha('#4caf50', 0.3)
                            }`,
                            fontWeight: 600,
                            fontSize: '0.7rem'
                          }}
                        />
                      )}
                    </TableCell>

                    <TableCell sx={{ verticalAlign: 'top' }}>
                      <Typography variant="body2" color="text.primary" sx={{ fontSize: '0.8rem', fontWeight: 500 }}>
                        {item.action_priority
                          ? item.action_priority.split(',').map((action, i, arr) => (
                              <Box key={i} component="div" sx={{ mb: i < arr.length - 1 ? 0.5 : 0 }}>
                                • {action.trim()}
                              </Box>
                          ))
                          : 'No action specified'}
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
  );
};

export default AIStrategies;
