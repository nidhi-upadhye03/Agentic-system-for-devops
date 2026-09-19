import React, { createContext, useState, useContext, useEffect } from 'react';
import { authAPI } from '../services/api';
import websocketService from '../services/websocket';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = () => {
      try {
        // Development bypass: allow jumping straight to dashboard without real JWT
        if (process.env.REACT_APP_DEV_BYPASS === 'true') {
          const devUser = process.env.REACT_APP_DEV_USER
            ? JSON.parse(process.env.REACT_APP_DEV_USER)
            : { id: 0, username: 'dev', email: 'dev@local', full_name: 'Developer', role: 'admin' };
          // store a marker token so other code sees a token exists
          localStorage.setItem('token', 'dev-bypass-token');
          localStorage.setItem('user', JSON.stringify(devUser));
          setUser(devUser);
          setIsAuthenticated(true);
          return;
        }

        if (authAPI.isAuthenticated()) {
          const currentUser = authAPI.getCurrentUser();
          setUser(currentUser);
          setIsAuthenticated(true);

          // Connect WebSocket
          websocketService.connect();
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        logout();
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Disconnect WebSocket on unmount
  useEffect(() => {
    return () => {
      websocketService.disconnect();
    };
  }, []);

  const login = async (email, password) => {
    try {
      const data = await authAPI.login(email, password);
      setUser(data.user);
      setIsAuthenticated(true);

      // Connect WebSocket after successful login
      websocketService.connect();

      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const register = async (userData) => {
    try {
      const data = await authAPI.register(userData);
      setUser(data.user);
      setIsAuthenticated(true);

      // Connect WebSocket after successful registration
      websocketService.connect();

      return data;
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    }
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
    setIsAuthenticated(false);

    // Disconnect WebSocket
    websocketService.disconnect();
  };

  const updateUser = (updatedUser) => {
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
  };

  // Check if user has specific role
  const hasRole = (role) => {
    if (!user || !user.role) return false;
    return user.role === role;
  };

  // Check if user is approver
  const isApprover = () => {
    if (!user || !user.role) return false;
    return ['approver', 'admin'].includes(user.role.toLowerCase());
  };

  // Check if user is admin
  const isAdmin = () => {
    return hasRole('admin');
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    updateUser,
    hasRole,
    isApprover,
    isAdmin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
