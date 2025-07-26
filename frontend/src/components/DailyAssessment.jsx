import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Alert,
  Avatar,
  useTheme,
  alpha,
  LinearProgress
} from '@mui/material';
import { Assessment as AssessmentIcon } from '@mui/icons-material';

const DailyAssessment = ({
  report,
  loading,
  error
}) => {
  const materialTheme = useTheme();

  return (
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
  );
};

export default DailyAssessment;
