// src/components/ManualControl.jsx
import React, { useState } from 'react';
import {
  Card,
  Typography,
  Box,
  Slider,
  Button,
  Divider,
  CircularProgress,
  Snackbar,
  Alert
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { sendRequest } from '../Request';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function ManualControl (props) {
  const [temperature, setTemperature] = useState(25);
  const [humidity, setHumidity] = useState(60);
  const [lightIntensity, setLightIntensity] = useState(500);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    severity: 'success',
    message: ''
  });

  const handleConfirm = async () => {
    setLoading(true);
    try {
      const payload = {
        running_mode: 1, // manual mode only
        temperature,
        humidity,
        light_intensity: lightIntensity
      };

      const res = await sendRequest('api/control/1', 'POST', payload);
      console.log('Control response:', res);

      setSnackbar({
        open: true,
        severity: 'success',
        message: 'Control settings updated'
      });
    } catch (err) {
      setSnackbar({
        open: true,
        severity: 'error',
        message: err.message
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <GlassCard
        elevation={1}
        sx={{
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          ...props.sx
        }}
      >
        {/* Header */}
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="subtitle1">Manual Control</Typography>
        </Box>

        {/* Temperature */}
        <Box mb={2}>
          <Typography gutterBottom>Temperature ({temperature}°C)</Typography>
          <Slider
            value={temperature}
            onChange={(e, v) => setTemperature(v)}
            valueLabelDisplay="auto"
            min={0}
            max={40}
          />
        </Box>

        {/* Humidity */}
        <Box mb={2}>
          <Typography gutterBottom>Humidity ({humidity}%)</Typography>
          <Slider
            value={humidity}
            onChange={(e, v) => setHumidity(v)}
            valueLabelDisplay="auto"
            min={0}
            max={100}
          />
        </Box>

        {/* Light Intensity */}
        <Box mb={2}>
          <Typography gutterBottom>Light ({lightIntensity} lx)</Typography>
          <Slider
            value={lightIntensity}
            onChange={(e, v) => setLightIntensity(v)}
            valueLabelDisplay="auto"
            min={0}
            max={2000}
          />
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Confirm Button */}
        <Button
          variant="contained"
          fullWidth
          onClick={handleConfirm}
          disabled={loading}
        >
          {loading
            ? <CircularProgress size={24} color="inherit" />
            : 'Confirm Changes'
          }
        </Button>
      </GlassCard>

      {/* Snackbar for feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar(s => ({ ...s, open: false }))}
      >
        <Alert
          onClose={() => setSnackbar(s => ({ ...s, open: false }))}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
}
