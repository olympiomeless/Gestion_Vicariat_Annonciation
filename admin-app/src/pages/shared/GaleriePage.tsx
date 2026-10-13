import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { galleryApi, sectionsApi } from '../../api/resources';
import type { GalleryPhotoOut, Section } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { usePrompt } from '../../components/PromptDialog';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';
import { fetchAsObjectUrl } from '../../api/client';

const PAGE_SIZE = 24;

function PhotoThumb({ id }: { id: string }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchAsObjectUrl(galleryApi.fileUrl(id)).then((url) => {
      if (cancelled) {
        URL.revokeObjectURL(url);
        return;
      }
      objectUrl = url;
      setSrc(url);
    }).catch(() => {});
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  return (
    <div style={{ width: '100%', aspectRatio: '4/3', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {src ? <img src={src} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span style={{ color: 'var(--ink-faint)', fontSize: '.8rem' }}>Chargement…</span>}
    </div>
  );
}

export default function GaleriePage({ scope }: { scope: 'admin' | 'section' }) {
  const { user } = useAuth();
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const prompt = usePrompt();

  const [items, setItems] = useState<GalleryPhotoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [sections, setSections] = useState<Section[]>([]);
  const [showUpload, setShowUpload] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await galleryApi.list({
        page,
        page_size: PAGE_SIZE,
        status: statusFilter || undefined,
        section_id: scope === 'admin' ? sectionFilter || undefined : undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError('Impossible de charger la galerie.');
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

  async function handleApprove(p: GalleryPhotoOut) {
    const ok = await confirm({ title: 'Publier cette photo ?', message: 'Elle sera visible publiquement dans la galerie.', confirmLabel: 'Publier' });
    if (!ok) return;
    try {
      await galleryApi.approve(p.id);
      showToast('Photo publiée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleReject(p: GalleryPhotoOut) {
    const reason = await prompt({ title: 'Refuser cette photo', message: 'Motif du refus :', confirmLabel: 'Refuser' });
    if (!reason) return;
    try {
      await galleryApi.reject(p.id, reason);
      showToast('Photo refusée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDelete(p: GalleryPhotoOut) {
    const ok = await confirm({ title: 'Supprimer cette photo ?', message: 'Cette photo sera définitivement supprimée.', danger: true, confirmLabel: 'Supprimer' });
    if (!ok) return;
    try {
      await galleryApi.remove(p.id);
      showToast('Photo supprimée.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  const canManage = (p: GalleryPhotoOut) => scope === 'admin' || (p.section_id === user?.section_id && p.status !== 'PUBLIE');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Galerie</h1>
          <p>{scope === 'admin' ? 'Modération des photos de toutes les sections.' : 'Déposez vos photos pour validation.'}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
          + Déposer une photo
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
      {!loading && !error && items.length === 0 && <EmptyState message="Aucune photo trouvée." />}

      {!loading && !error && items.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
          {items.map((p) => (
            <div key={p.id} className="card" style={{ padding: 10 }}>
              <PhotoThumb id={p.id} />
              <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 6 }}>
                <div style={{ fontSize: '.85rem' }}>
                  {p.caption && <div style={{ fontWeight: 600 }}>{p.caption}</div>}
                  {scope === 'admin' && <div style={{ color: 'var(--ink-faint)' }}>{p.section_name || 'Vicariat'}</div>}
                </div>
                <StatusBadge status={p.status} />
              </div>
              {p.status === 'REFUSE' && p.rejection_reason && (
                <div style={{ color: 'var(--brick)', fontSize: '.78rem', marginTop: 4 }}>Motif : {p.rejection_reason}</div>
              )}
              <div className="section-actions" style={{ marginTop: 8 }}>
                {scope === 'admin' && p.status === 'EN_ATTENTE' && (
                  <>
                    <button className="btn btn-primary btn-sm" onClick={() => handleApprove(p)}>Publier</button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleReject(p)}>Refuser</button>
                  </>
                )}
                {canManage(p) && (
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p)}>Supprimer</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />

      {showUpload && (
        <GalleryUploadModal
          sections={scope === 'admin' ? sections : []}
          onClose={() => setShowUpload(false)}
          onDone={() => { setShowUpload(false); load(); }}
        />
      )}
    </div>
  );
}

function GalleryUploadModal({
  sections,
  onClose,
  onDone,
}: {
  sections: Section[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { showError, showToast } = useToast();
  const [caption, setCaption] = useState('');
  const [sectionId, setSectionId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!file) {
      setFormError('Veuillez choisir une image.');
      return;
    }
    setSubmitting(true);
    setProgress(0);
    try {
      await galleryApi.upload({ caption: caption.trim() || undefined, section_id: sectionId || undefined }, file, setProgress);
      showToast('Photo déposée. Elle sera visible après validation.', 'success');
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
      setProgress(null);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 460, width: '100%' }}>
        <h3>Déposer une photo</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Légende (optionnelle)</label>
            <input value={caption} onChange={(e) => setCaption(e.target.value)} disabled={submitting} autoFocus />
          </div>
          {sections.length > 0 && (
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
          <div className="field">
            <label>Image</label>
            <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} disabled={submitting} />
          </div>

          {progress !== null && (
            <div style={{ margin: '10px 0' }}>
              <div style={{ height: 8, background: 'var(--surface-3)', borderRadius: 999, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${progress}%`, background: 'var(--primary)', transition: 'width .15s ease' }} />
              </div>
              <div style={{ fontSize: '.78rem', color: 'var(--ink-faint)', marginTop: 3 }}>{progress}%</div>
            </div>
          )}

          {formError && <div className="field-error" style={{ marginBottom: 10 }}>{formError}</div>}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-line" onClick={onClose} disabled={submitting}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Envoi…' : 'Déposer'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
