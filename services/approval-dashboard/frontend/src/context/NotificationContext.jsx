import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import websocketService from '../services/websocket';
import { notificationAPI } from '../services/api';

const NotificationContext = createContext(null);

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await notificationAPI.getNotifications();
      setNotifications(data.notifications || []);
      setUnreadCount(data.unreadCount || 0);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load notifications on mount
  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);


  // Set up WebSocket listeners
  useEffect(() => {
    const handleNewNotification = (notification) => {
      setNotifications((prev) => [notification, ...prev]);
      setUnreadCount((prev) => prev + 1);

      // Show toast notification
      toast.info(notification.message, {
        autoClose: 5000,
        onClick: () => {
          if (notification.link) {
            window.location.href = notification.link;
          }
        },
      });
    };

    const handleApprovalCreated = (data) => {
      toast.info(`New approval request: ${data.title}`, {
        autoClose: 5000,
      });
      fetchNotifications();
    };

    const handleApprovalUpdated = (data) => {
      toast.info(`Approval updated: ${data.title}`, {
        autoClose: 3000,
      });
      fetchNotifications();
    };

    const handleApprovalApproved = (data) => {
      toast.success(`Approval approved: ${data.title}`, {
        autoClose: 5000,
      });
      fetchNotifications();
    };

    const handleApprovalRejected = (data) => {
      toast.error(`Approval rejected: ${data.title}`, {
        autoClose: 5000,
      });
      fetchNotifications();
    };

    const handleApprovalRolledback = (data) => {
      toast.warning(`Approval rolled back: ${data.title}`, {
        autoClose: 5000,
      });
      fetchNotifications();
    };

    // Subscribe to events
    const unsubscribers = [
      websocketService.on('notification:new', handleNewNotification),
      websocketService.on('approval:created', handleApprovalCreated),
      websocketService.on('approval:updated', handleApprovalUpdated),
      websocketService.on('approval:approved', handleApprovalApproved),
      websocketService.on('approval:rejected', handleApprovalRejected),
      websocketService.on('approval:rolledback', handleApprovalRolledback),
    ];

    return () => {
      // Unsubscribe from all events
      unsubscribers.forEach((unsubscribe) => unsubscribe());
    };
  }, [fetchNotifications]);

  // Mark notification as read
  const markAsRead = async (id) => {
    try {
      await notificationAPI.markAsRead(id);
      setNotifications((prev) =>
        prev.map((notif) =>
          notif.id === id ? { ...notif, read: true } : notif
        )
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification as read:', error);
      toast.error('Failed to mark notification as read');
    }
  };

  // Mark all notifications as read
  const markAllAsRead = async () => {
    try {
      await notificationAPI.markAllAsRead();
      setNotifications((prev) =>
        prev.map((notif) => ({ ...notif, read: true }))
      );
      setUnreadCount(0);
      toast.success('All notifications marked as read');
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
      toast.error('Failed to mark all notifications as read');
    }
  };

  // Delete notification
  const deleteNotification = async (id) => {
    try {
      await notificationAPI.deleteNotification(id);
      setNotifications((prev) => prev.filter((notif) => notif.id !== id));
      toast.success('Notification deleted');
    } catch (error) {
      console.error('Error deleting notification:', error);
      toast.error('Failed to delete notification');
    }
  };

  // Show custom toast notification
  const showNotification = (message, type = 'info') => {
    switch (type) {
      case 'success':
        toast.success(message);
        break;
      case 'error':
        toast.error(message);
        break;
      case 'warning':
        toast.warning(message);
        break;
      default:
        toast.info(message);
    }
  };

  const value = {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    showNotification,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;
