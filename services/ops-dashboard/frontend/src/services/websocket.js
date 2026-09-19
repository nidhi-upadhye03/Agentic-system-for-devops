import { io } from 'socket.io-client';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.listeners = {};
  }

  connect(url = 'http://localhost:8001') {
    if (this.socket && this.connected) {
      console.log('WebSocket already connected');
      return this.socket;
    }

    console.log(`Connecting to WebSocket: ${url}`);
    this.socket = io(url, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.connected = true;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.connected = false;
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    // Real-time event listeners
    this.socket.on('incident:detected', (data) => {
      this.emit('incident', data);
    });

    this.socket.on('incident:updated', (data) => {
      this.emit('incident_update', data);
    });

    this.socket.on('analysis:complete', (data) => {
      this.emit('analysis', data);
    });

    this.socket.on('action:executed', (data) => {
      this.emit('action', data);
    });

    this.socket.on('agent:status', (data) => {
      this.emit('agent_status', data);
    });

    this.socket.on('metrics:update', (data) => {
      this.emit('metrics', data);
    });

    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      this.listeners = {};
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  isConnected() {
    return this.connected;
  }
}

// Singleton instance
const wsService = new WebSocketService();
export default wsService;
