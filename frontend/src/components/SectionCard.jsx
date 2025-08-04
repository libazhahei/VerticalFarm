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
  alpha
} from '@mui/material';

const SectionCard = ({
  title,
  icon: Icon,
  color,
  children,
  loading,
  error,
  isEmpty,
  emptyMessage
}) => {
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

export default SectionCard;
