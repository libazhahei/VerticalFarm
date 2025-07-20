// src/components/TemperatureGauge.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, Card } from '@mui/material';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

const DEFAULT_WEATHER_API_KEY = 'a1ea5d212b5f49e7841125640251607';

export default function TemperatureGauge ({
  city = 'Sydney,AU',
  apiKey = DEFAULT_WEATHER_API_KEY,
  maxTemp = 40
}) {
  const [temperature, setTemperature] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // const fetchWeather = async () => {
    //   try {
    //     // WeatherAPI.com endpoint
    //     const res = await fetch(
    //       `https://api.weatherapi.com/v1/current.json?key=${apiKey}&q=${encodeURIComponent(city)}&aqi=no`
    //     );
    //     if (!res.ok) {
    //       throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    //     }
    //     const data = await res.json();
    //     if (data.error) {
    //       throw new Error(data.error.message);
    //     }
    //     setTemperature(Math.round(data.current.temp_c * 10) / 10);
    //     setLastUpdate(new Date(data.current.last_updated));
    //     setError(null);
    //   } catch (err) {
    //     console.error('Fetch error:', err);
    //     setError(err.message);
    //     setTemperature(null);
    //     setLastUpdate(null);
    //   }
    // };
    // fetchWeather();
    setTemperature(24.5);
    setLastUpdate(new Date());
    setError(null);
  }, [city, apiKey]);

  if (error) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="error">Error: {error}</Typography>
      </GlassCard>
    );
  }

  if (temperature == null) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading temperature for {city}…</Typography>
      </GlassCard>
    );
  }

  // gauge math
  const size = 240;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (temperature / maxTemp) * circumference;

  return (
    <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
      <Typography variant="subtitle1" gutterBottom>
        {city.split(',')[0]} Temperature
      </Typography>
      <Box position="relative" mx="auto" width={size} height={size}>
        <svg viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="#e0e0e0" strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="#1976d2" strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <Box
          position="absolute"
          top={0} left={0}
          width="100%" height="100%"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Typography variant="h4">{temperature}°C</Typography>
        </Box>
      </Box>
      {lastUpdate && (
        <Typography variant="caption">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </Typography>
      )}
    </GlassCard>
  );
}
