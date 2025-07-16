// src/components/AIInsights.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, Chip, Card, Divider, Grid } from '@mui/material';
import { styled } from '@mui/material/styles';
// import { sendRequest } from '../Request';  // ← keep this for when your API is ready

const GlassCard = styled(Card)(({ theme }) => ({
  background: theme.palette.background.paper,
  border: '1px solid rgba(0,0,0,0.12)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  borderRadius: theme.shape.borderRadius,
  transition: 'transform 0.2s',
  '&:hover': { transform: 'scale(1.02)' }
}));

export default function AIInsights () {
  const [insight, setInsight] = useState(null);
  //   const [error, setError] = useState(null);

  useEffect(() => {
    // Real API call (commented until backend is ready):
    // const fetchInsights = async () => {
    //   try {
    //     const data = await sendRequest('api/ai/short/insights', 'GET');
    //     // normalize fields, split action_priority, etc...
    //     setInsight(processedData);
    //   } catch (err) {
    //     setError(err.message);
    //   }
    // };
    // fetchInsights();

    // —— Fake data for development ——
    const fake = {
      summary: '降湿至<70% 牺牲: 10%光合效率',
      reasoning: '蒸腾加速，湿热易致病害，根系耗氧↑ ↔ 光合↑，可能灯带发热',
      risk_level: 'high',
      control_priority: '避免病害风险 & 防热损伤',
      action_priority: ['风扇至100%强通风', 'LED略调低至9,000 Lux'],
      suggestion_time: new Date().toISOString()
    };
    setInsight(fake);
  }, []);

  if (!insight) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading AI insights…</Typography>
      </GlassCard>
    );
  }
  //   if (!insight && !error) {
  //     return (
  //       <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
  //         <Typography>Loading AI insights…</Typography>
  //       </GlassCard>
  //     );
  //   }
  //   if (error) {
  //     return (
  //       <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
  //         <Typography color="error">Error: {error}</Typography>
  //       </GlassCard>
  //     );
  //   }

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        AI Insights
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary">
            Summary
          </Typography>
          <Typography variant="body1">{insight.summary}</Typography>
        </Grid>
        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary">
            Reasoning
          </Typography>
          <Typography variant="body1">{insight.reasoning}</Typography>
        </Grid>
        <Grid item xs={12} sm={6}>
          <Typography variant="subtitle2" color="text.secondary">
            Risk Level
          </Typography>
          <Chip
            label={insight.risk_level.toUpperCase()}
            color={insight.risk_level === 'high' ? 'secondary' : 'default'}
            sx={{ fontWeight: 'bold', mt: 0.5 }}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <Typography variant="subtitle2" color="text.secondary">
            Control Priority
          </Typography>
          <Typography variant="body1" sx={{ mt: 0.5 }}>
            {insight.control_priority}
          </Typography>
        </Grid>
        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary">
            Action Priority
          </Typography>
          <Box component="ul" sx={{ pl: 2, mt: 0.5 }}>
            {insight.action_priority.map((act, i) => (
              <li key={i}>
                <Typography variant="body2">{act}</Typography>
              </li>
            ))}
          </Box>
        </Grid>
      </Grid>
      <Divider sx={{ my: 2 }} />
      <Typography variant="caption" color="text.secondary">
        Suggested at: {new Date(insight.suggestion_time).toLocaleString()}
      </Typography>
    </GlassCard>
  );
}
