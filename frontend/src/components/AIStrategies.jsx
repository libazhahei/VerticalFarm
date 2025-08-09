import React, { useState } from 'react';
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
  Chip,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Psychology as StrategyIcon,
  Lightbulb as LightbulbIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Close as CloseIcon
} from '@mui/icons-material';
const AIStrategies = ({
  strategies,
  loading,
  error,
  onUpdateStrategy
}) => {
  const materialTheme = useTheme();
  const [editDialog, setEditDialog] = useState({ open: false, strategy: null, index: null });
  const [editForm, setEditForm] = useState({
    summary: '',
    reasoning: '',
    'risk level': '',
    action_priority: ''
  });

  const handleEditClick = (strategy, index) => {
    setEditForm({
      summary: strategy.summary || '',
      reasoning: strategy.reasoning || '',
      'risk level': strategy['risk level'] || '',
      action_priority: strategy.action_priority || ''
    });
    setEditDialog({ open: true, strategy, index });
  };

  const handleEditClose = () => {
    setEditDialog({ open: false, strategy: null, index: null });
    setEditForm({
      summary: '',
      reasoning: '',
      'risk level': '',
      action_priority: ''
    });
  };

  const handleEditSave = () => {
    if (onUpdateStrategy) {
      const updatedStrategy = {
        ...editDialog.strategy,
        ...editForm
      };
      onUpdateStrategy(editDialog.index, updatedStrategy);
    }
    handleEditClose();
  };

  const handleFormChange = (field, value) => {
    setEditForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
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
        {loading && (
          <Box display="flex" alignItems="center" gap={2} py={2}>
            <CircularProgress size={20} sx={{ color: materialTheme.palette.secondary.main }} />
            <Typography variant="body2" color="text.secondary">
              Loading strategies...
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && !error && strategies.length === 0 && (
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

        {!loading && !error && strategies.length > 0 && (
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
                        <Box flex={1}>
                          <Typography
                            variant="body2"
                            sx={{ fontWeight: 600, color: 'text.primary', fontSize: '0.8rem' }}
                          >
                            {item.summary || 'Strategy'}
                          </Typography>
                        </Box>
                        <Tooltip title="Edit Strategy">
                          <IconButton
                            size="small"
                            onClick={() => handleEditClick(item, idx)}
                            sx={{
                              opacity: 0.7,
                              '&:hover': {
                                opacity: 1,
                                bgcolor: alpha(materialTheme.palette.secondary.main, 0.1)
                              }
                            }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
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

      {/* Edit Dialog */}

  {/* Header */}
  <DialogTitle
    sx={{
      pb: 0,
      position: 'relative',
      background: alpha(materialTheme.palette.primary.main, 0.03),
      borderBottom: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`,
      display: 'flex',
      alignItems: 'center',
      gap: 2,
    }}
  >
    <Avatar
      sx={{
        bgcolor: materialTheme.palette.secondary.main,
        width: 48,
        height: 48,
        boxShadow: materialTheme.shadows[4],
      }}
    >
      <EditIcon />
    </Avatar>
    <Typography variant="h6" fontWeight={700} color="text.primary">
      Edit AI Strategy
    </Typography>
    <IconButton
      onClick={handleEditClose}
      size="small"
      sx={{
        position: 'absolute',
        right: 8,
        top: 8,
        bgcolor: alpha(materialTheme.palette.grey[500], 0.1),
        '&:hover': { bgcolor: alpha(materialTheme.palette.grey[500], 0.2) },
      }}
    >
      <CloseIcon />
    </IconButton>
  </DialogTitle>

  {/* Body */}
  <DialogContent sx={{ p: 3 }}>
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
      <TextField
        fullWidth
        label="Condition & Summary"
        value={editForm.summary}
        onChange={(e) => handleFormChange('summary', e.target.value)}
        multiline
        rows={2}
        variant="outlined"
        sx={{
          '& .MuiOutlinedInput-root': { borderRadius: 2 },
        }}
      />

      <TextField
        fullWidth
        label="Reasoning"
        value={editForm.reasoning}
        onChange={(e) => handleFormChange('reasoning', e.target.value)}
        multiline
        rows={3}
        variant="outlined"
        sx={{
          '& .MuiOutlinedInput-root': { borderRadius: 2 },
        }}
      />

      <TextField
        select
        label="Risk Level"
        value={editForm['risk level']}
        onChange={(e) => handleFormChange('risk level', e.target.value)}
        variant="outlined"
        sx={{
          '& .MuiOutlinedInput-root': { borderRadius: 2 },
        }}
      >
        <MenuItem value="Low">Low</MenuItem>
        <MenuItem value="Medium">Medium</MenuItem>
        <MenuItem value="High">High</MenuItem>
      </TextField>

      <TextField
        fullWidth
        label="Action Priority"
        value={editForm.action_priority}
        onChange={(e) => handleFormChange('action_priority', e.target.value)}
        multiline
        rows={3}
        variant="outlined"
        helperText="Separate multiple actions with commas"
        sx={{
          '& .MuiOutlinedInput-root': { borderRadius: 2 },
        }}
      />
    </Box>
  </DialogContent>

  {/* Footer */}
  <DialogActions
    sx={{
      p: 3,
      pt: 2,
      background: materialTheme.palette.background.paper,
      borderTop: `1px solid ${alpha(materialTheme.palette.divider, 0.1)}`,
      gap: 2,
    }}
  >
    <Button
      onClick={handleEditClose}
      variant="outlined"
      sx={{
        borderRadius: 2,
        px: 3,
        py: 1,
        textTransform: 'none',
        fontWeight: 600,
        borderColor: alpha(materialTheme.palette.grey[500], 0.5),
        color: materialTheme.palette.text.secondary,
        '&:hover': {
          borderColor: materialTheme.palette.grey[500],
          bgcolor: alpha(materialTheme.palette.grey[500], 0.05),
        },
      }}
    >
      Cancel
    </Button>
    <Button
      onClick={handleEditSave}
      variant="contained"
      startIcon={<SaveIcon />}
      sx={{
        borderRadius: 2,
        px: 3,
        py: 1,
        textTransform: 'none',
        fontWeight: 600,
        background: `linear-gradient(135deg, ${materialTheme.palette.secondary.main} 0%, ${materialTheme.palette.primary.main} 100%)`,
        boxShadow: materialTheme.shadows[4],
        '&:hover': {
          background: `linear-gradient(135deg, ${materialTheme.palette.secondary.dark} 0%, ${materialTheme.palette.primary.dark} 100%)`,
          boxShadow: materialTheme.shadows[8],
          transform: 'translateY(-1px)',
        },
      }}
    >
      Save Changes
    </Button>
  </DialogActions>

    </Card>
  );
};

export default AIStrategies;
