import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import isTokenExpired from '../../utils';

interface ProtectedRouteProps {
  children: JSX.Element;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token || isTokenExpired(token)) {
      logout();
    }
    if (user) {
      const fullPath = location.pathname + location.search;
      localStorage.setItem('lastPath', fullPath);
    }
  }, [user, location]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const userEmailName = user.user_email.split('@')[0];

  return <>{children}</>;
};

export default ProtectedRoute;
