import React, { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  Paper,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Undo as UndoIcon,
} from '@mui/icons-material';
import { approvalAPI } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const ApprovalActions = ({ approvalId, status, onActionComplete }) => {
  const { showNotification } = useNotification();
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleApprove = async () => {
    if (!comment.trim()) {
      setError('Please provide a comment');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await approvalAPI.approve(approvalId, comment);
      showNotification('Approval approved successfully', 'success');
      setComment('');
      if (onActionComplete) {
        onActionComplete();
      }
    } catch (err) {
      const message = err.response?.data?.message || 'Failed to approve';
      setError(message);
      showNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!comment.trim()) {
      setError('Please provide a reason for rejection');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await approvalAPI.reject(approvalId, comment);
      showNotification('Approval rejected', 'success');
      setComment('');
      if (onActionComplete) {
        onActionComplete();
      }
    } catch (err) {
      const message = err.response?.data?.message || 'Failed to reject';
      setError(message);
      showNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!comment.trim()) {
      setError('Please provide a reason for rollback');
      return;
    }

    if (!window.confirm('Are you sure you want to rollback this approval?')) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      await approvalAPI.rollback(approvalId, comment);
      showNotification('Approval rolled back successfully', 'success');
      setComment('');
      if (onActionComplete) {
        onActionComplete();
      }
    } catch (err) {
      const message = err.response?.data?.message || 'Failed to rollback';
      setError(message);
      showNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const isPending = status === 'pending';
  const isApproved = status === 'approved';

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight="bold">
        {isPending ? 'Take Action' : 'Rollback'}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TextField
        fullWidth
        label={isPending ? 'Comment' : 'Rollback Reason'}
        value={comment}
        onChange={(e) => {
          setComment(e.target.value);
          setError('');
        }}
        multiline
        rows={4}
        required
        placeholder={
          isPending
            ? 'Add your comment...'
            : 'Provide a reason for rolling back this approval...'
        }
        sx={{ mb: 2 }}
      />

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        {isPending ? (
          <>
            <Button
              variant="contained"
              color="success"
              startIcon={<CheckCircleIcon />}
              onClick={handleApprove}
              disabled={loading || !comment.trim()}
              sx={{ flexGrow: 1 }}
            >
              {loading ? 'Approving...' : 'Approve'}
            </Button>

            <Button
              variant="contained"
              color="error"
              startIcon={<CancelIcon />}
              onClick={handleReject}
              disabled={loading || !comment.trim()}
              sx={{ flexGrow: 1 }}
            >
              {loading ? 'Rejecting...' : 'Reject'}
            </Button>
          </>
        ) : isApproved ? (
          <Button
            variant="contained"
            color="warning"
            startIcon={<UndoIcon />}
            onClick={handleRollback}
            disabled={loading || !comment.trim()}
            fullWidth
          >
            {loading ? 'Rolling back...' : 'Rollback'}
          </Button>
        ) : null}
      </Box>

      {isPending && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Please review the approval details carefully before taking action. Your comment
          will be recorded in the approval history.
        </Alert>
      )}

      {isApproved && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Rolling back will revert this approval to pending status. This action should only
          be performed when necessary.
        </Alert>
      )}
    </Box>
  );
};

export default ApprovalActions;
