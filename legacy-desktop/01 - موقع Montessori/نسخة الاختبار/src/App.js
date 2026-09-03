import { useState, useEffect } from 'react';
import { useAuth, canViewPage } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import Home from './pages/Home';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import Classes from './pages/Classes';
import Teachers from './pages/Teachers';
import Gallery from './pages/Gallery';
import Attendance from './pages/Attendance';
import Payments from './pages/Payments';
import Reminders from './pages/Reminders';
import Reports from './pages/Reports';
import { Menu, MapPin } from 'lucide-react';
import { getLocation, distanceInMeters } from './utils/database';

const PAGE_TITLES = {
  home: { title: '', subtitle: '' },
  dashboard: { title: 'Dashboard', subtitle: 'Kawkab Al-Tifl Overview' },
  students: { title: 'Students', subtitle: 'Manage enrolled students, registrations, and parents' },
  classes: { title: 'Classes', subtitle: 'Manage nursery classes and fees' },
  teachers: { title: 'Teachers', subtitle: 'Manage teaching staff and assignments' },
  gallery: { title: 'Photo Gallery', subtitle: 'View nursery photos and activities' },
  attendance: { title: 'Attendance', subtitle: 'Track student attendance and reports' },
  payments: { title: 'Payments', subtitle: 'Track and record all fee payments' },
  reminders: { title: 'Payment Reminders', subtitle: 'Follow up on overdue payments' },
  reports: { title: 'Reports & Analytics', subtitle: 'Financial performance insights' },
};

export default function App() {
  const { user, loading } = useAuth();
  const [page, setPage] = useState('home');
  const [pendingPage, setPendingPage] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [proximityMsg, setProximityMsg] = useState(null);

  useEffect(() => {
    if (!user || user.role !== 'teacher') return;
    const loc = getLocation();
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const dist = distanceInMeters(pos.coords.latitude, pos.coords.longitude, loc.lat, loc.lng);
        if (dist > 300) {
          setProximityMsg(`You are ${Math.round(dist)}m from the nursery. Within 300m required.`);
        } else {
          setProximityMsg(`✓ You are within range (${Math.round(dist)}m from nursery)`);
          setTimeout(() => setProximityMsg(null), 5000);
        }
      },
      () => setProximityMsg('Could not verify location. Please enable GPS.')
    );
  }, [user]);

  if (loading) return null;

  if (!user) {
    if (showLogin) return <Login onSuccess={() => { setShowLogin(false); if (pendingPage) { setPage(pendingPage); setPendingPage(null); } }} />;
    return <Home onNavigate={(target) => { setPendingPage(target || 'dashboard'); setShowLogin(true); }} />;
  }

  const safePage = canViewPage(user.role, page) ? page : 'dashboard';

  const { title, subtitle } = PAGE_TITLES[safePage] || PAGE_TITLES.dashboard;

  const Pages = {
    dashboard: Dashboard, students: Students, classes: Classes,
    teachers: Teachers, gallery: Gallery, attendance: Attendance,
    payments: Payments, reminders: Reminders, reports: Reports,
  };
  const PageComponent = Pages[safePage] || Dashboard;

  return (
    <div className="app-layout">
      <button className="mobile-menu-btn" onClick={() => setSidebarOpen(true)}>
        <Menu size={20} />
      </button>

      <Sidebar
        page={safePage}
        setPage={setPage}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onLogout={() => { setPage('home'); }}
      />

      <div className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">{title}</h1>
            <p className="page-subtitle">{subtitle}</p>
          </div>
          <div className="page-header-user">
            {user.name} <span className="role-badge">{user.role}</span>
          </div>
        </div>
        {proximityMsg && (
          <div style={{
            padding: '10px 32px', fontSize: '0.85rem',
            background: proximityMsg.includes('✓') ? 'var(--success-light)' : 'var(--warning-light)',
            color: proximityMsg.includes('✓') ? 'var(--success)' : 'var(--warning)',
            display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid',
            borderColor: proximityMsg.includes('✓') ? 'var(--success)' : 'var(--warning)',
          }}>
            <MapPin size={16} /> {proximityMsg}
          </div>
        )}
        <div className="page-body">
          <PageComponent />
        </div>
      </div>
    </div>
  );
}
