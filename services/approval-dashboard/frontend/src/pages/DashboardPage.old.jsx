import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  TextField,
  InputAdornment,
  Button,
  Chip,
  CircularProgress,
  Alert,
  MenuItem,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Search as SearchIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import useApprovals from '../hooks/useApprovals';
import ApprovalCard from '../components/ApprovalCard';
import ApprovalForm from '../components/ApprovalForm';

const DashboardPage = () => {
  const navigate = useNavigate();
  // Static user for display (no auth required)
  const user = { id: 1, name: 'Admin User', email: 'admin@devops.local', role: 'Admin' };

  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // Build filters for API - memoize to prevent infinite re-renders
  const filters = React.useMemo(() => ({
    search: searchQuery,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    priority: priorityFilter !== 'all' ? priorityFilter : undefined,
  }), [searchQuery, statusFilter, priorityFilter]);

  const {
    approvals,
    loading,
    error,
    fetchApprovals,
    createApproval,
    deleteApproval,
  } = useApprovals(filters);

  // Filter approvals based on active tab
  const getFilteredApprovals = useCallback(() => {
    let filtered = approvals;

    switch (activeTab) {
      case 0: // All
        return filtered;
      case 1: // Pending
        return filtered.filter((a) => a.status === 'pending');
      case 2: // Approved
        return filtered.filter((a) => a.status === 'approved');
      case 3: // Rejected
        return filtered.filter((a) => a.status === 'rejected');
      case 4: // My Requests
        return filtered.filter((a) => a.requesterId === user?.id);
      default:
        return filtered;
    }
  }, [approvals, activeTab, user]);

  const filteredApprovals = getFilteredApprovals();

  // Get count for each tab
  const getCounts = () => {
    return {
      all: approvals.length,
      pending: approvals.filter((a) => a.status === 'pending').length,
      approved: approvals.filter((a) => a.status === 'approved').length,
      rejected: approvals.filter((a) => a.status === 'rejected').length,
      mine: approvals.filter((a) => a.requesterId === user?.id).length,
    };
  };

  const counts = getCounts();

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleSearchChange = (event) => {
    setSearchQuery(event.target.value);
  };

  const handleCreateApproval = async (approvalData) => {
    try {
      await createApproval(approvalData);
      setShowCreateDialog(false);
    } catch (err) {
      console.error('Error creating approval:', err);
    }
  };

  const handleApprovalClick = (id) => {
    navigate(`/approvals/${id}`);
  };

  const handleDeleteApproval = async (id) => {
    if (window.confirm('Are you sure you want to delete this approval?')) {
      try {
        await deleteApproval(id);
      } catch (err) {
        console.error('Error deleting approval:', err);
      }
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 2,
          }}
        >
          <Typography variant="h4" component="h1" fontWeight="bold">
            Approval Dashboard
          </Typography>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh">
              <IconButton onClick={fetchApprovals} color="primary">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setShowCreateDialog(true)}
            >
              New Approval
            </Button>
          </Box>
        </Box>

        {/* Stats Cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom variant="body2">
                  Total Approvals
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {counts.all}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom variant="body2">
                  Pending
                </Typography>
                <Typography variant="h4" fontWeight="bold" color="warning.main">
                  {counts.pending}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom variant="body2">
                  Approved
                </Typography>
                <Typography variant="h4" fontWeight="bold" color="success.main">
                  {counts.approved}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom variant="body2">
                  Rejected
                </Typography>
                <Typography variant="h4" fontWeight="bold" color="error.main">
                  {counts.rejected}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Filters */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              placeholder="Search approvals..."
              value={searchQuery}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              select
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="all">All Status</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              select
              label="Priority"
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
            >
              <MenuItem value="all">All Priorities</MenuItem>
              <MenuItem value="low">Low</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
            </TextField>
          </Grid>
        </Grid>
      </Box>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onChange={handleTabChange}
        sx={{ mb: 3 }}
        variant="scrollable"
        scrollButtons="auto"
      >
        <Tab label={`All (${counts.all})`} />
        <Tab label={`Pending (${counts.pending})`} />
        <Tab label={`Approved (${counts.approved})`} />
        <Tab label={`Rejected (${counts.rejected})`} />
        <Tab label={`My Requests (${counts.mine})`} />
      </Tabs>

      {/* Content */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : filteredApprovals.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No approvals found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {searchQuery
              ? 'Try adjusting your search or filters'
              : 'Create your first approval request'}
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setShowCreateDialog(true)}
          >
            New Approval
          </Button>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {filteredApprovals.map((approval) => (
            <Grid item xs={12} sm={6} lg={4} key={approval.id}>
              <ApprovalCard
                approval={approval}
                onClick={() => handleApprovalClick(approval.id)}
                onDelete={() => handleDeleteApproval(approval.id)}
                onActionComplete={fetchApprovals}
              />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Approval Dialog */}
      <ApprovalForm
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSubmit={handleCreateApproval}
      />
    </Container>
  );
};

export default DashboardPage;
