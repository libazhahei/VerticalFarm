// src/components/PlantInfoDialog.jsx
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  IconButton,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  Avatar,
  useTheme,
  alpha,
  CircularProgress
} from '@mui/material';
import {
  Close as CloseIcon,
  LocalFlorist as PlantIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Timeline as StageIcon
} from '@mui/icons-material';
import { sendRequest } from '../Request';
const plantStages = [
  'Seedling',
  'Vegetative',
  'Flowering',
  'Fruiting',
  'Harvest Ready',
  'Dormant'
];

const commonPlants = [
  'Lettuce',
  'Tomato',
  'Basil',
  'Spinach',
  'Kale',
  'Mint',
  'Cilantro',
  'Parsley',
  'Pepper',
  'Cucumber'
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

export default function PlantInfoDialog ({ open, initialInfo, onClose, onSave }) {
  const theme = useTheme();
  const [formData, setFormData] = useState({ name: '', stage: '', remark: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (initialInfo) {
      setFormData({ name: initialInfo.name, stage: initialInfo.stage, remark: initialInfo.remark });
    }
  }, [initialInfo]);
  useEffect(() => {
    if (initialInfo) {
      setFormData({ name: initialInfo.name, stage: initialInfo.stage, remark: initialInfo.remark });
    }
  }, [initialInfo]);

  const handleInputChange = (k, v) => setFormData(fd => ({ ...fd, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        plant_name: formData.name,
        growth_stage: formData.stage,
        notes: formData.remark
      };
      await sendRequest('api/plant/plant-settings', 'POST', payload);
      onSave(formData);
      onClose();
    } catch (err) {
      console.error('Failed to save plant settings:', err);
      // optionally show an alert here
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setFormData({ name: initialInfo.name, stage: initialInfo.stage, remark: initialInfo.remark });
    onClose();
  };
  return (
<Dialog
  open={open}
  onClose={handleCancel}
  maxWidth="sm"
  fullWidth
  PaperProps={{
    sx: {
      borderRadius: 3,
      boxShadow: theme.shadows[20],
      // force the dialog panel itself to be fully opaque:
      backgroundColor: theme.palette.background.default,
      border: `1px solid ${alpha(theme.palette.divider, 0.1)}`
    }
  }}
>
      {/* Header */}
      <DialogTitle
        sx={{
          pb: 0,
          position: 'relative',
          background: alpha(theme.palette.primary.main, 0.03),
          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`
        }}
      >
        <Box display="flex" alignItems="center" gap={2}>
          <Avatar
            sx={{
              bgcolor: theme.palette.primary.main,
              width: 56,
              height: 56,
              boxShadow: theme.shadows[4]
            }}
          >
            <PlantIcon fontSize="large" />
          </Avatar>
          <Box flex={1}>
            <Typography variant="h5" fontWeight={700} color="primary">
              Plant Information
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Configure your plant settings and growth stage
            </Typography>
          </Box>
          <IconButton
            onClick={handleCancel}
            sx={{
              position: 'absolute',
              right: 8,
              top: 8,
              bgcolor: alpha(theme.palette.grey[500], 0.1),
              '&:hover': {
                bgcolor: alpha(theme.palette.grey[500], 0.2)
              }
            }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        <Box display="flex" flexDirection="column" gap={3}>
          {/* Plant Name Section */}
          <Box>
            <Typography
              variant="subtitle1"
              fontWeight={600}
              color="text.primary"
              sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}
            >
              <PlantIcon color="primary" fontSize="small" />
              Plant Details
            </Typography>

            <TextField
              fullWidth
              label="Plant Name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    boxShadow: `0 0 0 2px ${alpha(theme.palette.primary.main, 0.1)}`
                  },
                  '&.Mui-focused': {
                    boxShadow: `0 0 0 2px ${alpha(theme.palette.primary.main, 0.2)}`
                  }
                }
              }}
            />

            {/* Plant Suggestions */}
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                Quick select:
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {commonPlants.slice(0, 5).map((plant) => (
                  <Chip
                    key={plant}
                    label={plant}
                    variant={formData.name === plant ? 'filled' : 'outlined'}
                    color={formData.name === plant ? 'primary' : 'default'}
                    size="small"
                    onClick={() => handleInputChange('name', plant)}
                    sx={{
                      borderRadius: 2,
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        transform: 'translateY(-1px)',
                        boxShadow: theme.shadows[2]
                      }
                    }}
                  />
                ))}
              </Box>
            </Box>
          </Box>

          <Divider sx={{ opacity: 0.3 }} />

          {/* Growth Stage Section */}
          <Box>
            <Typography
              variant="subtitle1"
              fontWeight={600}
              color="text.primary"
              sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}
            >
              <StageIcon color="secondary" fontSize="small" />
              Growth Stage
            </Typography>

            <FormControl
              fullWidth
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    boxShadow: `0 0 0 2px ${alpha(theme.palette.secondary.main, 0.1)}`
                  },
                  '&.Mui-focused': {
                    boxShadow: `0 0 0 2px ${alpha(theme.palette.secondary.main, 0.2)}`
                  }
                }
              }}
            >
              <InputLabel>Growth Stage</InputLabel>
<Select
  value={formData.stage}
  label="Growth Stage"
  onChange={(e) => handleInputChange('stage', e.target.value)}
  MenuProps={{
    PaperProps: {
      sx: {
        // Make the dropdown panel completely solid
        backgroundColor: theme.palette.background.default,
        opacity: 1,
        backdropFilter: 'none',
        // Ensure it's above everything else
        zIndex: theme.zIndex.modal + 1,
        // Remove any transparency effects
        '& .MuiMenuItem-root': {
          backgroundColor: 'transparent',
          opacity: 1
        }
      }
    },
    // Additional menu props to ensure solid background
    sx: {
      '& .MuiPaper-root': {
        backgroundColor: theme.palette.background.default,
        opacity: 1,
        backdropFilter: 'none'
      }
    }
  }}
>
{plantStages.map((stage) => (
  <MenuItem
    key={stage}
    value={stage}
    sx={{
      backgroundColor: 'transparent',
      opacity: 1,
      // Solid background when selected
      '&.Mui-selected': {
        backgroundColor: `${getStageColor(stage)} !important`,
        color: theme.palette.common.white,
        opacity: 1
      },
      // Keep it solid on hover when selected
      '&.Mui-selected:hover': {
        backgroundColor: `${getStageColor(stage)} !important`,
        opacity: 1
      },
      // Normal hover state
      '&:hover': {
        backgroundColor: alpha(getStageColor(stage), 0.1),
        opacity: 1
      }
    }}
  >
    <Box display="flex" alignItems="center" gap={2}>
      <Box
        sx={{
          width: 12,
          height: 12,
          borderRadius: '50%',
          backgroundColor: getStageColor(stage),
          opacity: 1
        }}
      />
      {stage}
    </Box>
  </MenuItem>
))}
              </Select>
            </FormControl>

{formData.stage && (
  <Box sx={{ mt: 2 }}>
    <Chip
      label={formData.stage}
      sx={{
        // use the actual stage colour (no alpha)
        bgcolor: getStageColor(formData.stage),
        // ensure text remains readable
        color: theme.palette.common.white,
        // optional: keep a subtle border
        border: `1px solid ${alpha(getStageColor(formData.stage), 0.3)}`,
        // force full opacity
        opacity: 1,
        fontWeight: 600
      }}
    />
  </Box>
)}
          </Box>

          <Divider sx={{ opacity: 0.3 }} />

          {/* Remarks Section */}
          <Box>
            <Typography
              variant="subtitle1"
              fontWeight={600}
              color="text.primary"
              sx={{ mb: 2 }}
            >
              Notes & Observations
            </Typography>

            <TextField
              fullWidth
              label="Remarks"
              multiline
              rows={4}
              value={formData.remark}
              onChange={(e) => handleInputChange('remark', e.target.value)}
              placeholder="Add any observations, notes, or special care instructions..."
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    boxShadow: `0 0 0 2px ${alpha(theme.palette.info.main, 0.1)}`
                  },
                  '&.Mui-focused': {
                    boxShadow: `0 0 0 2px ${alpha(theme.palette.info.main, 0.2)}`
                  }
                }
              }}
            />
          </Box>
        </Box>
      </DialogContent>

      <DialogActions
        sx={{
          p: 3,
          pt: 2,
          background: theme.palette.background.paper,
          borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          gap: 2
        }}
      >
        <Button
          onClick={handleCancel}
          variant="outlined"
          startIcon={<CancelIcon />}
          sx={{
            borderRadius: 2,
            px: 3,
            py: 1,
            textTransform: 'none',
            fontWeight: 600,
            borderColor: alpha(theme.palette.grey[500], 0.5),
            color: theme.palette.text.secondary,
            '&:hover': {
              borderColor: theme.palette.grey[500],
              bgcolor: alpha(theme.palette.grey[500], 0.05)
            }
          }}
        >
          Cancel
        </Button>
  <Button
    onClick={handleSave}
    variant="contained"
    disabled={saving}
    startIcon={<SaveIcon />}
    sx={{
      borderRadius: 2,
      px: 3,
      py: 1,
      textTransform: 'none',
      fontWeight: 600,
      background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
      boxShadow: theme.shadows[4],
      '&:hover': {
        background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.secondary.dark} 100%)`,
        boxShadow: theme.shadows[8],
        transform: 'translateY(-1px)'
      }
    }}
  >
    {saving
      ? <CircularProgress size={20} color="inherit" />
      : 'Save Changes'
    }
  </Button>
      </DialogActions>
    </Dialog>
  );
}
