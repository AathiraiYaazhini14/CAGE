import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, setAuthToken, setUnauthorizedHandler } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setTokenState] = useState(() => localStorage.getItem('cage_jwt_token'));
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    setAuthToken(null);
    setTokenState(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout();
    });
  }, [logout]);

  const verifyUser = useCallback(async () => {
    const savedToken = localStorage.getItem('cage_jwt_token');
    if (!savedToken) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await api.auth.me();
      setUser(userData);
      setTokenState(savedToken);
    } catch (err) {
      console.warn('[CAGE Auth] Token invalid or expired:', err.message);
      logout();
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    verifyUser();
  }, [verifyUser]);

  const login = async (email, password) => {
    const res = await api.auth.login(email, password);
    setAuthToken(res.access_token);
    setTokenState(res.access_token);
    setUser(res.user);
    return res;
  };

  const signup = async (name, email, password) => {
    const res = await api.auth.signup(name, email, password);
    setAuthToken(res.access_token);
    setTokenState(res.access_token);
    setUser(res.user);
    return res;
  };

  const loginAsDemo = async () => {
    return await login('demo@cage.dev', 'demo1234');
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    login,
    signup,
    loginAsDemo,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

