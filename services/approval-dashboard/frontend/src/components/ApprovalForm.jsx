import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  MenuItem,
  Grid,
  Box,
} from '@mui/material';

const ApprovalForm = ({ open, onClose, onSubmit, initialData, mode = 'create' }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'deployment',
    priority: 'medium',
    metadata: {},
  });

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  // Reset form when dialog opens/closes or initialData changes
  useEffect(() => {
    if (open) {
      if (initialData && mode === 'edit') {
        setFormData({
          title: initialData.title || '',
          description: initialData.description || '',
          type: initialData.type || 'deployment',
          priority: initialData.priority || 'medium',
          metadata: initialData.metadata || {},
        });
      } else {
        setFormData({
          title: '',
          description: '',
          type: 'deployment',
          priority: 'medium',
          metadata: {},
        });
      }
      setErrors({});
    }
  }, [open, initialData, mode]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleMetadataChange = (e) => {
    try {
      const metadata = JSON.parse(e.target.value);
      setFormData((prev) => ({ ...prev, metadata }));
      setErrors((prev) => ({ ...prev, metadata: '' }));
    } catch (err) {
      setErrors((prev) => ({ ...prev, metadata: 'Invalid JSON format' }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    setLoading(true);

    try {
      await onSubmit(formData);
      handleClose();
    } catch (err) {
      console.error('Form submission error:', err);
      setErrors({ submit: err.response?.data?.message || 'Submission failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        component: 'form',
        onSubmit: handleSubmit,
      }}
    >
      <DialogTitle>
        {mode === 'edit' ? 'Edit Approval' : 'Create New Approval'}
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                required
                error={!!errors.title}
                helperText={errors.title}
                autoFocus
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                required
                multiline
                rows={4}
                error={!!errors.description}
                helperText={errors.description}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Type"
                name="type"
                value={formData.type}
                onChange={handleChange}
                required
              >
                <MenuItem value="deployment">Deployment</MenuItem>
                <MenuItem value="release">Release</MenuItem>
                <MenuItem value="configuration">Configuration</MenuItem>
                <MenuItem value="access">Access</MenuItem>
                <MenuItem value="budget">Budget</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Priority"
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                required
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Additional Metadata (JSON)"
                name="metadata"
                value={JSON.stringify(formData.metadata, null, 2)}
                onChange={handleMetadataChange}
                multiline
                rows={4}
                error={!!errors.metadata}
                helperText={errors.metadata || 'Optional: Additional data in JSON format'}
                placeholder='{"key": "value"}'
              />
            </Grid>
          </Grid>

          {errors.submit && (
            <Box sx={{ mt: 2, color: 'error.main', textAlign: 'center' }}>
              {errors.submit}
            </Box>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          type="submit"
          variant="contained"
          disabled={loading}
        >
          {loading ? 'Submitting...' : mode === 'edit' ? 'Update' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ApprovalForm;
