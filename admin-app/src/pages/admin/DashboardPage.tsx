import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi } from '../../api/resources';
import type { AdminDashboardStats } from '../../api/types';
import { LoadingState, ErrorState } from '../../components/UiStates';
import { StatusBadge } from '../../components/StatusBadge';

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi
      .admin()
      .then(setStats)
      .catch(() => setError('Impossible de charger le tableau de bord.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error || !stats) return <ErrorState message={error || 'Erreur inconnue.'} />;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Tableau de bord</h1>
          <p>Vue d'ensemble du Vicariat de l'Annonciation.</p>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card"><div className="stat-value">{stats.sections_count}</div><div className="stat-label">Sections</div></div>
        <div className="stat-card"><div className="stat-value">{stats.users_active_count}/{stats.users_count}</div><div className="stat-label">Comptes actifs</div></div>
        <div className="stat-card"><div className="stat-value">{stats.documents_count}</div><div className="stat-label">Documents</div></div>
        <div className="stat-card"><div className="stat-value">{stats.documents_pending_count}</div><div className="stat-label">Documents en attente</div></div>
        <div className="stat-card"><div className="stat-value">{stats.actualites_pending_count}</div><div className="stat-label">Actualités à valider</div></div>
        <div className="stat-card"><div className="stat-value">{stats.programmes_count}</div><div className="stat-label">Activités programmées</div></div>
        <div className="stat-card"><div className="stat-value">{stats.gallery_photos_pending_count}</div><div className="stat-label">Photos en attente</div></div>
      </div>

      <h2>Documents en attente de validation</h2>
      {stats.pending_documents.length === 0 ? (
        <p style={{ color: 'var(--ink-faint)' }}>Rien à valider pour le moment.</p>
      ) : (
        <div className="card" style={{ padding: 0, overflowX: 'auto', marginBottom: 26 }}>
          <table>
            <thead><tr><th>Nom</th><th>Section</th><th>Statut</th></tr></thead>
            <tbody>
              {stats.pending_documents.map((d) => (
                <tr key={d.id}><td>{d.name}</td><td>{d.section_name || 'Vicariat'}</td><td><StatusBadge status={d.status} /></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p><Link to="/admin/documents">Voir tous les documents →</Link></p>

      <h2 style={{ marginTop: 26 }}>Répartition par section</h2>
      <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
        <table>
          <thead><tr><th>Section</th><th>Comptes</th><th>Documents</th><th>En attente</th></tr></thead>
          <tbody>
            {stats.sections_breakdown.map((s) => (
              <tr key={s.section_id}>
                <td>{s.section_name}</td>
                <td>{s.users_count}</td>
                <td>{s.documents_count}</td>
                <td>{s.documents_pending_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
