const jwt = require('jsonwebtoken');
const config = require('../config/config');
const User = require('../models/User');

// Verify JWT token middleware
const authenticateToken = async (req, res, next) => {
  try {
    // Get token from header
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

    if (!token) {
      return res.status(401).json({
        success: false,
        message: 'Access token is required'
      });
    }

    // Verify token
    jwt.verify(token, config.jwt.secret, async (err, decoded) => {
      if (err) {
        if (err.name === 'TokenExpiredError') {
          return res.status(401).json({
            success: false,
            message: 'Token has expired'
          });
        }

        return res.status(403).json({
          success: false,
          message: 'Invalid token'
        });
      }

      // Get user from database
      const user = await User.findById(decoded.userId);

      if (!user) {
        return res.status(404).json({
          success: false,
          message: 'User not found'
        });
      }

      if (!user.is_active) {
        return res.status(403).json({
          success: false,
          message: 'User account is inactive'
        });
      }

      // Attach user to request
      req.user = {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        department: user.department
      };

      next();
    });
  } catch (error) {
    console.error('Authentication error:', error);
    return res.status(500).json({
      success: false,
      message: 'Authentication failed'
    });
  }
};

// Verify user role middleware
const authorizeRoles = (...roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: 'Authentication required'
      });
    }

    if (!roles.includes(req.user.role)) {
      return res.status(403).json({
        success: false,
        message: `Access denied. Required roles: ${roles.join(', ')}`
      });
    }

    next();
  };
};

// Optional authentication (doesn't fail if no token)
const optionalAuth = async (req, res, next) => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
      return next();
    }

    jwt.verify(token, config.jwt.secret, async (err, decoded) => {
      if (!err) {
        const user = await User.findById(decoded.userId);
        if (user && user.is_active) {
          req.user = {
            id: user.id,
            username: user.username,
            email: user.email,
            role: user.role,
            department: user.department
          };
        }
      }
      next();
    });
  } catch (error) {
    next();
  }
};

module.exports = {
  authenticateToken,
  authorizeRoles,
  optionalAuth
};
