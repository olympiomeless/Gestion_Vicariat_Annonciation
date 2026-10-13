import { useEffect, useState, type FormEvent } from 'react';
import { sectionsApi } from '../../api/resources';
import type { Section, SectionCreateResult } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';
import { PhotoUploader } from '../../components/PhotoUploader';

export default function SectionsPage() {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Section | null>(null);
  const [newCredentials, setNewCredentials] = useState<SectionCreateResult | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setSections(await sectionsApi.list(true));
    } catch {
      setError('Impossible de charger les sections.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleToggleActive(s: Section) {
    const action = s.is_active ? 'désactiver' : 'réactiver';
    const ok = await confirm({ title: `Voulez-vous ${action} cette section ?`, message: s.name, danger: s.is_active, confirmLabel: s.is_active ? 'Désactiver' : 'Réactiver' });
    if (!ok) return;
    try {
      await sectionsApi.update(s.id, { is_active: !s.is_active });
      showToast(`Section ${action}e.`, 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDelete(s: Section) {
    const ok = await confirm({ title: 'Supprimer cette section ?', message: `« ${s.name} » sera définitivement supprimée. Cette action n'est possible que si elle n'a plus de contenu associé.`, danger: true, confirmLabel: 'Supprimer' });
    if (!ok) return;
    try {
      await sectionsApi.remove(s.id);
      showToast('Section supprimée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Sections</h1>
          <p>Les 5 sections du Vicariat et leurs informations publiques.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Nouvelle section</button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && sections.length === 0 && <EmptyState message="Aucune section." />}

      {!loading && !error && sections.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Photo</th><th>Nom</th><th>Slug</th><th>Quartier</th><th>Responsable</th><th>Effectif</th><th>Statut</th><th></th></tr></thead>
            <tbody>
              {sections.map((s) => (
                <tr key={s.id}>
                  <td>
                    <PhotoUploader
                      hasPhoto={s.has_photo}
                      photoUrl={sectionsApi.photoUrl(s.id)}
                      alt={s.name}
                      onUpload={(file) => sectionsApi.uploadPhoto(s.id, file).then(load)}
                      onRemove={() => sectionsApi.removePhoto(s.id).then(load)}
                    />
                  </td>
                  <td>{s.name}</td>
                  <td>{s.slug}</td>
                  <td>{s.quartier || '—'}</td>
                  <td>{s.responsable_name || '—'}</td>
                  <td>{s.effectif_total}</td>
                  <td><span className={`badge ${s.is_active ? 'badge-published' : 'badge-refused'}`}>{s.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td>
                    <div className="section-actions">
                      <button className="btn btn-line btn-sm" onClick={() => setEditing(s)}>Modifier</button>
                      <button className="btn btn-line btn-sm" onClick={() => handleToggleActive(s)}>{s.is_active ? 'Désactiver' : 'Réactiver'}</button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(s)}>Supprimer</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <SectionFormModal
          onClose={() => setShowForm(false)}
          onDone={(created) => {
            setShowForm(false);
            load();
            if (created && created.generated_password) setNewCredentials(created);
          }}
        />
      )}
      {editing && <SectionFormModal existing={editing} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />}
      {newCredentials && <GeneratedCredentialsModal result={newCredentials} onClose={() => setNewCredentials(null)} />}
    </div>
  );
}

function SectionFormModal({
  existing,
  onClose,
  onDone,
}: {
  existing?: Section;
  onClose: () => void;
  onDone: (created?: SectionCreateResult) => void;
}) {
  const { showError, showToast } = useToast();
  const [slug, setSlug] = useState(existing?.slug || '');
  const [name, setName] = useState(existing?.name || '');
  const [badgeLabel, setBadgeLabel] = useState(existing?.badge_label || '');
  const [quartier, setQuartier] = useState(existing?.quartier || '');
  const [responsableName, setResponsableName] = useState(existing?.responsable_name || '');
  const [description, setDescription] = useState(existing?.description || '');
  const [effectifTotal, setEffectifTotal] = useState(existing?.effectif_total ?? 0);
  const [photoUrl, setPhotoUrl] = useState(existing?.photo_url || '');
  const [displayOrder, setDisplayOrder] = useState(existing?.display_order ?? 0);
  const [username, setUsername] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!name.trim() || (!existing && !slug.trim())) {
      setFormError('Le nom (et le slug pour une nouvelle section) sont obligatoires.');
      return;
    }
    setSubmitting(true);
    const common = {
      name: name.trim(),
      badge_label: badgeLabel.trim() || undefined,
      quartier: quartier.trim() || undefined,
      responsable_name: responsableName.trim() || undefined,
      description: description.trim() || undefined,
      effectif_total: effectifTotal,
      photo_url: photoUrl.trim() || undefined,
      display_order: displayOrder,
    };
    try {
      if (existing) {
        await sectionsApi.update(existing.id, common);
        showToast('Section mise à jour.', 'success');
        onDone();
      } else {
        const created = await sectionsApi.create({
          ...common,
          slug: slug.trim(),
          username: username.trim() ? username.trim().toLowerCase() : undefined,
        });
        showToast('Section créée.', 'success');
        onDone(created);
      }
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16, overflowY: 'auto' }}>
      <div className="card" style={{ maxWidth: 520, width: '100%', margin: '30px 0' }}>
        <h3>{existing ? 'Modifier la section' : 'Nouvelle section'}</h3>
        <form onSubmit={handleSubmit}>
          {!existing && (
            <div className="field">
              <label>Identifiant technique (slug — lettres minuscules, chiffres, tirets)</label>
              <input value={slug} onChange={(e) => setSlug(e.target.value)} disabled={submitting} autoFocus />
            </div>
          )}
          <div className="field">
            <label>Nom</label>
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Étiquette (badge)</label>
            <input value={badgeLabel} onChange={(e) => setBadgeLabel(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Quartier / paroisse</label>
            <input value={quartier} onChange={(e) => setQuartier(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Responsable</label>
            <input value={responsableName} onChange={(e) => setResponsableName(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} disabled={submitting} />
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <div className="field" style={{ flex: 1 }}>
              <label>Effectif total</label>
              <input type="number" min={0} value={effectifTotal} onChange={(e) => setEffectifTotal(Number(e.target.value))} disabled={submitting} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Ordre d'affichage</label>
              <input type="number" value={displayOrder} onChange={(e) => setDisplayOrder(Number(e.target.value))} disabled={submitting} />
            </div>
          </div>
          <div className="field">
            <label>URL de la photo</label>
            <input value={photoUrl} onChange={(e) => setPhotoUrl(e.target.value)} disabled={submitting} />
          </div>
          {!existing && (
            <div className="field">
              <label>Identifiant de connexion de la section (optionnel)</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={submitting}
                placeholder="ex. nda — laissez vide pour créer le compte plus tard"
              />
              <small style={{ color: 'var(--ink-faint)' }}>
                Si renseigné, un compte de connexion est créé en même temps, avec un mot de passe par défaut généré
                automatiquement — affiché une seule fois à la création.
              </small>
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

function GeneratedCredentialsModal({ result, onClose }: { result: SectionCreateResult; onClose: () => void }) {
  const { showToast } = useToast();

  async function copyToClipboard() {
    try {
      await navigator.clipboard.writeText(
        `Identifiant : ${result.generated_username}\nMot de passe : ${result.generated_password}`
      );
      showToast('Identifiants copiés.', 'success');
    } catch {
      /* le presse-papiers peut être indisponible — pas bloquant */
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1600, padding: 16 }}>
      <div className="card" style={{ maxWidth: 440, width: '100%' }}>
        <h3>Compte de connexion créé</h3>
        <p style={{ color: 'var(--ink-soft)' }}>
          Pour « {result.name} ». <strong>Ce mot de passe ne sera plus jamais affiché</strong> — notez-le ou transmettez-le
          maintenant à la section, qui pourra le changer dès sa première connexion (« Mon compte »).
        </p>
        <div className="field">
          <label>Identifiant</label>
          <input value={result.generated_username || ''} readOnly />
        </div>
        <div className="field">
          <label>Mot de passe par défaut</label>
          <input value={result.generated_password || ''} readOnly style={{ fontFamily: 'monospace' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
          <button type="button" className="btn btn-line" onClick={copyToClipboard}>Copier</button>
          <button type="button" className="btn btn-primary" onClick={onClose}>J'ai noté le mot de passe</button>
        </div>
      </div>
    </div>
  );
}
