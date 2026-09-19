require('dotenv').config();
const express = require('express');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const cookieParser = require('cookie-parser');
const rateLimit = require('express-rate-limit');

const config = require('./config/config');
const { testConnection, initializeTables } = require('./services/database');
const { initializeWebSocket } = require('./services/websocket');

// Import routes
const authRoutes = require('./routes/auth');
const approvalRoutes = require('./routes/approvals');

// Create Express app
const app = express();
const server = http.createServer(app);

// Initialize WebSocket
initializeWebSocket(server);

// Middleware
app.use(helmet()); // Security headers
app.use(cors({
  origin: config.server.corsOrigin,
  credentials: true
}));
app.use(compression()); // Compress responses
app.use(express.json({ limit: '10mb' })); // Parse JSON bodies
app.use(express.urlencoded({ extended: true, limit: '10mb' })); // Parse URL-encoded bodies
app.use(cookieParser()); // Parse cookies

// Logging
if (config.server.env === 'development') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined'));
}

// Rate limiting - DISABLED in development
if (config.server.env === 'production') {
  const limiter = rateLimit({
    windowMs: config.rateLimit.windowMs,
    max: config.rateLimit.max,
    message: 'Too many requests from this IP, please try again later.',
    standardHeaders: true,
    legacyHeaders: false,
    skip: (req) => {
      // Skip rate limiting for health and metrics endpoints
      return req.path === '/health' || req.path === '/metrics';
    }
  });
  app.use('/api/', limiter);
  console.log('✓ Rate limiting enabled for production');
} else {
  console.log('✓ Rate limiting DISABLED for development');
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: config.server.env
  });
});

// Metrics endpoint (for Prometheus compatibility)
app.get('/metrics', (req, res) => {
  res.set('Content-Type', 'text/plain');
  res.send(`# HELP approval_dashboard_uptime Uptime in seconds
# TYPE approval_dashboard_uptime gauge
approval_dashboard_uptime ${process.uptime()}
# HELP approval_dashboard_requests_total Total HTTP requests
# TYPE approval_dashboard_requests_total counter
approval_dashboard_requests_total 0
`);
});

// API Routes
app.use(`${config.app.apiPrefix}/auth`, authRoutes);
app.use(`${config.app.apiPrefix}/approvals`, approvalRoutes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    name: config.app.name,
    version: config.app.version,
    status: 'running',
    endpoints: {
      health: '/health',
      auth: `${config.app.apiPrefix}/auth`,
      approvals: `${config.app.apiPrefix}/approvals`
    }
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: 'Route not found'
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Error:', err);

  const statusCode = err.statusCode || 500;
  const message = err.message || 'Internal server error';

  res.status(statusCode).json({
    success: false,
    message,
    ...(config.server.env === 'development' && { stack: err.stack })
  });
});

// Initialize database and start server
const startServer = async () => {
  try {
    // Test database connection
    console.log('Testing database connection...');
    const dbConnected = await testConnection();

    if (!dbConnected) {
      console.error('Failed to connect to database. Exiting...');
      process.exit(1);
    }

    // Initialize database tables
    console.log('Initializing database tables...');
    await initializeTables();

    // Start server
    server.listen(config.server.port, () => {
      console.log('='.repeat(50));
      console.log(`${config.app.name} v${config.app.version}`);
      console.log('='.repeat(50));
      console.log(`Environment: ${config.server.env}`);
      console.log(`Server running on port ${config.server.port}`);
      console.log(`API URL: http://localhost:${config.server.port}${config.app.apiPrefix}`);
      console.log(`Health check: http://localhost:${config.server.port}/health`);
      console.log('='.repeat(50));
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
};

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received: closing HTTP server');
  server.close(() => {
    console.log('HTTP server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT signal received: closing HTTP server');
  server.close(() => {
    console.log('HTTP server closed');
    process.exit(0);
  });
});

// Start the server
startServer();

module.exports = { app, server };
