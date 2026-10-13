import { useEffect, useState, type FormEvent } from 'react';
import { effectifsApi } from '../../api/resources';
import type { EffectifCategorieOut } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';

export default function EffectifsPage() {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const [items, setItems] = useState<EffectifCategorieOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<EffectifCategorieOut | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems(await effectifsApi.list());
    } catch {
      setError('Impossible de charger les effectifs.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const total = items.reduce((sum, i) => sum + i.effectif, 0);

  async function handleDelete(i: EffectifCategorieOut) {
    const ok = await confirm({ title: 'Supprimer cette catégorie ?', message: i.categorie, danger: true, confirmLabel: 'Supprimer' });
    if (!ok) return;
    try {
      await effectifsApi.remove(i.id);
      showToast('Catégorie supprimée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Effectifs globaux</h1>
          <p>Total actuel : {total} membres.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Nouvelle catégorie</button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && items.length === 0 && <EmptyState message="Aucune catégorie d'effectif." />}

      {!loading && !error && items.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Catégorie</th><th>Effectif</th><th></th></tr></thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id}>
                  <td>{i.categorie}</td>
                  <td>{i.effectif}</td>
                  <td>
                    <div className="section-actions">
                      <button className="btn btn-line btn-sm" onClick={() => setEditing(i)}>Modifier</button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(i)}>Supprimer</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && <EffectifFormModal onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />}
      {editing && <EffectifFormModal existing={editing} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function EffectifFormModal({ existing, onClose, onDone }: { existing?: EffectifCategorieOut; onClose: () => void; onDone: () => void }) {
  const { showError, showToast } = useToast();
  const [categorie, setCategorie] = useState(existing?.categorie || '');
  const [effectif, setEffectif] = useState(existing?.effectif ?? 0);
  const [displayOrder, setDisplayOrder] = useState(existing?.display_order ?? 0);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!existing && !categorie.trim()) {
      setFormError('Le nom de la catégorie est obligatoire.');
      return;
    }
    setSubmitting(true);
    try {
      if (existing) {
        await effectifsApi.update(existing.id, { effectif, display_order: displayOrder });
        showToast('Effectif mis à jour.', 'success');
      } else {
        await effectifsApi.create({ categorie: categorie.trim(), effectif, display_order: displayOrder });
        showToast('Catégorie créée.', 'success');
      }
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 420, width: '100%' }}>
        <h3>{existing ? 'Modifier la catégorie' : 'Nouvelle catégorie'}</h3>
        <form onSubmit={handleSubmit}>
          {!existing && (
            <div className="field">
              <label>Nom de la catégorie</label>
              <input value={categorie} onChange={(e) => setCategorie(e.target.value)} disabled={submitting} autoFocus />
            </div>
          )}
          <div className="field">
            <label>Effectif</label>
            <input type="number" min={0} value={effectif} onChange={(e) => setEffectif(Number(e.target.value))} disabled={submitting} />
          </div>
          <div className="field">
            <label>Ordre d'affichage</label>
            <input type="number" value={displayOrder} onChange={(e) => setDisplayOrder(Number(e.target.value))} disabled={submitting} />
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
