import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { categoriesApi, documentsApi, sectionsApi } from '../../api/resources';
import type { DocumentCategory, DocumentOut, Section } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { usePrompt } from '../../components/PromptDialog';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';
import { downloadFile } from '../../api/client';

const PAGE_SIZE = 20;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function DocumentsPage({ scope }: { scope: 'admin' | 'section' }) {
  const { user } = useAuth();
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const prompt = usePrompt();

  const [items, setItems] = useState<DocumentOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [categories, setCategories] = useState<DocumentCategory[]>([]);
  const [sections, setSections] = useState<Section[]>([]);

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');

  const [showUpload, setShowUpload] = useState(false);
  const [editing, setEditing] = useState<DocumentOut | null>(null);
  const [showCategories, setShowCategories] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await documentsApi.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        category_id: categoryFilter || undefined,
        status: statusFilter || undefined,
        section_id: scope === 'admin' ? sectionFilter || undefined : undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError('Impossible de charger les documents.');
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryFilter, statusFilter, sectionFilter, scope]);

  useEffect(() => {
    load();
  }, [load]);

  const loadCategories = useCallback(() => {
    categoriesApi.list().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    loadCategories();
    if (scope === 'admin') sectionsApi.list(true).then(setSections).catch(() => {});
  }, [scope, loadCategories]);

  async function handleApprove(doc: DocumentOut) {
    const ok = await confirm({ title: 'Publier ce document ?', message: `« ${doc.name} » sera visible publiquement.`, confirmLabel: 'Publier' });
    if (!ok) return;
    try {
      await documentsApi.approve(doc.id);
      showToast('Document publié.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleReject(doc: DocumentOut) {
    const reason = await prompt({ title: 'Refuser ce document', message: `Motif du refus de « ${doc.name} » (visible par la section) :`, confirmLabel: 'Refuser' });
    if (!reason) return;
    try {
      await documentsApi.reject(doc.id, reason);
      showToast('Document refusé.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDelete(doc: DocumentOut) {
    const ok = await confirm({ title: 'Supprimer ce document ?', message: `« ${doc.name} » sera définitivement supprimé.`, danger: true, confirmLabel: 'Supprimer' });
    if (!ok) return;
    try {
      await documentsApi.remove(doc.id);
      showToast('Document supprimé.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDownload(doc: DocumentOut) {
    try {
      await downloadFile(documentsApi.downloadUrl(doc.id), doc.original_filename);
    } catch (err) {
      showError(err);
    }
  }

  const canManage = (doc: DocumentOut) =>
    scope === 'admin' || (doc.section_id === user?.section_id && doc.status !== 'PUBLIE');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Documents</h1>
          <p>{scope === 'admin' ? 'Bibliothèque complète — toutes sections.' : 'Vos documents et les documents publiés.'}</p>
        </div>
        <div className="section-actions">
          {scope === 'admin' && (
            <button className="btn btn-line" onClick={() => setShowCategories(true)}>
              Gérer les catégories
            </button>
          )}
          <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
            + Déposer un document
          </button>
        </div>
      </div>

      <div className="filters-bar">
        <div className="field">
          <label>Recherche</label>
          <input value={search} onChange={(e) => { setPage(1); setSearch(e.target.value); }} placeholder="Nom du document…" />
        </div>
        <div className="field">
          <label>Catégorie</label>
          <select value={categoryFilter} onChange={(e) => { setPage(1); setCategoryFilter(e.target.value); }}>
            <option value="">Toutes</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
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
      {!loading && !error && items.length === 0 && <EmptyState message="Aucun document trouvé." />}

      {!loading && !error && items.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>Catégorie</th>
                {scope === 'admin' && <th>Section</th>}
                <th>Taille</th>
                <th>Statut</th>
                <th>Déposé le</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{doc.name}</div>
                    <div style={{ color: 'var(--ink-faint)', fontSize: '.8rem' }}>{doc.original_filename}</div>
                    {doc.status === 'REFUSE' && doc.rejection_reason && (
                      <div style={{ color: 'var(--brick)', fontSize: '.8rem', marginTop: 2 }}>Motif : {doc.rejection_reason}</div>
                    )}
                  </td>
                  <td>{doc.category_name}</td>
                  {scope === 'admin' && <td>{doc.section_name || 'Vicariat'}</td>}
                  <td>{formatSize(doc.size_bytes)}</td>
                  <td><StatusBadge status={doc.status} /></td>
                  <td>{formatDate(doc.created_at)}</td>
                  <td>
                    <div className="section-actions">
                      <button className="btn btn-line btn-sm" onClick={() => handleDownload(doc)}>Télécharger</button>
                      {scope === 'admin' && doc.status === 'EN_ATTENTE' && (
                        <>
                          <button className="btn btn-primary btn-sm" onClick={() => handleApprove(doc)}>Publier</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleReject(doc)}>Refuser</button>
                        </>
                      )}
                      {canManage(doc) && (
                        <>
                          <button className="btn btn-line btn-sm" onClick={() => setEditing(doc)}>Modifier</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(doc)}>Supprimer</button>
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

      {showUpload && (
        <UploadModal
          categories={categories}
          sections={scope === 'admin' ? sections : []}
          onClose={() => setShowUpload(false)}
          onDone={() => { setShowUpload(false); load(); }}
        />
      )}

      {editing && (
        <EditModal
          doc={editing}
          categories={categories}
          onClose={() => setEditing(null)}
          onDone={() => { setEditing(null); load(); }}
        />
      )}

      {showCategories && (
        <CategoriesModal
          categories={categories}
          onClose={() => setShowCategories(false)}
          onChanged={loadCategories}
        />
      )}
    </div>
  );
}

function CategoriesModal({
  categories,
  onClose,
  onChanged,
}: {
  categories: DocumentCategory[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await categoriesApi.create(name.trim());
      setName('');
      onChanged();
      showToast('Catégorie créée.', 'success');
    } catch (err) {
      showError(err);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(cat: DocumentCategory) {
    const ok = await confirm({
      title: 'Supprimer cette catégorie ?',
      message: `« ${cat.name} » — possible seulement si aucun document ne l'utilise.`,
      danger: true,
      confirmLabel: 'Supprimer',
    });
    if (!ok) return;
    try {
      await categoriesApi.remove(cat.id);
      onChanged();
      showToast('Catégorie supprimée.', 'success');
    } catch (err) {
      showError(err);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 440, width: '100%' }}>
        <h3>Catégories de documents</h3>
        {categories.length === 0 ? (
          <p style={{ color: 'var(--ink-faint)' }}>Aucune catégorie pour l'instant — créez-en une ci-dessous pour permettre les dépôts de documents.</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {categories.map((c) => (
              <li key={c.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 10px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)' }}>
                <span>{c.name}{c.is_system && <span style={{ color: 'var(--ink-faint)', fontSize: '.78rem' }}> (système)</span>}</span>
                {!c.is_system && (
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(c)}>Supprimer</button>
                )}
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 8 }}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nouvelle catégorie…" disabled={submitting} style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 'var(--radius-sm)', padding: '9px 11px' }} />
          <button type="submit" className="btn btn-primary" disabled={submitting || !name.trim()}>Ajouter</button>
        </form>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
          <button type="button" className="btn btn-line" onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  );
}

function UploadModal({
  categories,
  sections,
  onClose,
  onDone,
}: {
  categories: DocumentCategory[];
  sections: Section[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { showError, showToast } = useToast();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [sectionId, setSectionId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!name.trim() || !categoryId || !file) {
      setFormError('Veuillez renseigner le nom, la catégorie et choisir un fichier.');
      return;
    }
    setSubmitting(true);
    setProgress(0);
    try {
      await documentsApi.upload(
        { name: name.trim(), description: description.trim() || undefined, category_id: categoryId, section_id: sectionId || undefined },
        file,
        setProgress
      );
      showToast('Document déposé. Il sera visible après validation.', 'success');
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
      setProgress(null);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 480, width: '100%' }}>
        <h3>Déposer un document</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Nom du document</label>
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={submitting} autoFocus />
          </div>
          <div className="field">
            <label>Description (optionnelle)</label>
            <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Catégorie</label>
            <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} disabled={submitting}>
              <option value="">Choisir…</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
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
            <label>Fichier</label>
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} disabled={submitting} />
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
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Envoi…' : 'Déposer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditModal({
  doc,
  categories,
  onClose,
  onDone,
}: {
  doc: DocumentOut;
  categories: DocumentCategory[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { showError, showToast } = useToast();
  const [name, setName] = useState(doc.name);
  const [description, setDescription] = useState(doc.description || '');
  const [categoryId, setCategoryId] = useState(doc.category_id);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await documentsApi.update(doc.id, { name: name.trim(), description: description.trim(), category_id: categoryId });
      showToast('Document mis à jour.', 'success');
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 460, width: '100%' }}>
        <h3>Modifier le document</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Nom</label>
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={submitting} autoFocus />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Catégorie</label>
            <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} disabled={submitting}>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-line" onClick={onClose} disabled={submitting}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
