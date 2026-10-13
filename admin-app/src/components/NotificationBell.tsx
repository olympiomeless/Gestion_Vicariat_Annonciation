import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { notificationsApi } from '../api/resources';

// Petite pastille de notifications non lues, rafraîchie périodiquement.
// Le lien renvoie vers la page complète des notifications de l'espace actif.
export function NotificationBell({ to }: { to: string }) {
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await notificationsApi.list(1, 1);
        if (!cancelled) setUnread(res.unread_count);
      } catch {
        // silencieux : la pastille n'est pas critique
      }
    }
    load();
    const interval = setInterval(load, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <Link to={to} style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', color: 'inherit', textDecoration: 'none' }}>
      <span aria-hidden="true" style={{ fontSize: '1.2rem' }}>
        🔔
      </span>
      {unread > 0 && (
        <span
          style={{
            position: 'absolute',
            top: -6,
            right: -10,
            background: 'var(--brick)',
            color: '#fff',
            borderRadius: 999,
            fontSize: '.68rem',
            fontWeight: 700,
            padding: '1px 6px',
            lineHeight: 1.4,
          }}
        >
          {unread > 99 ? '99+' : unread}
        </span>
      )}
    </Link>
  );
}
