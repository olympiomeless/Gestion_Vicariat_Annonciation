import { useEffect, useState, type FormEvent } from 'react';
import { bureauApi } from '../../api/resources';
import type { BureauMemberOut } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';
import { PhotoUploader } from '../../components/PhotoUploader';

export default function BureauPage() {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const [members, setMembers] = useState<BureauMemberOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<BureauMemberOut | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setMembers(await bureauApi.list());
    } catch {
      setError('Impossible de charger le bureau.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(m: BureauMemberOut) {
    const ok = await confirm({ title: 'Retirer ce membre du bureau ?', message: m.full_name, danger: true, confirmLabel: 'Retirer' });
    if (!ok) return;
    try {
      await bureauApi.remove(m.id);
      showToast('Membre retiré.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleToggleActive(m: BureauMemberOut) {
    try {
      await bureauApi.update(m.id, { is_active: !m.is_active });
      showToast(m.is_active ? 'Membre masqué du site public.' : 'Membre affiché sur le site public.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Bureau</h1>
          <p>Membres du bureau affichés sur le site public.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Ajouter un membre</button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && members.length === 0 && <EmptyState message="Aucun membre du bureau." />}

      {!loading && !error && members.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Photo</th><th>Nom</th><th>Fonction</th><th>Paroisse</th><th>Rang</th><th>Visible</th><th></th></tr></thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id}>
                  <td>
                    <PhotoUploader
                      hasPhoto={m.has_photo}
                      photoUrl={bureauApi.photoUrl(m.id)}
                      alt={m.full_name}
                      onUpload={(file) => bureauApi.uploadPhoto(m.id, file).then(load)}
                      onRemove={() => bureauApi.removePhoto(m.id).then(load)}
                    />
                  </td>
                  <td>{m.full_name}</td>
                  <td>{m.role_title}</td>
                  <td>{m.paroisse || '—'}</td>
                  <td>{m.rang || '—'}</td>
                  <td><span className={`badge ${m.is_active ? 'badge-published' : 'badge-draft'}`}>{m.is_active ? 'Oui' : 'Non'}</span></td>
                  <td>
                    <div className="section-actions">
                      <button className="btn btn-line btn-sm" onClick={() => setEditing(m)}>Modifier</button>
                      <button className="btn btn-line btn-sm" onClick={() => handleToggleActive(m)}>{m.is_active ? 'Masquer' : 'Afficher'}</button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(m)}>Retirer</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && <BureauFormModal onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />}
      {editing && <BureauFormModal existing={editing} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function BureauFormModal({ existing, onClose, onDone }: { existing?: BureauMemberOut; onClose: () => void; onDone: () => void }) {
  const { showError, showToast } = useToast();
  const [fullName, setFullName] = useState(existing?.full_name || '');
  const [roleTitle, setRoleTitle] = useState(existing?.role_title || '');
  const [paroisse, setParoisse] = useState(existing?.paroisse || '');
  const [rang, setRang] = useState(existing?.rang || '');
  const [displayOrder, setDisplayOrder] = useState(existing?.display_order ?? 0);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!fullName.trim() || !roleTitle.trim()) {
      setFormError('Le nom et la fonction sont obligatoires.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = { full_name: fullName.trim(), role_title: roleTitle.trim(), paroisse: paroisse.trim() || undefined, rang: rang.trim() || undefined, display_order: displayOrder };
      if (existing) {
        await bureauApi.update(existing.id, payload);
        showToast('Membre mis à jour.', 'success');
      } else {
        await bureauApi.create({ ...payload, is_active: true });
        showToast('Membre ajouté.', 'success');
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
            <label>Paroisse</label>
            <input value={paroisse} onChange={(e) => setParoisse(e.target.value)} disabled={submitting} />
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <div className="field" style={{ flex: 1 }}>
              <label>Rang</label>
              <input value={rang} onChange={(e) => setRang(e.target.value)} disabled={submitting} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Ordre d'affichage</label>
              <input type="number" value={displayOrder} onChange={(e) => setDisplayOrder(Number(e.target.value))} disabled={submitting} />
            </div>
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
