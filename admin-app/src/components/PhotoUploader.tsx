import { useRef, useState } from 'react';
import { useToast } from './ToastContext';
import { useConfirm } from './ConfirmDialog';

/**
 * Miniature + boutons d'ajout/remplacement/retrait d'une photo (membre du
 * bureau ou section). L'aperçu utilise l'endpoint public (pas besoin
 * d'authentification pour un <img>) ; un paramètre de cache-buster force le
 * rechargement après un remplacement, car l'URL ne change jamais autrement.
 */
export function PhotoUploader({
  hasPhoto,
  photoUrl,
  alt,
  onUpload,
  onRemove,
}: {
  hasPhoto: boolean;
  photoUrl: string;
  alt: string;
  onUpload: (file: File) => Promise<unknown>;
  onRemove: () => Promise<unknown>;
}) {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [cacheBust, setCacheBust] = useState(0);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setBusy(true);
    try {
      await onUpload(file);
      setCacheBust((n) => n + 1);
      showToast('Photo mise à jour.', 'success');
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove() {
    const ok = await confirm({ title: 'Retirer cette photo ?', message: alt, danger: true, confirmLabel: 'Retirer' });
    if (!ok) return;
    setBusy(true);
    try {
      await onRemove();
      setCacheBust((n) => n + 1);
      showToast('Photo retirée.', 'success');
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {hasPhoto ? (
        <img
          src={`${photoUrl}?v=${cacheBust}`}
          alt={alt}
          style={{ width: 40, height: 40, borderRadius: '50%', objectFit: 'cover', border: '1px solid var(--line)' }}
        />
      ) : (
        <div
          style={{
            width: 40, height: 40, borderRadius: '50%', background: 'var(--surface-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.7rem', color: 'var(--ink-faint)',
          }}
        >
          —
        </div>
      )}
      <div className="section-actions">
        <button type="button" className="btn btn-line btn-sm" disabled={busy} onClick={() => inputRef.current?.click()}>
          {hasPhoto ? 'Changer' : 'Ajouter une photo'}
        </button>
        {hasPhoto && (
          <button type="button" className="btn btn-danger btn-sm" disabled={busy} onClick={handleRemove}>
            Retirer
          </button>
        )}
      </div>
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" style={{ display: 'none' }} onChange={handleFile} />
    </div>
  );
}
