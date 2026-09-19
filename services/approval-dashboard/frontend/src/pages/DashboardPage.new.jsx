import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, RefreshCw, CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';

import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Beams } from '../components/ui/beams';
import useApprovals from '../hooks/useApprovals';
import ApprovalCard from '../components/ApprovalCard';
import ApprovalForm from '../components/ApprovalForm';
import { cn } from '../lib/utils';

const DashboardPage = () => {
  const navigate = useNavigate();
  const user = { id: 1, name: 'Admin User', email: 'admin@devops.local', role: 'Admin' };

  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);

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

  const getFilteredApprovals = useCallback(() => {
    let filtered = approvals;

    switch (activeTab) {
      case 0: return filtered;
      case 1: return filtered.filter((a) => a.status === 'pending');
      case 2: return filtered.filter((a) => a.status === 'approved');
      case 3: return filtered.filter((a) => a.status === 'rejected');
      case 4: return filtered.filter((a) => a.requesterId === user?.id);
      default: return filtered;
    }
  }, [approvals, activeTab, user]);

  const filteredApprovals = getFilteredApprovals();

  const getCounts = () => ({
    all: approvals.length,
    pending: approvals.filter((a) => a.status === 'pending').length,
    approved: approvals.filter((a) => a.status === 'approved').length,
    rejected: approvals.filter((a) => a.status === 'rejected').length,
    mine: approvals.filter((a) => a.requesterId === user?.id).length,
  });

  const counts = getCounts();

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

  const tabs = [
    { label: `All (${counts.all})`, value: 0 },
    { label: `Pending (${counts.pending})`, value: 1 },
    { label: `Approved (${counts.approved})`, value: 2 },
    { label: `Rejected (${counts.rejected})`, value: 3 },
    { label: `My Requests (${counts.mine})`, value: 4 },
  ];

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-black">
      {/* Beams Background */}
      <div className="absolute inset-0 z-0">
        <Beams
          beamWidth={2.5}
          beamHeight={18}
          beamNumber={15}
          lightColor="#ffffff"
          speed={2.5}
          noiseIntensity={2}
          scale={0.15}
          rotation={43}
        />
      </div>

      {/* Glassmorphic Navbar */}
      <nav className="relative z-20 w-full">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center">
              <span className="text-xl font-bold text-white">DevOps Copilot</span>
            </div>

            <div className="hidden md:flex items-center space-x-1 rounded-full glass p-1 -mr-6">
              <a href="/dashboard" className="rounded-full px-4 py-2 text-sm font-medium text-white bg-white/10">
                Approvals
              </a>
            </div>

            <div className="flex items-center space-x-4">
              <Badge variant="default">
                {user.name}
              </Badge>
              <Badge variant="outline">
                {user.role}
              </Badge>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10 min-h-[calc(100vh-4rem)]">
        <div className="mx-auto max-w-7xl px-6 lg:px-8 py-8">
          {/* Hero Section */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-4xl font-bold text-white mb-2">
                  Approval Dashboard
                </h1>
                <p className="text-white/70 text-lg">
                  Manage deployment approvals and track requests
                </p>
              </div>
              
              <div className="flex gap-3">
                <Button 
                  variant="ghost"
                  size="lg"
                  onClick={fetchApprovals}
                >
                  <RefreshCw className="mr-2 h-5 w-5" />
                  Refresh
                </Button>
                <Button 
                  variant="default"
                  size="lg"
                  onClick={() => setShowCreateDialog(true)}
                  className="shimmer"
                >
                  <Plus className="mr-2 h-5 w-5" />
                  New Approval
                </Button>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Total Approvals</p>
                      <p className="text-3xl font-bold text-white">{counts.all}</p>
                    </div>
                    <AlertCircle className="h-10 w-10 text-white/40" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Pending</p>
                      <p className="text-3xl font-bold text-yellow-400">{counts.pending}</p>
                    </div>
                    <Clock className="h-10 w-10 text-yellow-400/60" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Approved</p>
                      <p className="text-3xl font-bold text-green-400">{counts.approved}</p>
                    </div>
                    <CheckCircle2 className="h-10 w-10 text-green-400/60" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-hover">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Rejected</p>
                      <p className="text-3xl font-bold text-red-400">{counts.rejected}</p>
                    </div>
                    <XCircle className="h-10 w-10 text-red-400/60" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-white/40" />
              <input
                type="text"
                placeholder="Search approvals..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-full text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20 backdrop-blur-xl"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-3 bg-white/5 border border-white/10 rounded-full text-white focus:outline-none focus:ring-2 focus:ring-white/20 backdrop-blur-xl"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-4 py-3 bg-white/5 border border-white/10 rounded-full text-white focus:outline-none focus:ring-2 focus:ring-white/20 backdrop-blur-xl"
            >
              <option value="all">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Tabs */}
          <div className="flex space-x-1 rounded-full glass p-1 mb-8 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setActiveTab(tab.value)}
                className={cn(
                  "rounded-full px-4 py-2 text-sm font-medium transition-all whitespace-nowrap",
                  activeTab === tab.value
                    ? "bg-white/10 text-white"
                    : "text-white/70 hover:text-white hover:bg-white/5"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          {error && (
            <div className="glass border-red-500/50 p-4 rounded-2xl mb-6">
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
            </div>
          ) : filteredApprovals.length === 0 ? (
            <div className="text-center py-16">
              <AlertCircle className="h-16 w-16 text-white/40 mx-auto mb-4" />
              <h3 className="text-2xl font-semibold text-white mb-2">No approvals found</h3>
              <p className="text-white/60 mb-6">
                {searchQuery
                  ? 'Try adjusting your search or filters'
                  : 'Create your first approval request'}
              </p>
              <Button onClick={() => setShowCreateDialog(true)} className="shimmer">
                <Plus className="mr-2 h-5 w-5" />
                New Approval
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredApprovals.map((approval) => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  onClick={() => handleApprovalClick(approval.id)}
                  onDelete={() => handleDeleteApproval(approval.id)}
                  onActionComplete={fetchApprovals}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Approval Dialog */}
      <ApprovalForm
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSubmit={handleCreateApproval}
      />

      {/* Gradient Overlay */}
      <div className="absolute inset-0 z-0 bg-gradient-to-t from-black/50 via-transparent to-black/30 pointer-events-none" />
    </div>
  );
};

export default DashboardPage;
