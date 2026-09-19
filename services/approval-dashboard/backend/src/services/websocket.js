const socketIO = require('socket.io');
const jwt = require('jsonwebtoken');
const config = require('../config/config');
const User = require('../models/User');

let io;
const userSockets = new Map(); // Map userId to socket.id

// Initialize WebSocket server
const initializeWebSocket = (server) => {
  io = socketIO(server, {
    cors: config.websocket.cors,
    pingTimeout: config.websocket.pingTimeout,
    pingInterval: config.websocket.pingInterval
  });

  // Authentication middleware
  io.use(async (socket, next) => {
    try {
      const token = socket.handshake.auth.token || socket.handshake.query.token;

      if (!token) {
        return next(new Error('Authentication token required'));
      }

      // Verify token
      const decoded = jwt.verify(token, config.jwt.secret);

      // Get user
      const user = await User.findById(decoded.userId);

      if (!user || !user.is_active) {
        return next(new Error('Invalid user'));
      }

      // Attach user to socket
      socket.userId = user.id;
      socket.userRole = user.role;
      socket.username = user.username;

      next();
    } catch (error) {
      console.error('WebSocket authentication error:', error);
      next(new Error('Authentication failed'));
    }
  });

  // Connection handler
  io.on('connection', (socket) => {
    console.log(`User connected: ${socket.username} (ID: ${socket.userId})`);

    // Store user socket mapping
    userSockets.set(socket.userId, socket.id);

    // Join user to their personal room
    socket.join(`user:${socket.userId}`);

    // Join role-based rooms
    socket.join(`role:${socket.userRole}`);

    // Send connection confirmation
    socket.emit('connected', {
      message: 'Connected to WebSocket server',
      userId: socket.userId,
      username: socket.username
    });

    // Handle custom events
    socket.on('join_approval', (approvalId) => {
      socket.join(`approval:${approvalId}`);
      console.log(`User ${socket.username} joined approval room: ${approvalId}`);
    });

    socket.on('leave_approval', (approvalId) => {
      socket.leave(`approval:${approvalId}`);
      console.log(`User ${socket.username} left approval room: ${approvalId}`);
    });

    // Handle typing indicator
    socket.on('typing', (data) => {
      socket.to(`approval:${data.approvalId}`).emit('user_typing', {
        userId: socket.userId,
        username: socket.username,
        approvalId: data.approvalId
      });
    });

    // Handle stop typing
    socket.on('stop_typing', (data) => {
      socket.to(`approval:${data.approvalId}`).emit('user_stop_typing', {
        userId: socket.userId,
        username: socket.username,
        approvalId: data.approvalId
      });
    });

    // Handle notification read
    socket.on('mark_notification_read', (notificationId) => {
      socket.emit('notification_read', { notificationId });
    });

    // Handle disconnect
    socket.on('disconnect', () => {
      console.log(`User disconnected: ${socket.username} (ID: ${socket.userId})`);
      userSockets.delete(socket.userId);
    });

    // Handle errors
    socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
  });

  console.log('WebSocket server initialized');
  return io;
};

// Notify specific user
const notifyUser = (userId, event, data) => {
  if (io) {
    io.to(`user:${userId}`).emit(event, data);
  }
};

// Notify users by role
const notifyRole = (role, event, data) => {
  if (io) {
    io.to(`role:${role}`).emit(event, data);
  }
};

// Notify all users in an approval room
const notifyApproval = (approvalId, event, data) => {
  if (io) {
    io.to(`approval:${approvalId}`).emit(event, data);
  }
};

// Broadcast to all connected clients
const broadcast = (event, data) => {
  if (io) {
    io.emit(event, data);
  }
};

// Generic notification handler
const notifyClients = (eventType, data) => {
  if (!io) return;

  switch (eventType) {
    case 'new_approval':
      // Notify specific approver
      if (data.userId) {
        notifyUser(data.userId, 'new_approval', data.approval);
      }
      // Notify all approvers
      notifyRole('approver', 'new_approval', data.approval);
      notifyRole('admin', 'new_approval', data.approval);
      break;

    case 'approval_updated':
      // Notify approver
      if (data.userId) {
        notifyUser(data.userId, 'approval_updated', data.approval);
      }
      // Notify in approval room
      notifyApproval(data.approval.id, 'approval_updated', data.approval);
      break;

    case 'approval_approved':
    case 'approval_rejected':
      // Notify requester
      if (data.userId) {
        notifyUser(data.userId, eventType, data.approval);
      }
      // Notify in approval room
      notifyApproval(data.approval.id, eventType, data.approval);
      break;

    case 'approval_deleted':
      // Notify approver
      if (data.userId) {
        notifyUser(data.userId, 'approval_deleted', data.approval);
      }
      break;

    default:
      console.log('Unknown event type:', eventType);
  }
};

// Get connected users count
const getConnectedUsersCount = () => {
  return io ? io.sockets.sockets.size : 0;
};

// Get user online status
const isUserOnline = (userId) => {
  return userSockets.has(userId);
};

// Get all connected users
const getConnectedUsers = () => {
  if (!io) return [];

  const users = [];
  io.sockets.sockets.forEach((socket) => {
    users.push({
      userId: socket.userId,
      username: socket.username,
      role: socket.userRole,
      socketId: socket.id
    });
  });

  return users;
};

module.exports = {
  initializeWebSocket,
  notifyUser,
  notifyRole,
  notifyApproval,
  broadcast,
  notifyClients,
  getConnectedUsersCount,
  isUserOnline,
  getConnectedUsers
};
