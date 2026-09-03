import { useAuth } from '../context/AuthContext';
import { getPayments, getRegistrations } from '../utils/database';
import { LogOut, LayoutDashboard, Users, BookOpen, CreditCard, Bell, BarChart2, GraduationCap, GalleryVertical, ClipboardList, Home } from 'lucide-react';

const ALL_NAV = [
  { id: 'home', label: 'Home', icon: Home, roles: ['owner', 'director', 'finance', 'admin', 'teacher'] },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['owner', 'director', 'finance', 'admin', 'teacher'] },
  { id: 'students', label: 'Students', icon: Users, roles: ['owner', 'director', 'admin', 'teacher'] },
  { id: 'classes', label: 'Classes', icon: BookOpen, roles: ['owner', 'director', 'admin', 'teacher'] },
  { id: 'teachers', label: 'Teachers', icon: GraduationCap, roles: ['owner', 'director', 'admin', 'teacher'] },
  { id: 'attendance', label: 'Attendance', icon: ClipboardList, roles: ['owner', 'director', 'admin', 'teacher'] },
  { id: 'gallery', label: 'Photo Gallery', icon: GalleryVertical, roles: ['owner', 'director', 'finance', 'admin', 'teacher'] },
  { id: 'payments', label: 'Payments', icon: CreditCard, roles: ['owner', 'director', 'finance', 'admin', 'teacher'] },
  { id: 'reminders', label: 'Reminders', icon: Bell, badge: true, roles: ['owner', 'director', 'finance', 'admin', 'teacher'] },
  { id: 'reports', label: 'Reports', icon: BarChart2, roles: ['owner', 'director', 'finance', 'admin', 'teacher'] },
];

export default function Sidebar({ page, setPage, isOpen, onClose, onLogout }) {
  const { user, logout } = useAuth();
  const overdueCount = getPayments().filter(p => p.status === 'pending').length;
  const regCount = getRegistrations().length;
  const NAV = ALL_NAV.filter(n => n.roles.includes(user?.role));

  const handleLogout = () => {
    logout();
    onLogout && onLogout();
    onClose();
  };

  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <nav className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <img src="logo.png" alt="Kawkab Al-Tifl" style={{ width: 48, height: 35, objectFit: 'contain', marginBottom: 8 }} />
          <h1>Kawkab Al-Tifl<br />Al-Hurr</h1>
          <span>Kindergarten</span>
        </div>

        <div className="sidebar-nav">
          <div className="nav-section-label">Menu</div>
          {NAV.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              className={`nav-item ${page === id ? 'active' : ''}`}
              onClick={() => { setPage(id); onClose(); }}
            >
              <Icon size={17} />
              {label}
              {badge && overdueCount > 0 && (
                <span className="badge">{overdueCount}</span>
              )}
              {id === 'students' && regCount > 0 && (
                <span className="badge" style={{ background: 'var(--clay)' }}>{regCount}</span>
              )}
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            {user?.name} <span className="role-badge">{user?.role}</span>
          </div>
          <button className="nav-item logout-btn" onClick={handleLogout}>
            <LogOut size={17} /> Logout
          </button>
        </div>
      </nav>
    </>
  );
}
