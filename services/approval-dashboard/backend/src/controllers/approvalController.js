const Approval = require('../models/Approval');
const { query } = require('../services/database');
const emailService = require('../services/email');
const { notifyClients } = require('../services/websocket');
const eventPublisher = require('../services/eventPublisher');

// Create new approval request
exports.createApproval = async (req, res) => {
  try {
    const {
      title,
      description,
      request_type,
      priority,
      metadata,
      due_date
    } = req.body;

    // Validation
    if (!title || !request_type) {
      return res.status(400).json({
        success: false,
        message: 'Title and request type are required'
      });
    }

    // Create approval (auto-response agents don't specify approver - will be assigned)
    const approval = await Approval.create({
      title,
      description,
      request_type,
      priority: priority || 'medium',
      requested_by: req.user?.id || 1,
      approved_by: null,  // Will be assigned when someone approves
      metadata,
      attachments: null,  // Not used in automated requests
      due_date
    });

    // Add to history
    await Approval.addHistory(
      approval.id,
      req.user?.id || 1,
      'created',
      null,
      'pending',
      'Approval request created'
    );

    // Send real-time notification (broadcast to all users)
    notifyClients('new_approval', {
      approval
    });

    // Email notifications skipped for automated approvals

    res.status(201).json({
      success: true,
      message: 'Approval request created successfully',
      data: approval
    });
  } catch (error) {
    console.error('Create approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to create approval request',
      error: error.message
    });
  }
};

// Get all approvals with filters
exports.getApprovals = async (req, res) => {
  try {
    const {
      status,
      request_type,
      priority,
      requested_by,
      approver_id,
      limit = 50,
      offset = 0
    } = req.query;

    const filters = {};
    if (status) filters.status = status;
    if (request_type) filters.request_type = request_type;
    if (priority) filters.priority = priority;
    if (requested_by) filters.requested_by = requested_by;
    if (approver_id) filters.approver_id = approver_id;

    const approvals = await Approval.findAll(filters, parseInt(limit), parseInt(offset));

    res.json({
      success: true,
      data: approvals,
      pagination: {
        limit: parseInt(limit),
        offset: parseInt(offset),
        total: approvals.length
      }
    });
  } catch (error) {
    console.error('Get approvals error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve approvals',
      error: error.message
    });
  }
};

// Get approval by ID
exports.getApprovalById = async (req, res) => {
  try {
    const { id } = req.params;

    const approval = await Approval.findById(id);

    if (!approval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    // Get approval history
    const history = await Approval.getHistory(id);

    res.json({
      success: true,
      data: {
        ...approval,
        history
      }
    });
  } catch (error) {
    console.error('Get approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve approval',
      error: error.message
    });
  }
};

// Update approval
exports.updateApproval = async (req, res) => {
  try {
    const { id } = req.params;
    const updates = req.body;

    // Check if approval exists
    const existingApproval = await Approval.findById(id);
    if (!existingApproval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    // Check permissions (only requester can update pending approvals)
    // Use fallback for req.user since auth is disabled
    const userId = req.user?.id || 1;
    const userRole = req.user?.role || 'admin';

    if (existingApproval.requested_by !== userId && userRole !== 'admin') {
      return res.status(403).json({
        success: false,
        message: 'You do not have permission to update this approval'
      });
    }

    // Cannot update approved/rejected approvals
    if (['approved', 'rejected'].includes(existingApproval.status)) {
      return res.status(400).json({
        success: false,
        message: 'Cannot update an already processed approval'
      });
    }

    const updatedApproval = await Approval.update(id, updates);

    // Add to history
    await Approval.addHistory(
      id,
      userId,
      'updated',
      existingApproval.status,
      updatedApproval.status,
      'Approval request updated'
    );

    // Notify approver if significant changes
    notifyClients('approval_updated', {
      approval: updatedApproval,
      userId: updatedApproval.approver_id
    });

    res.json({
      success: true,
      message: 'Approval updated successfully',
      data: updatedApproval
    });
  } catch (error) {
    console.error('Update approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to update approval',
      error: error.message
    });
  }
};

// Approve or reject approval
exports.reviewApproval = async (req, res) => {
  try {
    const { id } = req.params;
    const { action, comments } = req.body;

    // Validation
    if (!action || !['approve', 'reject'].includes(action)) {
      return res.status(400).json({
        success: false,
        message: 'Valid action (approve/reject) is required'
      });
    }

    // Get approval
    const approval = await Approval.findById(id);
    if (!approval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    // Check permissions
    const userId = req.user?.id || 1;
    const userRole = req.user?.role || 'admin';

    if (approval.approver_id !== userId && userRole !== 'admin') {
      return res.status(403).json({
        success: false,
        message: 'You do not have permission to review this approval'
      });
    }

    // Check if already processed
    if (['approved', 'rejected'].includes(approval.status)) {
      return res.status(400).json({
        success: false,
        message: 'This approval has already been processed'
      });
    }

    const newStatus = action === 'approve' ? 'approved' : 'rejected';

    // Update approval status
    const updatedApproval = await Approval.updateStatus(id, newStatus, comments);

    // Add to history
    await Approval.addHistory(
      id,
      userId,
      action,
      approval.status,
      newStatus,
      comments
    );

    // Create notification for requester
    await query(
      `INSERT INTO notifications (user_id, approval_id, type, title, message)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        approval.requested_by,
        id,
        `approval_${action}d`,
        `Approval ${action === 'approve' ? 'Approved' : 'Rejected'}`,
        `Your approval request "${approval.title}" has been ${action}d by ${req.user?.username || 'Admin User'}`
      ]
    );

    // Send real-time notification
    notifyClients(`approval_${action}d`, {
      approval: updatedApproval,
      userId: approval.requested_by
    });

    // Send email notification
    try {
      const requesterResult = await query('SELECT email, full_name FROM users WHERE id = $1', [approval.requested_by]);
      if (requesterResult.rows.length > 0) {
        const requester = requesterResult.rows[0];
        await emailService.sendApprovalStatusUpdate(
          requester.email,
          requester.full_name,
          approval.title,
          newStatus,
          comments,
          id
        );
      }
    } catch (emailError) {
      console.error('Failed to send email notification:', emailError);
    }

    res.json({
      success: true,
      message: `Approval ${action}d successfully`,
      data: updatedApproval
    });
  } catch (error) {
    console.error('Review approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to review approval',
      error: error.message
    });
  }
};

// Delete approval
exports.deleteApproval = async (req, res) => {
  try {
    const { id } = req.params;

    // Get approval
    const approval = await Approval.findById(id);
    if (!approval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    // Check permissions
    const userId = req.user?.id || 1;
    const userRole = req.user?.role || 'admin';

    if (approval.requested_by !== userId && userRole !== 'admin') {
      return res.status(403).json({
        success: false,
        message: 'You do not have permission to delete this approval'
      });
    }

    // Cannot delete processed approvals
    if (['approved', 'rejected'].includes(approval.status)) {
      return res.status(400).json({
        success: false,
        message: 'Cannot delete an already processed approval'
      });
    }

    await Approval.delete(id);

    res.json({
      success: true,
      message: 'Approval deleted successfully'
    });
  } catch (error) {
    console.error('Delete approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to delete approval',
      error: error.message
    });
  }
};

// Get approval statistics
exports.getApprovalStats = async (req, res) => {
  try {
    const userId = req.user?.id || 1;
    const userRole = req.user?.role || 'admin';

    const stats = await Approval.getStats(userId, userRole);

    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    console.error('Get stats error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve statistics',
      error: error.message
    });
  }
};

// Get my approvals (as requester)
exports.getMyApprovals = async (req, res) => {
  try {
    const { status, limit = 50, offset = 0 } = req.query;
    const userId = req.user?.id || 1;

    const filters = { requested_by: userId };
    if (status) filters.status = status;

    const approvals = await Approval.findAll(filters, parseInt(limit), parseInt(offset));

    res.json({
      success: true,
      data: approvals
    });
  } catch (error) {
    console.error('Get my approvals error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve approvals',
      error: error.message
    });
  }
};

// Get pending approvals (as approver)
exports.getPendingApprovals = async (req, res) => {
  try {
    const { limit = 50, offset = 0 } = req.query;
    const userId = req.user?.id || 1;

    const filters = {
      approver_id: userId,
      status: 'pending'
    };

    const approvals = await Approval.findAll(filters, parseInt(limit), parseInt(offset));

    res.json({
      success: true,
      data: approvals
    });
  } catch (error) {
    console.error('Get pending approvals error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve pending approvals',
      error: error.message
    });
  }
};

// Search approvals
exports.searchApprovals = async (req, res) => {
  try {
    const { q, status, request_type, limit = 50 } = req.query;

    if (!q) {
      return res.status(400).json({
        success: false,
        message: 'Search query is required'
      });
    }

    const filters = {};
    if (status) filters.status = status;
    if (request_type) filters.request_type = request_type;

    const approvals = await Approval.search(q, filters, parseInt(limit));

    res.json({
      success: true,
      data: approvals
    });
  } catch (error) {
    console.error('Search approvals error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to search approvals',
      error: error.message
    });
  }
};

// Approve approval (convenience endpoint)
exports.approveApproval = async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    const { comment } = req.body;

    // Check if approval exists
    const approval = await Approval.findById(id);
    if (!approval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    // Check if already reviewed
    if (approval.status !== 'pending') {
      return res.status(400).json({
        success: false,
        message: `Approval is already ${approval.status}`
      });
    }

    // Update approval status
    const userId = req.user?.id || 1;
    const updated = await Approval.updateStatus(id, 'approved', comment);

    // Add to history
    await Approval.addHistory(
      id,
      userId,
      'approved',
      'pending',
      'approved',
      comment || 'Approval request approved'
    );

    // Notify
    notifyClients('approval_approved', {
      approval: updated,
      userId: approval.requested_by
    });

    // Publish to RabbitMQ for auto-response agent
    await eventPublisher.publishApprovalDecision(id, 'approved', updated);
    console.log(`✓ Approval ${id} approved - notified auto-response agent`);

    res.json({
      success: true,
      message: 'Approval approved successfully',
      data: updated
    });
  } catch (error) {
    console.error('Approve approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to approve approval',
      error: error.message
    });
  }
};

// Reject approval (convenience endpoint)
exports.rejectApproval = async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    const { comment } = req.body;

    // Check if approval exists
    const approval = await Approval.findById(id);
    if (!approval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    // Check if already reviewed
    if (approval.status !== 'pending') {
      return res.status(400).json({
        success: false,
        message: `Approval is already ${approval.status}`
      });
    }

    // Update approval status
    const userId = req.user?.id || 1;
    const updated = await Approval.updateStatus(id, 'rejected', comment);

    // Add to history
    await Approval.addHistory(
      id,
      userId,
      'rejected',
      'pending',
      'rejected',
      comment || 'Approval request rejected'
    );

    // Notify
    notifyClients('approval_rejected', {
      approval: updated,
      userId: approval.requested_by
    });

    // Publish to RabbitMQ for auto-response agent
    await eventPublisher.publishApprovalDecision(id, 'rejected', updated);
    console.log(`✓ Approval ${id} rejected - notified auto-response agent`);

    res.json({
      success: true,
      message: 'Approval rejected successfully',
      data: updated
    });
  } catch (error) {
    console.error('Reject approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to reject approval',
      error: error.message
    });
  }
};

// Rollback approval (convenience endpoint)
exports.rollbackApproval = async (req, res) => {
  try {
    const { id } = req.params;
    const { comment } = req.body;

    // Check if approval exists
    const approval = await Approval.findById(id);
    if (!approval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    // Check if can be rolled back
    if (approval.status !== 'approved') {
      return res.status(400).json({
        success: false,
        message: 'Only approved approvals can be rolled back'
      });
    }

    // Update approval status
    const userId = req.user?.id || 1;
    const updated = await Approval.updateStatus(id, 'rolledback', userId, comment);

    // Add to history
    await Approval.addHistory(
      id,
      userId,
      'rolledback',
      'approved',
      'rolledback',
      comment || 'Approval rolled back'
    );

    // Notify
    notifyClients('approval_rolledback', {
      approval: updated,
      userId: approval.requested_by
    });

    res.json({
      success: true,
      message: 'Approval rolled back successfully',
      data: updated
    });
  } catch (error) {
    console.error('Rollback approval error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to rollback approval',
      error: error.message
    });
  }
};

// Get approval history
exports.getApprovalHistory = async (req, res) => {
  try {
    const { id } = req.params;

    // Check if approval exists
    const approval = await Approval.findById(id);
    if (!approval) {
      return res.status(404).json({
        success: false,
        message: 'Approval not found'
      });
    }

    const history = await Approval.getHistory(id);

    res.json({
      success: true,
      data: history
    });
  } catch (error) {
    console.error('Get approval history error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve approval history',
      error: error.message
    });
  }
};

