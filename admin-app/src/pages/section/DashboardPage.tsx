import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi } from '../../api/resources';
import type { SectionDashboardStats } from '../../api/types';
import { LoadingState, ErrorState } from '../../components/UiStates';
import { StatusBadge } from '../../components/StatusBadge';

export default function SectionDashboardPage() {
  const [stats, setStats] = useState<SectionDashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi
      .section()
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
          <h1>{stats.section_name}</h1>
          <p>Tableau de bord de votre section.</p>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card"><div className="stat-value">{stats.documents_count}</div><div className="stat-label">Documents</div></div>
        <div className="stat-card"><div className="stat-value">{stats.documents_pending_count}</div><div className="stat-label">En attente</div></div>
        <div className="stat-card"><div className="stat-value">{stats.documents_published_count}</div><div className="stat-label">Publiés</div></div>
        <div className="stat-card"><div className="stat-value">{stats.documents_refused_count}</div><div className="stat-label">Refusés</div></div>
        <div className="stat-card"><div className="stat-value">{stats.actualites_count}</div><div className="stat-label">Actualités</div></div>
        <div className="stat-card"><div className="stat-value">{stats.programmes_count}</div><div className="stat-label">Activités</div></div>
        <div className="stat-card"><div className="stat-value">{stats.gallery_photos_count}</div><div className="stat-label">Photos</div></div>
      </div>

      <h2>Vos documents récents</h2>
      {stats.recent_documents.length === 0 ? (
        <p style={{ color: 'var(--ink-faint)' }}>Aucun document déposé pour l'instant.</p>
      ) : (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Nom</th><th>Statut</th></tr></thead>
            <tbody>
              {stats.recent_documents.map((d) => (
                <tr key={d.id}><td>{d.name}</td><td><StatusBadge status={d.status} /></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p><Link to="/section/documents">Gérer vos documents →</Link></p>
    </div>
  );
}
