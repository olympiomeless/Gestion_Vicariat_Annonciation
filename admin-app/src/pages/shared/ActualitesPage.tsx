import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { actualitesApi, sectionsApi } from '../../api/resources';
import type { ActualiteOut, Section } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { usePrompt } from '../../components/PromptDialog';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';

const PAGE_SIZE = 20;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function ActualitesPage({ scope }: { scope: 'admin' | 'section' }) {
  const { user } = useAuth();
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const prompt = usePrompt();

  const [items, setItems] = useState<ActualiteOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [sections, setSections] = useState<Section[]>([]);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ActualiteOut | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await actualitesApi.list({
        page,
        page_size: PAGE_SIZE,
        status: statusFilter || undefined,
        section_id: scope === 'admin' ? sectionFilter || undefined : undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError('Impossible de charger les actualités.');
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, sectionFilter, scope]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (scope === 'admin') sectionsApi.list(true).then(setSections).catch(() => {});
  }, [scope]);

  async function handleSubmitForValidation(a: ActualiteOut) {
    const ok = await confirm({ title: 'Soumettre cette actualité ?', message: `« ${a.title} » sera envoyée à l'administration pour validation.`, confirmLabel: 'Soumettre' });
    if (!ok) return;
    try {
      await actualitesApi.submit(a.id);
      showToast('Actualité soumise pour validation.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleApprove(a: ActualiteOut) {
    const ok = await confirm({ title: 'Publier cette actualité ?', message: `« ${a.title} » sera visible publiquement.`, confirmLabel: 'Publier' });
    if (!ok) return;
    try {
      await actualitesApi.approve(a.id);
      showToast('Actualité publiée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleReject(a: ActualiteOut) {
    const reason = await prompt({ title: 'Refuser cette actualité', message: `Motif du refus de « ${a.title} » :`, confirmLabel: 'Refuser' });
    if (!reason) return;
    try {
      await actualitesApi.reject(a.id, reason);
      showToast('Actualité refusée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDelete(a: ActualiteOut) {
    const ok = await confirm({ title: 'Supprimer cette actualité ?', message: `« ${a.title} » sera définitivement supprimée.`, danger: true, confirmLabel: 'Supprimer' });
    if (!ok) return;
    try {
      await actualitesApi.remove(a.id);
      showToast('Actualité supprimée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  const canManage = (a: ActualiteOut) => scope === 'admin' || a.section_id === user?.section_id;
  const canEdit = (a: ActualiteOut) => canManage(a) && (a.status === 'BROUILLON' || a.status === 'REFUSE' || scope === 'admin');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Actualités</h1>
          <p>{scope === 'admin' ? 'Modération des actualités de toutes les sections.' : 'Rédigez, soumettez et suivez vos actualités.'}</p>
        </div>
        {scope === 'section' && (
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            + Nouvelle actualité
          </button>
        )}
      </div>

      <div className="filters-bar">
        <div className="field">
          <label>Statut</label>
          <select value={statusFilter} onChange={(e) => { setPage(1); setStatusFilter(e.target.value); }}>
            <option value="">Tous</option>
            <option value="BROUILLON">Brouillon</option>
            <option value="SOUMIS">Soumis</option>
            <option value="PUBLIE">Publié</option>
            <option value="REFUSE">Refusé</option>
          </select>
        </div>
        {scope === 'admin' && (
          <div className="field">
            <label>Section</label>
            <select value={sectionFilter} onChange={(e) => { setPage(1); setSectionFilter(e.target.value); }}>
              <option value="">Toutes</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && items.length === 0 && <EmptyState message="Aucune actualité trouvée." />}

      {!loading && !error && items.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((a) => (
            <div key={a.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ marginBottom: 2 }}>{a.title}</h3>
                  <div style={{ color: 'var(--ink-faint)', fontSize: '.82rem' }}>
                    {scope === 'admin' ? `${a.section_name || 'Vicariat'} · ` : ''}
                    {formatDate(a.created_at)}
                  </div>
                </div>
                <StatusBadge status={a.status} />
              </div>
              <p style={{ color: 'var(--ink-soft)', marginTop: 10, whiteSpace: 'pre-wrap' }}>{a.body}</p>
              {a.status === 'REFUSE' && a.rejection_reason && (
                <div style={{ color: 'var(--brick)', fontSize: '.85rem' }}>Motif du refus : {a.rejection_reason}</div>
              )}
              <div className="section-actions" style={{ marginTop: 10 }}>
                {scope === 'section' && a.section_id === user?.section_id && (a.status === 'BROUILLON' || a.status === 'REFUSE') && (
                  <button className="btn btn-primary btn-sm" onClick={() => handleSubmitForValidation(a)}>Soumettre à validation</button>
                )}
                {scope === 'admin' && a.status === 'SOUMIS' && (
                  <>
                    <button className="btn btn-primary btn-sm" onClick={() => handleApprove(a)}>Publier</button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleReject(a)}>Refuser</button>
                  </>
                )}
                {canEdit(a) && (
                  <button className="btn btn-line btn-sm" onClick={() => setEditing(a)}>Modifier</button>
                )}
                {canManage(a) && (
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(a)}>Supprimer</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />

      {showForm && (
        <ActualiteFormModal onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />
      )}
      {editing && (
        <ActualiteFormModal existing={editing} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />
      )}
    </div>
  );
}

function ActualiteFormModal({
  existing,
  onClose,
  onDone,
}: {
  existing?: ActualiteOut;
  onClose: () => void;
  onDone: () => void;
}) {
  const { showError, showToast } = useToast();
  const [title, setTitle] = useState(existing?.title || '');
  const [body, setBody] = useState(existing?.body || '');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!title.trim() || !body.trim()) {
      setFormError('Le titre et le contenu sont obligatoires.');
      return;
    }
    setSubmitting(true);
    try {
      if (existing) {
        await actualitesApi.update(existing.id, { title: title.trim(), body: body.trim() });
        showToast('Actualité mise à jour.', 'success');
      } else {
        await actualitesApi.create({ title: title.trim(), body: body.trim() });
        showToast('Actualité créée en brouillon.', 'success');
      }
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 560, width: '100%' }}>
        <h3>{existing ? "Modifier l'actualité" : 'Nouvelle actualité'}</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Titre</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={submitting} autoFocus />
          </div>
          <div className="field">
            <label>Contenu</label>
            <textarea rows={7} value={body} onChange={(e) => setBody(e.target.value)} disabled={submitting} />
          </div>
          {formError && <div className="field-error" style={{ marginBottom: 10 }}>{formError}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-line" onClick={onClose} disabled={submitting}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
