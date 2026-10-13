import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { courrierApi, sectionsApi } from '../../api/resources';
import type { CourrierOut, CourrierStatus, Section } from '../../api/types';
import { downloadFile } from '../../api/client';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';

/**
 * Courriers échangés entre une section et le Bureau du Vicariat : message
 * libre ou demande de fichier (ex. attestation de camp), traités par
 * l'administrateur sous forme de file d'attente — voir
 * backend/app/api/v1/courriers.py pour le workflow serveur.
 */
export default function CourrierPage({ scope }: { scope: 'admin' | 'section' }) {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();

  const [items, setItems] = useState<CourrierOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<CourrierStatus | ''>('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [sections, setSections] = useState<Section[]>([]);

  const [showForm, setShowForm] = useState(false);
  const [responding, setResponding] = useState<CourrierOut | null>(null);
  const [viewing, setViewing] = useState<CourrierOut | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await courrierApi.list({
        status: statusFilter || undefined,
        section_id: scope === 'admin' ? sectionFilter || undefined : undefined,
      });
      setItems(res);
    } catch {
      setError('Impossible de charger les courriers.');
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

  async function handleDelete(c: CourrierOut) {
    const ok = await confirm({
      title: 'Retirer ce courrier ?',
      message: `« ${c.subject} » sera définitivement retiré.`,
      danger: true,
      confirmLabel: 'Retirer',
    });
    if (!ok) return;
    try {
      await courrierApi.remove(c.id);
      showToast('Courrier retiré.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDownload(path: string, filename: string) {
    try {
      await downloadFile(path, filename);
    } catch (err) {
      showError(err);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Courriers</h1>
          <p>
            {scope === 'admin'
              ? 'Messages et demandes de fichiers reçus des sections.'
              : 'Envoyez un message ou une demande de fichier (ex. attestation de camp) au Bureau du Vicariat.'}
          </p>
        </div>
        {scope === 'section' && (
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            + Nouveau courrier
          </button>
        )}
      </div>

      <div className="filters-bar">
        <div className="field">
          <label>Statut</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as CourrierStatus | '')}>
            <option value="">Tous</option>
            <option value="NOUVEAU">Nouveau</option>
            <option value="TRAITE">Traité</option>
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
      {!loading && !error && items.length === 0 && <EmptyState message="Aucun courrier." />}

      {!loading && !error && items.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Objet</th>
                <th>Type</th>
                {scope === 'admin' && <th>Section</th>}
                <th>Statut</th>
                <th>Reçu le</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td style={{ fontWeight: 600 }}>{c.subject}</td>
                  <td>{c.kind === 'DEMANDE_FICHIER' ? 'Demande de fichier' : 'Message'}</td>
                  {scope === 'admin' && <td>{c.section_name || '—'}</td>}
                  <td><span className={`badge ${c.status === 'TRAITE' ? 'badge-published' : 'badge-pending'}`}>{c.status === 'TRAITE' ? 'Traité' : 'Nouveau'}</span></td>
                  <td>{new Date(c.created_at).toLocaleDateString('fr-FR')}</td>
                  <td>
                    <div className="section-actions">
                      <button className="btn btn-line btn-sm" onClick={() => setViewing(c)}>Voir</button>
                      {scope === 'admin' && c.status === 'NOUVEAU' && (
                        <button className="btn btn-primary btn-sm" onClick={() => setResponding(c)}>Traiter</button>
                      )}
                      {scope === 'section' && c.status === 'NOUVEAU' && (
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(c)}>Retirer</button>
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
        <CourrierFormModal onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />
      )}
      {responding && (
        <RespondModal courrier={responding} onClose={() => setResponding(null)} onDone={() => { setResponding(null); load(); }} />
      )}
      {viewing && (
        <ViewModal courrier={viewing} onClose={() => setViewing(null)} onDownload={handleDownload} />
      )}
    </div>
  );
}

function CourrierFormModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { showError, showToast } = useToast();
  const [kind, setKind] = useState<'MESSAGE' | 'DEMANDE_FICHIER'>('MESSAGE');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!subject.trim() || !body.trim()) {
      setFormError("L'objet et le message sont obligatoires.");
      return;
    }
    setSubmitting(true);
    try {
      await courrierApi.create(
        { kind, subject: subject.trim(), body: body.trim() },
        fileRef.current?.files?.[0] || null
      );
      showToast(kind === 'DEMANDE_FICHIER' ? 'Demande envoyée au Bureau du Vicariat.' : 'Message envoyé au Bureau du Vicariat.', 'success');
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16, overflowY: 'auto' }}>
      <div className="card" style={{ maxWidth: 520, width: '100%', margin: '30px 0' }}>
        <h3>Nouveau courrier au Bureau du Vicariat</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Type</label>
            <select value={kind} onChange={(e) => setKind(e.target.value as 'MESSAGE' | 'DEMANDE_FICHIER')} disabled={submitting}>
              <option value="MESSAGE">Message</option>
              <option value="DEMANDE_FICHIER">Demande de fichier (ex. attestation de camp)</option>
            </select>
          </div>
          <div className="field">
            <label>Objet</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} disabled={submitting} autoFocus />
          </div>
          <div className="field">
            <label>{kind === 'DEMANDE_FICHIER' ? 'Précisez votre demande (ex. « Attestation de camp pour Jean X »)' : 'Message'}</label>
            <textarea rows={5} value={body} onChange={(e) => setBody(e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label>Pièce jointe (optionnelle)</label>
            <input ref={fileRef} type="file" disabled={submitting} />
          </div>
          {formError && <div className="field-error" style={{ marginBottom: 10 }}>{formError}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-line" onClick={onClose} disabled={submitting}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Envoi…' : 'Envoyer'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RespondModal({ courrier, onClose, onDone }: { courrier: CourrierOut; onClose: () => void; onDone: () => void }) {
  const { showError, showToast } = useToast();
  const [responseNote, setResponseNote] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const file = fileRef.current?.files?.[0] || null;
    if (!responseNote.trim() && !file) {
      setFormError('Ajoutez une note et/ou un fichier de réponse.');
      return;
    }
    setSubmitting(true);
    try {
      await courrierApi.respond(courrier.id, responseNote.trim(), file);
      showToast('Courrier traité.', 'success');
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16, overflowY: 'auto' }}>
      <div className="card" style={{ maxWidth: 520, width: '100%', margin: '30px 0' }}>
        <h3>Traiter le courrier</h3>
        <p style={{ color: 'var(--ink-soft)' }}>« {courrier.subject} » — {courrier.section_name}</p>
        <p style={{ whiteSpace: 'pre-wrap', background: 'var(--surface-2)', padding: 10, borderRadius: 8 }}>{courrier.body}</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Note de réponse</label>
            <textarea rows={4} value={responseNote} onChange={(e) => setResponseNote(e.target.value)} disabled={submitting} autoFocus />
          </div>
          <div className="field">
            <label>{courrier.kind === 'DEMANDE_FICHIER' ? 'Fichier demandé (ex. attestation)' : 'Fichier joint (optionnel)'}</label>
            <input ref={fileRef} type="file" disabled={submitting} />
          </div>
          {formError && <div className="field-error" style={{ marginBottom: 10 }}>{formError}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-line" onClick={onClose} disabled={submitting}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Envoi…' : 'Marquer comme traité'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ViewModal({
  courrier,
  onClose,
  onDownload,
}: {
  courrier: CourrierOut;
  onClose: () => void;
  onDownload: (path: string, filename: string) => void;
}) {
  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16, overflowY: 'auto' }}>
      <div className="card" style={{ maxWidth: 520, width: '100%', margin: '30px 0' }}>
        <h3>{courrier.subject}</h3>
        <p style={{ color: 'var(--ink-soft)' }}>
          {courrier.section_name} · {courrier.kind === 'DEMANDE_FICHIER' ? 'Demande de fichier' : 'Message'} · {courrier.author_name}
        </p>
        <p style={{ whiteSpace: 'pre-wrap', background: 'var(--surface-2)', padding: 10, borderRadius: 8 }}>{courrier.body}</p>
        {courrier.has_attachment && (
          <p>
            <button
              className="btn btn-line btn-sm"
              onClick={() => onDownload(`/courriers/${courrier.id}/attachment`, courrier.attachment_original_filename || 'piece-jointe')}
            >
              Télécharger la pièce jointe {courrier.attachment_original_filename ? `(${courrier.attachment_original_filename})` : ''}
            </button>
          </p>
        )}
        {courrier.status === 'TRAITE' && (
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--line)' }}>
            <strong>Réponse du Bureau du Vicariat</strong>
            {courrier.response_note && <p style={{ whiteSpace: 'pre-wrap' }}>{courrier.response_note}</p>}
            {courrier.has_response_file && (
              <p>
                <button
                  className="btn btn-line btn-sm"
                  onClick={() => onDownload(`/courriers/${courrier.id}/response-file`, courrier.response_original_filename || 'reponse')}
                >
                  Télécharger le fichier de réponse {courrier.response_original_filename ? `(${courrier.response_original_filename})` : ''}
                </button>
              </p>
            )}
            <p style={{ color: 'var(--ink-faint)', fontSize: '.85rem' }}>
              Traité par {courrier.handled_by_name || '—'} le {courrier.handled_at ? new Date(courrier.handled_at).toLocaleString('fr-FR') : '—'}
            </p>
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
          <button type="button" className="btn btn-line" onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  );
}
