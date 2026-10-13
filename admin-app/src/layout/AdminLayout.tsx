import { useState, type ReactNode } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { NotificationBell } from '../components/NotificationBell';
import { ChangePasswordModal } from '../components/ChangePasswordModal';

const NAV: { to: string; label: string; end?: boolean }[] = [
  { to: '/admin', label: 'Tableau de bord', end: true },
  { to: '/admin/documents', label: 'Documents' },
  { to: '/admin/actualites', label: 'Actualités' },
  { to: '/admin/programme', label: 'Programme' },
  { to: '/admin/galerie', label: 'Galerie' },
  { to: '/admin/utilisateurs', label: 'Utilisateurs' },
  { to: '/admin/sections', label: 'Sections' },
  { to: '/admin/mouvement', label: 'Le mouvement' },
  { to: '/admin/bureau', label: 'Bureau' },
  { to: '/admin/bureau-sections', label: 'Bureaux de sections' },
  { to: '/admin/courriers', label: 'Courriers' },
  { to: '/admin/effectifs', label: 'Effectifs' },
  { to: '/admin/notifications', label: 'Notifications' },
  { to: '/admin/journal', label: "Journal d'audit" },
];

export default function AdminLayout({ children }: { children?: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showChangePassword, setShowChangePassword] = useState(false);

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Vicariat de l'Annonciation
          <small>Espace administration</small>
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
          <NotificationBell to="/admin/notifications" />
          <div className="topbar-user">
            <strong>{user?.full_name}</strong>
            <div>Administration</div>
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
