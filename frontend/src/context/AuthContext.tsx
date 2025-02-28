import React, { createContext, useState, useEffect, ReactNode, useContext } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';

import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import isTokenExpired from '../utils';

interface User {
  user_email: string;
  user_id: string;
  env: string;
  issued_on: string;
  access: string;
  exp: number;
}

interface AuthContextType {
  user: any;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  //const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      if (isTokenExpired(token)) {
        logout();
      } else {
        const decoded = jwtDecode(token);
        setUser(decoded);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    // Check if redirected back with access token
    const params = new URLSearchParams(window.location.search);
    const accessToken = params.get('access_token');
    if (accessToken) {
      localStorage.setItem('token', accessToken);
      //const decoded = jwtDecode(accessToken);
      const decoded: User = jwtDecode(accessToken);
      setUser(decoded);
      console.log(`User: ${JSON.stringify(user)}`);
      const lastPath = localStorage.getItem('lastPath') || '/';
      window.location.href = lastPath;
    }
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await axios.post('http://localhost:8887/api/v1/a/refresh-token', {
        client_id: username,
        client_secret: password,
      });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      const decoded = jwtDecode(access_token);
      setUser(decoded);
      console.log(`setuser deco: ${decoded}`);
      window.location.href = '/batches';
    } catch (error) {
      console.error('Failed to login', error);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    //navigate('/login');
  };

  useEffect(() => {
    const interval = setInterval(() => {
      const token = localStorage.getItem('token');
      if (token && isTokenExpired(token)) {
        logout();
      }
    }, 60000); // Check every 60 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>{children}</AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
