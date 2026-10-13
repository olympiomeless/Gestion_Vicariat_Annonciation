import { useCallback, useEffect, useState } from 'react';
import { notificationsApi } from '../../api/resources';
import type { NotificationOut } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';
import { Pagination } from '../../components/Pagination';

const TYPE_LABELS: Record<string, string> = {
  DOCUMENT_SUBMITTED: 'Document soumis',
  DOCUMENT_PUBLISHED: 'Document publié',
  DOCUMENT_REJECTED: 'Document refusé',
  ACTUALITE_SUBMITTED: 'Actualité soumise',
  ACTUALITE_PUBLISHED: 'Actualité publiée',
  ACTUALITE_REJECTED: 'Actualité refusée',
  PROGRAMME_SUBMITTED: 'Activité soumise',
  PROGRAMME_PUBLISHED: 'Activité publiée',
  PROGRAMME_REJECTED: 'Activité refusée',
  GALLERY_SUBMITTED: 'Photo soumise',
  GALLERY_PUBLISHED: 'Photo publiée',
  GALLERY_REJECTED: 'Photo refusée',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function NotificationsPage() {
  const { showError, showToast } = useToast();
  const [items, setItems] = useState<NotificationOut[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationsApi.list(page, pageSize);
      setItems(res.items);
      setTotal(res.total);
      setUnreadCount(res.unread_count);
    } catch {
      setError("Impossible de charger les notifications.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  async function markRead(id: string) {
    try {
      await notificationsApi.markRead(id);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      showError(err);
    }
  }

  async function markAllRead() {
    try {
      await notificationsApi.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      showToast('Toutes les notifications ont été marquées comme lues.', 'success');
    } catch (err) {
      showError(err);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Notifications</h1>
          <p>{unreadCount > 0 ? `${unreadCount} notification${unreadCount > 1 ? 's' : ''} non lue${unreadCount > 1 ? 's' : ''}` : 'Tout est lu.'}</p>
        </div>
        {unreadCount > 0 && (
          <button className="btn btn-line" onClick={markAllRead}>
            Tout marquer comme lu
          </button>
        )}
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && items.length === 0 && <EmptyState message="Aucune notification pour le moment." />}

      {!loading && !error && items.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map((n) => (
            <div
              key={n.id}
              className="card"
              style={{
                padding: '14px 16px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                gap: 12,
                background: n.is_read ? 'var(--surface)' : 'var(--primary-soft)',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '.82rem', color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '.02em' }}>
                  {TYPE_LABELS[n.type] || n.type}
                </div>
                <div style={{ marginTop: 3 }}>{n.message}</div>
                <div style={{ color: 'var(--ink-faint)', fontSize: '.8rem', marginTop: 4 }}>{formatDate(n.created_at)}</div>
              </div>
              {!n.is_read && (
                <button className="btn btn-line btn-sm" onClick={() => markRead(n.id)}>
                  Marquer comme lu
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
    </div>
  );
}
