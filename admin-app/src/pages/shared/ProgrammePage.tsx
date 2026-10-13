import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { programmeApi, sectionsApi } from '../../api/resources';
import type { ProgrammeOut, Section } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { usePrompt } from '../../components/PromptDialog';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';

const PAGE_SIZE = 20;

function formatDate(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
}

export default function ProgrammePage({ scope }: { scope: 'admin' | 'section' }) {
  const { user } = useAuth();
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const prompt = usePrompt();

  const [items, setItems] = useState<ProgrammeOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [sections, setSections] = useState<Section[]>([]);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ProgrammeOut | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await programmeApi.list({
        page,
        page_size: PAGE_SIZE,
        status: statusFilter || undefined,
        section_id: scope === 'admin' ? sectionFilter || undefined : undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError('Impossible de charger le programme.');
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

  async function handleApprove(p: ProgrammeOut) {
    const ok = await confirm({ title: 'Publier cette activité ?', message: `« ${p.title} » sera visible publiquement.`, confirmLabel: 'Publier' });
    if (!ok) return;
    try {
      await programmeApi.approve(p.id);
      showToast('Activité publiée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleReject(p: ProgrammeOut) {
    const reason = await prompt({ title: 'Refuser cette activité', message: `Motif du refus de « ${p.title} » :`, confirmLabel: 'Refuser' });
    if (!reason) return;
    try {
      await programmeApi.reject(p.id, reason);
      showToast('Activité refusée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDelete(p: ProgrammeOut) {
    const ok = await confirm({ title: 'Supprimer cette activité ?', message: `« ${p.title} » sera définitivement supprimée.`, danger: true, confirmLabel: 'Supprimer' });
    if (!ok) return;
    try {
      await programmeApi.remove(p.id);
      showToast('Activité supprimée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  const canManage = (p: ProgrammeOut) => scope === 'admin' || (p.section_id === user?.section_id && p.status !== 'PUBLIE');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Programme</h1>
          <p>{scope === 'admin' ? 'Modération des activités de toutes les sections.' : 'Proposez de nouvelles activités.'}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Nouvelle activité
        </button>
      </div>

      <div className="filters-bar">
        <div className="field">
          <label>Statut</label>
          <select value={statusFilter} onChange={(e) => { setPage(1); setStatusFilter(e.target.value); }}>
            <option value="">Tous</option>
            <option value="EN_ATTENTE">En attente</option>
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
      {!loading && !error && items.length === 0 && <EmptyState message="Aucune activité trouvée." />}

      {!loading && !error && items.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Activité</th>
                <th>Date</th>
                <th>Lieu</th>
                {scope === 'admin' && <th>Section</th>}
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{p.title}</div>
                    {p.target_audience && <div style={{ color: 'var(--ink-faint)', fontSize: '.8rem' }}>{p.target_audience}</div>}
                    {p.status === 'REFUSE' && p.rejection_reason && (
                      <div style={{ color: 'var(--brick)', fontSize: '.8rem' }}>Motif : {p.rejection_reason}</div>
                    )}
                  </td>
                  <td>
                    {formatDate(p.activity_date)}
                    {p.activity_time && <div style={{ color: 'var(--ink-faint)', fontSize: '.8rem' }}>{p.activity_time.slice(0, 5)}</div>}
                  </td>
                  <td>{p.location || '—'}</td>
                  {scope === 'admin' && <td>{p.section_name || 'Vicariat'}</td>}
                  <td><StatusBadge status={p.status} /></td>
                  <td>
                    <div className="section-actions">
                      {scope === 'admin' && p.status === 'EN_ATTENTE' && (
                        <>
                          <button className="btn btn-primary btn-sm" onClick={() => handleApprove(p)}>Publier</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleReject(p)}>Refuser</button>
                        </>
                      )}
                      {canManage(p) && (
                        <>
                          <button className="btn btn-line btn-sm" onClick={() => setEditing(p)}>Modifier</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p)}>Supprimer</button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />

      {showForm && <ProgrammeFormModal sections={scope === 'admin' ? sections : []} onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />}
      {editing && <ProgrammeFormModal existing={editing} sections={[]} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function ProgrammeFormModal({
  existing,
  sections,
  onClose,
  onDone,
}: {
  existing?: ProgrammeOut;
  sections: Section[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { showError, showToast } = useToast();
  const [title, setTitle] = useState(existing?.title || '');
  const [description, setDescription] = useState(existing?.description || '');
  const [activityDate, setActivityDate] = useState(existing?.activity_date || '');
  const [activityTime, setActivityTime] = useState(existing?.activity_time?.slice(0, 5) || '');
  const [location, setLocation] = useState(existing?.location || '');
  const [targetAudience, setTargetAudience] = useState(existing?.target_audience || '');
  const [sectionId, setSectionId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!title.trim() || !activityDate) {
      setFormError('Le titre et la date sont obligatoires.');
      return;
    }
    setSubmitting(true);
    try {
      if (existing) {
        await programmeApi.update(existing.id, {
          title: title.trim(),
          description: description.trim(),
          activity_date: activityDate,
          activity_time: activityTime || undefined,
          location: location.trim(),
          target_audience: targetAudience.trim(),
        });
        showToast('Activité mise à jour.', 'success');
      } else {
        await programmeApi.create({
          title: title.trim(),
          description: description.trim() || undefined,
          activity_date: activityDate,
          activity_time: activityTime || undefined,
          location: location.trim() || undefined,
          target_audience: targetAudience.trim() || undefined,
          section_id: sectionId || undefined,
        });
        showToast('Activité créée, en attente de validation.', 'success');
      }
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16, overflowY: 'auto' }}>
      <div className="card" style={{ maxWidth: 520, width: '100%', margin: '30px 0' }}>
        <h3>{existing ? "Modifier l'activité" : 'Nouvelle activité'}</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Titre</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={submitting} autoFocus />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} disabled={submitting} />
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <div className="field" style={{ flex: 1 }}>
              <label>Date</label>
              <input type="date" value={activityDate} onChange={(e) => setActivityDate(e.target.value)} disabled={submitting} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Heure (optionnelle)</label>
              <input type="time" value={activityTime} onChange={(e) => setActivityTime(e.target.value)} disabled={submitting} />
            </div>
          </div>
          <div className="field">
            <label>Lieu</label>
            <input value={location} onChange={(e) => setLocation(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Public visé</label>
            <input value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)} disabled={submitting} />
          </div>
          {sections.length > 0 && !existing && (
            <div className="field">
              <label>Section (laisser vide pour "Vicariat")</label>
              <select value={sectionId} onChange={(e) => setSectionId(e.target.value)} disabled={submitting}>
                <option value="">Vicariat</option>
                {sections.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          )}
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
