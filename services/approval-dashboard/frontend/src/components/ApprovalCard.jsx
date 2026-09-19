import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Chip,
  Box,
  IconButton,
  Tooltip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { useAuth } from '../context/AuthContext';
import { approvalAPI } from '../services/api';
import { useNotification } from '../context/NotificationContext';
import { useNavigate } from 'react-router-dom';

const ApprovalCard = ({ approval, onClick, onDelete, onActionComplete }) => {
  const { user } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();
  const [actionDialog, setActionDialog] = useState(null); // 'approve' or 'reject'
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAction = async (action) => {
    if (!comment.trim()) {
      showNotification('Please provide a comment', 'error');
      return;
    }

    setLoading(true);
    try {
      if (action === 'approve') {
        await approvalAPI.approve(approval.id, comment);
        showNotification('Approval approved successfully! Action will be executed.', 'success');
      } else {
        await approvalAPI.reject(approval.id, comment);
        showNotification('Approval rejected', 'success');
      }
      setActionDialog(null);
      setComment('');
      if (onActionComplete) onActionComplete();
    } catch (err) {
      showNotification(err.response?.data?.message || `Failed to ${action}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = () => {
    navigate(`/approvals/${approval.id}`);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'low':
        return 'info';
      case 'medium':
        return 'primary';
      case 'high':
        return 'warning';
      case 'critical':
        return 'error';
      default:
        return 'default';
    }
  };

  const canDelete = user?.id === approval.requesterId;

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': {
          boxShadow: 6,
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent
        sx={{ flexGrow: 1, pb: 1 }}
        onClick={onClick}
      >
        {/* Status and Priority Badges */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Chip
            label={approval.status.toUpperCase()}
            color={getStatusColor(approval.status)}
            size="small"
          />
          <Chip
            label={approval.priority.toUpperCase()}
            color={getPriorityColor(approval.priority)}
            size="small"
          />
        </Box>

        {/* Title */}
        <Typography
          variant="h6"
          component="h3"
          gutterBottom
          sx={{
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {approval.title}
        </Typography>

        {/* Description */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            mb: 2,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {approval.description || 'No description provided'}
        </Typography>

        {/* Type */}
        <Chip
          label={approval.type}
          size="small"
          variant="outlined"
          sx={{ mb: 2 }}
        />

        {/* Metadata */}
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Requested by: {approval.requester?.name || 'Unknown'}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {formatDistanceToNow(new Date(approval.createdAt), { addSuffix: true })}
          </Typography>
        </Box>
      </CardContent>

      {/* Actions */}
      <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Tooltip title="View Details">
          <IconButton size="small" color="primary" onClick={handleViewDetails}>
            <VisibilityIcon />
          </IconButton>
        </Tooltip>

        {approval.status === 'pending' && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Approve">
              <IconButton
                size="small"
                color="success"
                onClick={(e) => {
                  e.stopPropagation();
                  setActionDialog('approve');
                }}
              >
                <ApproveIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Reject">
              <IconButton
                size="small"
                color="error"
                onClick={(e) => {
                  e.stopPropagation();
                  setActionDialog('reject');
                }}
              >
                <RejectIcon />
              </IconButton>
            </Tooltip>
          </Box>
        )}

        {canDelete && approval.status === 'pending' && (
          <Tooltip title="Delete">
            <IconButton
              size="small"
              color="error"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
            >
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        )}
      </CardActions>

      {/* Action Dialog */}
      <Dialog open={!!actionDialog} onClose={() => setActionDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {actionDialog === 'approve' ? 'Approve Action' : 'Reject Action'}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {approval.title}
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Comment"
            fullWidth
            multiline
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={actionDialog === 'approve' ? 'Approval reason...' : 'Rejection reason...'}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionDialog(null)}>Cancel</Button>
          <Button
            onClick={() => handleAction(actionDialog)}
            variant="contained"
            color={actionDialog === 'approve' ? 'success' : 'error'}
            disabled={loading || !comment.trim()}
          >
            {loading ? 'Processing...' : (actionDialog === 'approve' ? 'Approve' : 'Reject')}
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default ApprovalCard;
