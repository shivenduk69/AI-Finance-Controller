import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import authApi from '../api/authApi';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshUser = useCallback(async () => {
    try {
      setLoading(true);
      const res = await authApi.getMe();
      if (res && res.success) {
        setUser(res.data?.user || res.data || res.user || null);
      } else {
        setUser(null);
      }
      setError(null);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email, password) => {
    setError(null);
    try {
      const res = await authApi.login(email, password);
      const userData = res?.data?.user || res?.user || res?.data;
      if (res && res.success && userData) {
        setUser(userData);
        if (res.token || res.data?.token) {
          localStorage.setItem('auth_token', res.token || res.data?.token);
        }
        return userData;
      }
      throw new Error(res?.message || 'Login failed');
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (err) {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('auth_token');
      setUser(null);
      window.location.href = '/login';
    }
  };

  const value = {
    user,
    loading,
    error,
    isAuthenticated: Boolean(user),
    isAdmin: user?.role === 'ADMIN',
    isMerchant: user?.role === 'MERCHANT',
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
