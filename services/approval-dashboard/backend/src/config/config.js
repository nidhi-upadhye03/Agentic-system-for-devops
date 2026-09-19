require('dotenv').config();

const config = {
  // Server Configuration
  server: {
    port: process.env.PORT || 5000,
    env: process.env.NODE_ENV || 'development',
    corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:3000'
  },

  // Database Configuration
  database: {
    // Parse DATABASE_URL if provided (postgresql://user:pass@host:port/dbname)
    ...(process.env.DATABASE_URL ? (() => {
      const url = new URL(process.env.DATABASE_URL);
      return {
        host: url.hostname,
        port: parseInt(url.port) || 5432,
        name: url.pathname.slice(1), // Remove leading /
        user: url.username,
        password: url.password
      };
    })() : {
      host: process.env.DB_HOST || 'postgres',
      port: process.env.DB_PORT || 5432,
      name: process.env.DB_NAME || 'devops_db',
      user: process.env.DB_USER || 'devops',
      password: process.env.DB_PASSWORD || 'devops123'
    }),
    maxConnections: parseInt(process.env.DB_MAX_CONNECTIONS) || 20,
    idleTimeoutMillis: parseInt(process.env.DB_IDLE_TIMEOUT) || 30000,
    connectionTimeoutMillis: parseInt(process.env.DB_CONNECTION_TIMEOUT) || 2000
  },

  // JWT Configuration
  jwt: {
    secret: process.env.JWT_SECRET || 'your-secret-key-change-in-production',
    expiresIn: process.env.JWT_EXPIRES_IN || '24h',
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d'
  },

  // Email Configuration
  email: {
    provider: process.env.EMAIL_PROVIDER || 'smtp', // 'smtp' or 'sendgrid'

    // SMTP Configuration
    smtp: {
      host: process.env.SMTP_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.SMTP_PORT) || 587,
      secure: process.env.SMTP_SECURE === 'true',
      auth: {
        user: process.env.SMTP_USER || '',
        pass: process.env.SMTP_PASSWORD || ''
      }
    },

    // SendGrid Configuration
    sendgrid: {
      apiKey: process.env.SENDGRID_API_KEY || ''
    },

    from: process.env.EMAIL_FROM || 'noreply@approvaldashboard.com',
    fromName: process.env.EMAIL_FROM_NAME || 'Approval Dashboard'
  },

  // WebSocket Configuration
  websocket: {
    pingTimeout: parseInt(process.env.WS_PING_TIMEOUT) || 60000,
    pingInterval: parseInt(process.env.WS_PING_INTERVAL) || 25000,
    cors: {
      origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
      credentials: true
    }
  },

  // Rate Limiting
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 minutes
    max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || 'logs/app.log',
    maxSize: process.env.LOG_MAX_SIZE || '20m',
    maxFiles: parseInt(process.env.LOG_MAX_FILES) || 5
  },

  // Application Settings
  app: {
    name: 'Approval Dashboard',
    version: '1.0.0',
    apiPrefix: '/api/v1'
  }
};

module.exports = config;
