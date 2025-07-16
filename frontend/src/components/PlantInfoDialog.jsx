import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Button, Box, CircularProgress, Alert
} from '@mui/material';
import { sendRequest } from '../Request';

export default function PlantInfoDialog ({ open, onClose }) {
  const [plantName, setPlantName] = useState('');
  const [stage, setStage] = useState('');
  const [remark, setRemark] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (open) {
      setFetching(true);
      setError('');
      setSuccess('');
      sendRequest('api/user/plant_info', 'GET')
        .then(data => {
          setPlantName(data.name || '');
          setStage(data.stage || '');
          setRemark(data.remark || '');
        })
        .catch(err => setError(err.message))
        .finally(() => setFetching(false));
    }
  }, [open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await sendRequest('api/user/plant_info', 'POST', {
        name: plantName,
        stage,
        remark
      });
      setSuccess('Plant information saved!');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setError('');
    setSuccess('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>Record Current Plant Information</DialogTitle>
      <DialogContent>
        {fetching
          ? (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight={120}>
              <CircularProgress />
            </Box>
            )
          : (
            <form onSubmit={handleSubmit}>
              <TextField
                label="Plant Name"
                value={plantName}
                onChange={e => setPlantName(e.target.value)}
                fullWidth
                margin="normal"
                required
              />
              <TextField
                label="Growth Stage"
                value={stage}
                onChange={e => setStage(e.target.value)}
                fullWidth
                margin="normal"
                required
              />
              <TextField
                label="Status Remark"
                value={remark}
                onChange={e => setRemark(e.target.value)}
                fullWidth
                margin="normal"
                multiline
                minRows={2}
              />
              {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
              {success && <Alert severity="success" sx={{ mt: 2 }}>{success}</Alert>}
            </form>
            )}
      </DialogContent>
      <DialogActions>
            <Button onClick={handleClose} color="secondary">cancel</Button>
            <Button
              onClick={handleSubmit}
              variant="contained"
              disabled={loading || fetching}
            >{loading ? <CircularProgress size={20} /> : 'Save'}</Button>
      </DialogActions>
    </Dialog>
  );
}
