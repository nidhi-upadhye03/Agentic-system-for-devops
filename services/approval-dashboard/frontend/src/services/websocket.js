import { io } from 'socket.io-client';

const SOCKET_URL = process.env.REACT_APP_SOCKET_URL || 'http://localhost:5000';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
  }

  connect() {
    const token = localStorage.getItem('token');

    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    const config = {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    };

    // Add auth token only if it exists
    if (token) {
      config.auth = { token };
    }

    console.log('Connecting to WebSocket at:', SOCKET_URL);
    this.socket = io(SOCKET_URL, config);

    this.socket.on('connect', () => {
      console.log('WebSocket connected:', this.socket.id);
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error.message);
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    // Set up event listeners
    this.setupEventListeners();
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.listeners.clear();
    }
  }

  setupEventListeners() {
    // Approval events
    this.socket.on('approval:created', (data) => {
      this.emit('approval:created', data);
    });

    this.socket.on('approval:updated', (data) => {
      this.emit('approval:updated', data);
    });

    this.socket.on('approval:approved', (data) => {
      this.emit('approval:approved', data);
    });

    this.socket.on('approval:rejected', (data) => {
      this.emit('approval:rejected', data);
    });

    this.socket.on('approval:rolledback', (data) => {
      this.emit('approval:rolledback', data);
    });

    this.socket.on('approval:deleted', (data) => {
      this.emit('approval:deleted', data);
    });

    // Notification events
    this.socket.on('notification', (data) => {
      this.emit('notification', data);
    });

    this.socket.on('notification:new', (data) => {
      this.emit('notification:new', data);
    });
  }

  // Subscribe to an event
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);

    // Return unsubscribe function
    return () => {
      this.off(event, callback);
    };
  }

  // Unsubscribe from an event
  off(event, callback) {
    if (!this.listeners.has(event)) return;

    const callbacks = this.listeners.get(event);
    const index = callbacks.indexOf(callback);
    if (index > -1) {
      callbacks.splice(index, 1);
    }

    if (callbacks.length === 0) {
      this.listeners.delete(event);
    }
  }

  // Emit event to all listeners
  emit(event, data) {
    if (!this.listeners.has(event)) return;

    const callbacks = this.listeners.get(event);
    callbacks.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in ${event} listener:`, error);
      }
    });
  }

  // Send custom event to server
  send(event, data) {
    if (!this.socket?.connected) {
      console.warn('WebSocket not connected, cannot send event:', event);
      return;
    }

    this.socket.emit(event, data);
  }

  // Join a room
  joinRoom(room) {
    if (!this.socket?.connected) {
      console.warn('WebSocket not connected, cannot join room:', room);
      return;
    }

    this.socket.emit('join:room', { room });
  }

  // Leave a room
  leaveRoom(room) {
    if (!this.socket?.connected) {
      console.warn('WebSocket not connected, cannot leave room:', room);
      return;
    }

    this.socket.emit('leave:room', { room });
  }

  // Check connection status
  isConnected() {
    return this.socket?.connected || false;
  }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;
