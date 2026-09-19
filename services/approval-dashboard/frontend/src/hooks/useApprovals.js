import { useState, useEffect, useCallback } from 'react';
import { approvalAPI } from '../services/api';
import websocketService from '../services/websocket';
import { useNotification } from '../context/NotificationContext';

const useApprovals = (filters = {}) => {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 0,
  });

  const { showNotification } = useNotification();

  // Fetch approvals - useCallback without dependencies to prevent infinite loop
  const fetchApprovals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await approvalAPI.getApprovals(filters);
      setApprovals(data.data || data.approvals || []);
      if (data.pagination) {
        setPagination(data.pagination);
      }
    } catch (err) {
      console.error('Error fetching approvals:', err);
      const errorMsg = err.response?.status === 429 
        ? 'Too many requests. Please wait a moment and refresh.'
        : err.response?.data?.message || 'Failed to fetch approvals';
      setError(errorMsg);
      // Only show notification if not a rate limit error (to prevent spam)
      if (err.response?.status !== 429) {
        showNotification(errorMsg, 'error');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Load approvals on mount and when filters change
  useEffect(() => {
    const loadApprovals = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await approvalAPI.getApprovals(filters);
        setApprovals(data.data || data.approvals || []);
        if (data.pagination) {
          setPagination(data.pagination);
        }
      } catch (err) {
        console.error('Error fetching approvals:', err);
        const errorMsg = err.response?.status === 429 
          ? 'Too many requests. Please wait a moment and refresh.'
          : err.response?.data?.message || 'Failed to fetch approvals';
        setError(errorMsg);
        if (err.response?.status !== 429) {
          showNotification(errorMsg, 'error');
        }
      } finally {
        setLoading(false);
      }
    };
    loadApprovals();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  // Set up WebSocket listeners for real-time updates
  useEffect(() => {
    const handleApprovalCreated = (data) => {
      setApprovals((prev) => [data, ...prev]);
    };

    const handleApprovalUpdated = (data) => {
      setApprovals((prev) =>
        prev.map((approval) =>
          approval.id === data.id ? { ...approval, ...data } : approval
        )
      );
    };

    const handleApprovalDeleted = (data) => {
      setApprovals((prev) =>
        prev.filter((approval) => approval.id !== data.id)
      );
    };

    const handleApprovalStatusChange = (data) => {
      setApprovals((prev) =>
        prev.map((approval) =>
          approval.id === data.id
            ? { ...approval, status: data.status, updatedAt: data.updatedAt }
            : approval
        )
      );
    };

    // Subscribe to WebSocket events
    const unsubscribers = [
      websocketService.on('approval:created', handleApprovalCreated),
      websocketService.on('approval:updated', handleApprovalUpdated),
      websocketService.on('approval:deleted', handleApprovalDeleted),
      websocketService.on('approval:approved', handleApprovalStatusChange),
      websocketService.on('approval:rejected', handleApprovalStatusChange),
      websocketService.on('approval:rolledback', handleApprovalStatusChange),
    ];

    return () => {
      // Unsubscribe from all events
      unsubscribers.forEach((unsubscribe) => unsubscribe());
    };
  }, []);

  // Create approval
  const createApproval = async (approvalData) => {
    try {
      const data = await approvalAPI.createApproval(approvalData);
      setApprovals((prev) => [data, ...prev]);
      showNotification('Approval created successfully', 'success');
      return data;
    } catch (err) {
      console.error('Error creating approval:', err);
      const message = err.response?.data?.message || 'Failed to create approval';
      showNotification(message, 'error');
      throw err;
    }
  };

  // Update approval
  const updateApproval = async (id, approvalData) => {
    try {
      const data = await approvalAPI.updateApproval(id, approvalData);
      setApprovals((prev) =>
        prev.map((approval) =>
          approval.id === id ? { ...approval, ...data } : approval
        )
      );
      showNotification('Approval updated successfully', 'success');
      return data;
    } catch (err) {
      console.error('Error updating approval:', err);
      const message = err.response?.data?.message || 'Failed to update approval';
      showNotification(message, 'error');
      throw err;
    }
  };

  // Delete approval
  const deleteApproval = async (id) => {
    try {
      await approvalAPI.deleteApproval(id);
      setApprovals((prev) => prev.filter((approval) => approval.id !== id));
      showNotification('Approval deleted successfully', 'success');
    } catch (err) {
      console.error('Error deleting approval:', err);
      const message = err.response?.data?.message || 'Failed to delete approval';
      showNotification(message, 'error');
      throw err;
    }
  };

  // Approve an approval
  const approve = async (id, comment = '') => {
    try {
      const data = await approvalAPI.approve(id, comment);
      setApprovals((prev) =>
        prev.map((approval) =>
          approval.id === id ? { ...approval, ...data } : approval
        )
      );
      showNotification('Approval approved successfully', 'success');
      return data;
    } catch (err) {
      console.error('Error approving:', err);
      const message = err.response?.data?.message || 'Failed to approve';
      showNotification(message, 'error');
      throw err;
    }
  };

  // Reject an approval
  const reject = async (id, comment = '') => {
    try {
      const data = await approvalAPI.reject(id, comment);
      setApprovals((prev) =>
        prev.map((approval) =>
          approval.id === id ? { ...approval, ...data } : approval
        )
      );
      showNotification('Approval rejected', 'success');
      return data;
    } catch (err) {
      console.error('Error rejecting:', err);
      const message = err.response?.data?.message || 'Failed to reject';
      showNotification(message, 'error');
      throw err;
    }
  };

  // Rollback an approval
  const rollback = async (id, comment = '') => {
    try {
      const data = await approvalAPI.rollback(id, comment);
      setApprovals((prev) =>
        prev.map((approval) =>
          approval.id === id ? { ...approval, ...data } : approval
        )
      );
      showNotification('Approval rolled back successfully', 'success');
      return data;
    } catch (err) {
      console.error('Error rolling back:', err);
      const message = err.response?.data?.message || 'Failed to rollback';
      showNotification(message, 'error');
      throw err;
    }
  };

  return {
    approvals,
    loading,
    error,
    pagination,
    fetchApprovals,
    createApproval,
    updateApproval,
    deleteApproval,
    approve,
    reject,
    rollback,
  };
};

export default useApprovals;
