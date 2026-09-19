import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Paper,
  Typography,
  Chip,
  Divider,
  Grid,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { useAuth } from '../context/AuthContext';
import { approvalAPI } from '../services/api';
import ApprovalActions from '../components/ApprovalActions';
import ApprovalForm from '../components/ApprovalForm';

const ApprovalDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isApprover } = useAuth();

  const [approval, setApproval] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  // Fetch approval details
  useEffect(() => {
    const fetchApproval = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await approvalAPI.getApprovalById(id);
        // Handle both data.data and direct data structures
        const approvalData = response.data || response;
        setApproval(approvalData);
        // Set history if included
        if (approvalData.history) {
          setHistory(approvalData.history);
        }
      } catch (err) {
        console.error('Error fetching approval:', err);
        setError(err.response?.data?.message || 'Failed to fetch approval');
      } finally {
        setLoading(false);
      }
    };

    fetchApproval();
  }, [id]);

  // Fetch history
  const fetchHistory = async () => {
    try {
      const data = await approvalAPI.getHistory(id);
      setHistory(data);
      setShowHistory(true);
    } catch (err) {
      console.error('Error fetching history:', err);
    }
  };

  const handleUpdateApproval = async (approvalData) => {
    try {
      const updated = await approvalAPI.updateApproval(id, approvalData);
      setApproval(updated);
      setShowEditDialog(false);
    } catch (err) {
      console.error('Error updating approval:', err);
    }
  };

  const handleDeleteApproval = async () => {
    if (window.confirm('Are you sure you want to delete this approval?')) {
      try {
        await approvalAPI.deleteApproval(id);
        navigate('/dashboard');
      } catch (err) {
        console.error('Error deleting approval:', err);
      }
    }
  };

  const handleActionComplete = () => {
    // Refresh approval data after action
    approvalAPI.getApprovalById(id).then(setApproval);
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

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '80vh',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error || !approval) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">{error || 'Approval not found'}</Alert>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/dashboard')}
          sx={{ mt: 2 }}
        >
          Back to Dashboard
        </Button>
      </Container>
    );
  }

  const canEdit = user?.id === approval.requesterId && approval.status === 'pending';
  const canDelete = user?.id === approval.requesterId;
  const canTakeAction = isApprover() && approval.status === 'pending';
  const canRollback = isApprover() && approval.status === 'approved';

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton onClick={() => navigate('/dashboard')} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" component="h1" fontWeight="bold" sx={{ flexGrow: 1 }}>
            Approval Details
          </Typography>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="View History">
              <IconButton onClick={fetchHistory} color="primary">
                <HistoryIcon />
              </IconButton>
            </Tooltip>
            {canEdit && (
              <Tooltip title="Edit">
                <IconButton onClick={() => setShowEditDialog(true)} color="primary">
                  <EditIcon />
                </IconButton>
              </Tooltip>
            )}
            {canDelete && (
              <Tooltip title="Delete">
                <IconButton onClick={handleDeleteApproval} color="error">
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Main Content */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box sx={{ mb: 3 }}>
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
                <Chip label={approval.type} size="small" variant="outlined" />
              </Box>

              <Typography variant="h5" gutterBottom fontWeight="bold">
                {approval.title}
              </Typography>

              <Typography variant="body2" color="text.secondary" gutterBottom>
                Created by {approval.requester?.name || 'Unknown'} on{' '}
                {format(new Date(approval.createdAt), 'PPpp')}
              </Typography>
            </Box>

            <Divider sx={{ my: 3 }} />

            <Box>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Description
              </Typography>
              <Typography variant="body1" paragraph sx={{ whiteSpace: 'pre-wrap' }}>
                {approval.description || 'No description provided'}
              </Typography>
            </Box>

            {approval.metadata && Object.keys(approval.metadata).length > 0 && (
              <>
                <Divider sx={{ my: 3 }} />
                <Box>
                  <Typography variant="h6" gutterBottom fontWeight="bold">
                    Additional Information
                  </Typography>
                  <Box component="pre" sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    fontSize: '0.875rem'
                  }}>
                    {JSON.stringify(approval.metadata, null, 2)}
                  </Box>
                </Box>
              </>
            )}
          </Paper>

          {/* Actions */}
          {(canTakeAction || canRollback) && (
            <Paper sx={{ p: 3 }}>
              <ApprovalActions
                approvalId={approval.id}
                status={approval.status}
                onActionComplete={handleActionComplete}
              />
            </Paper>
          )}
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Details Card */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Details
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Status"
                    secondary={
                      <Chip
                        label={approval.status.toUpperCase()}
                        color={getStatusColor(approval.status)}
                        size="small"
                      />
                    }
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Priority"
                    secondary={
                      <Chip
                        label={approval.priority.toUpperCase()}
                        color={getPriorityColor(approval.priority)}
                        size="small"
                      />
                    }
                  />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Type" secondary={approval.type} />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Requester"
                    secondary={approval.requester?.name || 'Unknown'}
                  />
                </ListItem>
                {approval.approver && (
                  <ListItem>
                    <ListItemText
                      primary="Approver"
                      secondary={approval.approver.name}
                    />
                  </ListItem>
                )}
                <ListItem>
                  <ListItemText
                    primary="Created"
                    secondary={format(new Date(approval.createdAt), 'PPpp')}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Updated"
                    secondary={format(new Date(approval.updatedAt), 'PPpp')}
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>

          {/* History Card */}
          {showHistory && history.length > 0 && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  History
                </Typography>
                <List dense>
                  {history.map((item, index) => (
                    <ListItem key={index}>
                      <ListItemText
                        primary={item.action}
                        secondary={
                          <>
                            {item.user?.name || 'System'}
                            <br />
                            {format(new Date(item.timestamp), 'PPpp')}
                            {item.comment && (
                              <>
                                <br />
                                <em>{item.comment}</em>
                              </>
                            )}
                          </>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Edit Dialog */}
      <ApprovalForm
        open={showEditDialog}
        onClose={() => setShowEditDialog(false)}
        onSubmit={handleUpdateApproval}
        initialData={approval}
        mode="edit"
      />
    </Container>
  );
};

export default ApprovalDetailPage;
