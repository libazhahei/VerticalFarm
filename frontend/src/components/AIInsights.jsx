import React from 'react';
import { Box, Typography, Chip, Card } from '@mui/material';
import { styled } from '@mui/material/styles';

const GlassCard = styled(Card)(({ theme }) => ({ /* same styles */ }));

export default function AIInsights ({ insight }) {
  return (
    <GlassCard elevation={1} sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>AI Insights</Typography>
      <Typography variant="body1"><strong>Summary:</strong> {insight.summary}</Typography>
      <Typography variant="body1" sx={{ mt: 0.5 }}><strong>Reasoning:</strong> {insight.reasoning}</Typography>
      <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="body1"><strong>Risk Level:</strong></Typography>
        <Chip label={insight.risk_level.toUpperCase()} color={insight.risk_level === 'high' ? 'secondary' : 'default'} />
      </Box>
      <Typography variant="body1" sx={{ mt: 1 }}><strong>Control Priority:</strong> {insight.control_priority}</Typography>
      <Typography variant="body1" sx={{ mt: 1 }}><strong>Action Priority:</strong></Typography>
      <ol>{insight.action_priority.map((act, idx) => <li key={idx}><Typography variant="body2">{act}</Typography></li>)}</ol>
      <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>Suggestion Time: {insight.suggestion_time}</Typography>
    </GlassCard>
  );
}
