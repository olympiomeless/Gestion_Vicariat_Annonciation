import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { sectionBureauApi, sectionsApi } from '../../api/resources';
import type { Section, SectionBureauMemberOut } from '../../api/types';
import { fetchAsObjectUrl } from '../../api/client';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { usePrompt } from '../../components/PromptDialog';
import { StatusBadge } from '../../components/StatusBadge';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';

/**
 * Bureau PROPRE à chaque section (distinct du Bureau du Vicariat, voir
 * admin/BureauPage.tsx, qui reste exclusivement administré par l'ADMIN).
 * Même workflow de validation que le programme : une section propose, un
 * administrateur publie ou refuse — voir backend/app/api/v1/section_bureau.py.
 */
export default function SectionBureauPage({ scope }: { scope: 'admin' | 'section' }) {
  const { user } = useAuth();
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const prompt = usePrompt();

  const [items, setItems] = useState<SectionBureauMemberOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [sections, setSections] = useState<Section[]>([]);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SectionBureauMemberOut | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await sectionBureauApi.list({
        status: statusFilter || undefined,
        section_id: scope === 'admin' ? sectionFilter || undefined : undefined,
      });
      setItems(res);
    } catch {
      setError('Impossible de charger le bureau de section.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, sectionFilter, scope]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (scope === 'admin') sectionsApi.list(true).then(setSections).catch(() => {});
  }, [scope]);

  async function handleApprove(m: SectionBureauMemberOut) {
    const ok = await confirm({ title: 'Publier ce membre ?', message: `« ${m.full_name} » sera visible publiquement.`, confirmLabel: 'Publier' });
    if (!ok) return;
    try {
      await sectionBureauApi.approve(m.id);
      showToast('Membre publié.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleReject(m: SectionBureauMemberOut) {
    const reason = await prompt({ title: 'Refuser ce membre', message: `Motif du refus de « ${m.full_name} » :`, confirmLabel: 'Refuser' });
    if (!reason) return;
    try {
      await sectionBureauApi.reject(m.id, reason);
      showToast('Membre refusé.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDelete(m: SectionBureauMemberOut) {
    const ok = await confirm({ title: 'Retirer ce membre ?', message: `« ${m.full_name} » sera définitivement retiré(e).`, danger: true, confirmLabel: 'Retirer' });
    if (!ok) return;
    try {
      await sectionBureauApi.remove(m.id);
      showToast('Membre retiré.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  const canManage = (m: SectionBureauMemberOut) => scope === 'admin' || (m.section_id === user?.section_id && m.status !== 'PUBLIE');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Bureau de section</h1>
          <p>
            {scope === 'admin'
              ? 'Modération des bureaux proposés par chaque section.'
              : 'Proposez les membres du bureau de votre section — soumis à validation du Bureau du Vicariat.'}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Ajouter un membre
        </button>
      </div>

      <div className="filters-bar">
        <div className="field">
          <label>Statut</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Tous</option>
            <option value="EN_ATTENTE">En attente</option>
            <option value="PUBLIE">Publié</option>
            <option value="REFUSE">Refusé</option>
          </select>
        </div>
        {scope === 'admin' && (
          <div className="field">
            <label>Section</label>
            <select value={sectionFilter} onChange={(e) => setSectionFilter(e.target.value)}>
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
      {!loading && !error && items.length === 0 && <EmptyState message="Aucun membre de bureau trouvé." />}

      {!loading && !error && items.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Photo</th>
                <th>Nom</th>
                <th>Fonction</th>
                {scope === 'admin' && <th>Section</th>}
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((m) => (
                <tr key={m.id}>
                  <td>
                    <MemberPhoto member={m} canManage={canManage(m)} onChanged={load} />
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{m.full_name}</div>
                    {m.status === 'REFUSE' && m.rejection_reason && (
                      <div style={{ color: 'var(--brick)', fontSize: '.8rem' }}>Motif : {m.rejection_reason}</div>
                    )}
                  </td>
                  <td>{m.role_title}</td>
                  {scope === 'admin' && <td>{m.section_name || '—'}</td>}
                  <td><StatusBadge status={m.status} /></td>
                  <td>
                    <div className="section-actions">
                      {scope === 'admin' && m.status === 'EN_ATTENTE' && (
                        <>
                          <button className="btn btn-primary btn-sm" onClick={() => handleApprove(m)}>Publier</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleReject(m)}>Refuser</button>
                        </>
                      )}
                      {canManage(m) && (
                        <>
                          <button className="btn btn-line btn-sm" onClick={() => setEditing(m)}>Modifier</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(m)}>Retirer</button>
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

      {showForm && (
        <SectionBureauFormModal sections={scope === 'admin' ? sections : []} onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />
      )}
      {editing && (
        <SectionBureauFormModal existing={editing} sections={[]} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />
      )}
    </div>
  );
}

function MemberPhoto({ member, canManage, onChanged }: { member: SectionBureauMemberOut; canManage: boolean; onChanged: () => void }) {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const inputRef = useRef<HTMLInputElement>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    if (member.has_photo) {
      fetchAsObjectUrl(sectionBureauApi.photoPath(member.id)).then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setSrc(url);
      }).catch(() => {});
    } else {
      setSrc(null);
    }
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [member.id, member.has_photo]);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setBusy(true);
    try {
      await sectionBureauApi.uploadPhoto(member.id, file);
      showToast('Photo mise à jour.', 'success');
      onChanged();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove() {
    const ok = await confirm({ title: 'Retirer cette photo ?', message: member.full_name, danger: true, confirmLabel: 'Retirer' });
    if (!ok) return;
    setBusy(true);
    try {
      await sectionBureauApi.removePhoto(member.id);
      showToast('Photo retirée.', 'success');
      onChanged();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {src ? (
        <img src={src} alt={member.full_name} style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover', border: '1px solid var(--line)' }} />
      ) : (
        <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'var(--surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.7rem', color: 'var(--ink-faint)' }}>—</div>
      )}
      {canManage && (
        <div className="section-actions">
          <button type="button" className="btn btn-line btn-sm" disabled={busy} onClick={() => inputRef.current?.click()}>
            {member.has_photo ? 'Changer' : 'Ajouter'}
          </button>
          {member.has_photo && (
            <button type="button" className="btn btn-danger btn-sm" disabled={busy} onClick={handleRemove}>Retirer</button>
          )}
        </div>
      )}
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" style={{ display: 'none' }} onChange={handleFile} />
    </div>
  );
}

function SectionBureauFormModal({
  existing,
  sections,
  onClose,
  onDone,
}: {
  existing?: SectionBureauMemberOut;
  sections: Section[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { showError, showToast } = useToast();
  const [fullName, setFullName] = useState(existing?.full_name || '');
  const [roleTitle, setRoleTitle] = useState(existing?.role_title || '');
  const [displayOrder, setDisplayOrder] = useState(existing?.display_order ?? 0);
  const [sectionId, setSectionId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!fullName.trim() || !roleTitle.trim()) {
      setFormError('Le nom et la fonction sont obligatoires.');
      return;
    }
    if (sections.length > 0 && !existing && !sectionId) {
      setFormError('Veuillez choisir la section de ce membre.');
      return;
    }
    setSubmitting(true);
    try {
      if (existing) {
        await sectionBureauApi.update(existing.id, {
          full_name: fullName.trim(),
          role_title: roleTitle.trim(),
          display_order: displayOrder,
        });
        showToast('Membre mis à jour.', 'success');
      } else {
        await sectionBureauApi.create({
          full_name: fullName.trim(),
          role_title: roleTitle.trim(),
          display_order: displayOrder,
          section_id: sectionId || undefined,
        });
        showToast('Membre proposé, en attente de validation.', 'success');
      }
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 460, width: '100%' }}>
        <h3>{existing ? 'Modifier le membre' : 'Ajouter un membre'}</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Nom complet</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} disabled={submitting} autoFocus />
          </div>
          <div className="field">
            <label>Fonction</label>
            <input value={roleTitle} onChange={(e) => setRoleTitle(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Ordre d'affichage</label>
            <input type="number" value={displayOrder} onChange={(e) => setDisplayOrder(Number(e.target.value))} disabled={submitting} />
          </div>
          {sections.length > 0 && !existing && (
            <div className="field">
              <label>Section</label>
              <select value={sectionId} onChange={(e) => setSectionId(e.target.value)} disabled={submitting}>
                <option value="">Choisir…</option>
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
