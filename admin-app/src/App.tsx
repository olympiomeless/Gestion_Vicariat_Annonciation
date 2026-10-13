import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { ToastProvider } from './components/ToastContext';
import { ConfirmProvider } from './components/ConfirmDialog';
import { PromptProvider } from './components/PromptDialog';
import { ProtectedRoute, homeForRole } from './auth/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import AdminLayout from './layout/AdminLayout';
import SectionLayout from './layout/SectionLayout';

import AdminDashboardPage from './pages/admin/DashboardPage';
import UsersPage from './pages/admin/UsersPage';
import SectionsPage from './pages/admin/SectionsPage';
import MouvementPage from './pages/admin/MouvementPage';
import BureauPage from './pages/admin/BureauPage';
import EffectifsPage from './pages/admin/EffectifsPage';
import AuditLogPage from './pages/admin/AuditLogPage';

import SectionDashboardPage from './pages/section/DashboardPage';

import DocumentsPage from './pages/shared/DocumentsPage';
import ActualitesPage from './pages/shared/ActualitesPage';
import ProgrammePage from './pages/shared/ProgrammePage';
import SectionBureauPage from './pages/shared/SectionBureauPage';
import CourrierPage from './pages/shared/CourrierPage';
import GaleriePage from './pages/shared/GaleriePage';
import NotificationsPage from './pages/shared/NotificationsPage';

function RootRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={homeForRole(user.role)} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <ConfirmProvider>
          <PromptProvider>
            <Routes>
              <Route path="/" element={<RootRedirect />} />
              <Route path="/login" element={<LoginPage />} />

              <Route
                path="/admin"
                element={
                  <ProtectedRoute roles={['ADMIN']}>
                    <AdminLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<AdminDashboardPage />} />
                <Route path="documents" element={<DocumentsPage scope="admin" />} />
                <Route path="actualites" element={<ActualitesPage scope="admin" />} />
                <Route path="programme" element={<ProgrammePage scope="admin" />} />
                <Route path="galerie" element={<GaleriePage scope="admin" />} />
                <Route path="utilisateurs" element={<UsersPage />} />
                <Route path="sections" element={<SectionsPage />} />
                <Route path="mouvement" element={<MouvementPage />} />
                <Route path="bureau" element={<BureauPage />} />
                <Route path="bureau-sections" element={<SectionBureauPage scope="admin" />} />
                <Route path="courriers" element={<CourrierPage scope="admin" />} />
                <Route path="effectifs" element={<EffectifsPage />} />
                <Route path="notifications" element={<NotificationsPage />} />
                <Route path="journal" element={<AuditLogPage />} />
              </Route>

              <Route
                path="/section"
                element={
                  <ProtectedRoute roles={['SECTION']}>
                    <SectionLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<SectionDashboardPage />} />
                <Route path="documents" element={<DocumentsPage scope="section" />} />
                <Route path="actualites" element={<ActualitesPage scope="section" />} />
                <Route path="programme" element={<ProgrammePage scope="section" />} />
                <Route path="bureau" element={<SectionBureauPage scope="section" />} />
                <Route path="courriers" element={<CourrierPage scope="section" />} />
                <Route path="galerie" element={<GaleriePage scope="section" />} />
                <Route path="notifications" element={<NotificationsPage />} />
              </Route>

              <Route path="*" element={<RootRedirect />} />
            </Routes>
          </PromptProvider>
          </ConfirmProvider>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
