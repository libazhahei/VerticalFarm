import React from 'react';
import {
  Box,
  Typography,
  Paper,
  useTheme,
  alpha
} from '@mui/material';
import { CheckCircle as CheckIcon } from '@mui/icons-material';

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

export default TaskItem;
