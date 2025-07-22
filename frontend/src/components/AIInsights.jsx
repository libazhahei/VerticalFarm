// src/components/AIInsights.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, Chip, Card, Divider, Grid } from '@mui/material';
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

export default function AIInsights () {
  const [insight, setInsight] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchInsights () {
      try {
        const data = await sendRequest('api/ai/insights/', 'GET');
        setInsight(data);
      } catch (err) {
        if (err.message.includes('404')) {
          console.warn('AI insights endpoint not found; using stub data.');
          setInsight({
            summary: 'No live insights available',
            reasoning: 'Endpoint `/api/ai/insights/` not yet deployed.',
            risk_level: 'low',
            control_priority: 'N/A',
            action_priority: [],
            suggestion_time: new Date().toISOString()
          });
        } else {
          setError(err.message);
        }
      }
    }
    fetchInsights();
  }, []);

  if (error) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="error">Error: {error}</Typography>
      </GlassCard>
    );
  }

  if (!insight) {
    return (
      <GlassCard elevation={1} sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading AI insights…</Typography>
      </GlassCard>
    );
  }

  const {
    summary = '',
    reasoning = '',
    risk_level: riskLevel = 'low',
    control_priority: controlPriority = '',
    action_priority: actionPriority,
    suggestion_time: suggestionTime = ''
  } = insight;

  // Ensure action list is an array
  const actions = Array.isArray(actionPriority)
    ? actionPriority
    : (actionPriority ? [actionPriority] : []);

  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>AI Insights</Typography>
      <Divider sx={{ mb: 2 }} />

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary">Summary</Typography>
          <Typography variant="body1">{summary}</Typography>
        </Grid>

        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary">Reasoning</Typography>
          <Typography variant="body1">{reasoning}</Typography>
        </Grid>

        <Grid item xs={12} sm={6}>
          <Typography variant="subtitle2" color="text.secondary">Risk Level</Typography>
          <Chip
            label={riskLevel.toUpperCase()}
            color={riskLevel === 'high' ? 'secondary' : 'default'}
            sx={{ fontWeight: 'bold', mt: 0.5 }}
          />
        </Grid>

        <Grid item xs={12} sm={6}>
          <Typography variant="subtitle2" color="text.secondary">Control Priority</Typography>
          <Typography variant="body1" sx={{ mt: 0.5 }}>{controlPriority}</Typography>
        </Grid>

        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary">Action Priority</Typography>
          <Box component="ul" sx={{ pl: 2, mt: 0.5 }}>
            {actions.map((act, i) => (
              <li key={i}><Typography variant="body2">{act}</Typography></li>
            ))}
          </Box>
        </Grid>
      </Grid>

      <Divider sx={{ my: 2 }} />

      <Typography variant="caption" color="text.secondary">
        Suggested at: {suggestionTime ? new Date(suggestionTime).toLocaleString() : ''}
      </Typography>
    </GlassCard>
  );
}
