import { useCallback, useEffect, useState } from 'react';
import { auditLogApi } from '../../api/resources';
import type { AuditLogOut } from '../../api/types';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';
import { Pagination } from '../../components/Pagination';

const PAGE_SIZE = 30;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function AuditLogPage() {
  const [items, setItems] = useState<AuditLogOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [action, setAction] = useState('');
  const [resourceType, setResourceType] = useState('');
  const [result, setResult] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await auditLogApi.list({
        page,
        page_size: PAGE_SIZE,
        action: action || undefined,
        resource_type: resourceType || undefined,
        result: result || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError("Impossible de charger le journal d'audit.");
    } finally {
      setLoading(false);
    }
  }, [page, action, resourceType, result, dateFrom, dateTo]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Journal d'audit</h1>
          <p>Traçabilité des actions effectuées sur la plateforme.</p>
        </div>
      </div>

      <div className="filters-bar">
        <div className="field">
          <label>Action</label>
          <input value={action} onChange={(e) => { setPage(1); setAction(e.target.value); }} placeholder="ex. DOCUMENT_REJECTED" />
        </div>
        <div className="field">
          <label>Type de ressource</label>
          <input value={resourceType} onChange={(e) => { setPage(1); setResourceType(e.target.value); }} placeholder="ex. document" />
        </div>
        <div className="field">
          <label>Résultat</label>
          <select value={result} onChange={(e) => { setPage(1); setResult(e.target.value); }}>
            <option value="">Tous</option>
            <option value="SUCCESS">Succès</option>
            <option value="FAILURE">Échec</option>
          </select>
        </div>
        <div className="field">
          <label>Depuis</label>
          <input type="date" value={dateFrom} onChange={(e) => { setPage(1); setDateFrom(e.target.value); }} />
        </div>
        <div className="field">
          <label>Jusqu'au</label>
          <input type="date" value={dateTo} onChange={(e) => { setPage(1); setDateTo(e.target.value); }} />
        </div>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && items.length === 0 && <EmptyState message="Aucune entrée trouvée." />}

      {!loading && !error && items.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Date</th><th>Utilisateur</th><th>Action</th><th>Ressource</th><th>Résultat</th><th>IP</th></tr></thead>
            <tbody>
              {items.map((log) => (
                <tr key={log.id}>
                  <td>{formatDate(log.created_at)}</td>
                  <td>{log.user_label}</td>
                  <td>{log.action}</td>
                  <td>{log.resource_type}{log.resource_label ? ` — ${log.resource_label}` : ''}</td>
                  <td><span className={`badge ${log.result === 'SUCCESS' ? 'badge-published' : 'badge-refused'}`}>{log.result}</span></td>
                  <td>{log.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
    </div>
  );
}
