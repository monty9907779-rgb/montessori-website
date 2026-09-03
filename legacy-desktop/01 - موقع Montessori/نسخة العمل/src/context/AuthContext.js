import { createContext, useContext, useState, useEffect } from 'react';
import { authenticateUser } from '../utils/database';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('montessori_current_user');
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch {}
    }
    setLoading(false);
  }, []);

  const login = (email, password) => {
    const u = authenticateUser(email, password);
    if (u) {
      setUser(u);
      localStorage.setItem('montessori_current_user', JSON.stringify(u));
    }
    return u;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('montessori_current_user');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

// Role-based access helpers
const ROLE_PAGES = {
  director: ['home', 'dashboard', 'students', 'classes', 'teachers', 'gallery', 'payments', 'reminders', 'reports'],
  finance: ['home', 'dashboard', 'payments', 'reminders', 'reports'],
  admin: ['home', 'dashboard', 'students', 'classes', 'teachers', 'gallery', 'payments', 'reminders', 'reports'],
  teacher: ['home', 'dashboard', 'students', 'classes', 'teachers', 'gallery', 'payments', 'reminders', 'reports', 'attendance'],
};

export const canViewPage = (role, page) => {
  const allowed = ROLE_PAGES[role];
  return allowed ? allowed.includes(page) : false;
};
