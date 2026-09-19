const express = require('express');
const router = express.Router();
const approvalController = require('../controllers/approvalController');

// No authentication required - public access

// Statistics
router.get('/stats', approvalController.getApprovalStats);

// My approvals (as requester)
router.get('/my-approvals', approvalController.getMyApprovals);

// Pending approvals (as approver)
router.get('/pending', approvalController.getPendingApprovals);

// Search approvals
router.get('/search', approvalController.searchApprovals);

// CRUD operations
router.post('/', approvalController.createApproval);
router.get('/', approvalController.getApprovals);
router.get('/:id', approvalController.getApprovalById);
router.put('/:id', approvalController.updateApproval);
router.delete('/:id', approvalController.deleteApproval);

// Review approval (approve/reject)
router.post('/:id/review', approvalController.reviewApproval);

// Individual approve/reject/rollback endpoints (for frontend compatibility)
router.post('/:id/approve', approvalController.approveApproval);
router.post('/:id/reject', approvalController.rejectApproval);
router.post('/:id/rollback', approvalController.rollbackApproval);

// History
router.get('/:id/history', approvalController.getApprovalHistory);

module.exports = router;
