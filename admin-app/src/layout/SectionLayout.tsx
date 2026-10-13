import { useState, type ReactNode } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { NotificationBell } from '../components/NotificationBell';
import { ChangePasswordModal } from '../components/ChangePasswordModal';

const NAV: { to: string; label: string; end?: boolean }[] = [
  { to: '/section', label: 'Tableau de bord', end: true },
  { to: '/section/documents', label: 'Documents' },
  { to: '/section/actualites', label: 'Actualités' },
  { to: '/section/programme', label: 'Programme' },
  { to: '/section/bureau', label: 'Bureau de section' },
  { to: '/section/courriers', label: 'Courriers' },
  { to: '/section/galerie', label: 'Galerie' },
  { to: '/section/notifications', label: 'Notifications' },
];

export default function SectionLayout({ children }: { children?: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showChangePassword, setShowChangePassword] = useState(false);

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar section-theme">
        <div className="sidebar-brand">
          Vicariat de l'Annonciation
          <small>Espace section</small>
        </div>
        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? 'active' : '')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <NotificationBell to="/section/notifications" />
          <div className="topbar-user">
            <strong>{user?.full_name}</strong>
            <div>Section</div>
          </div>
          <button className="btn btn-line btn-sm" onClick={() => setShowChangePassword(true)}>
            Mon compte
          </button>
          <button className="btn btn-line btn-sm" onClick={handleLogout}>
            Déconnexion
          </button>
        </header>
        <main className="main-content">{children ?? <Outlet />}</main>
      </div>
      {showChangePassword && <ChangePasswordModal onClose={() => setShowChangePassword(false)} />}
    </div>
  );
}
