import { useState, type FormEvent } from 'react';
import { authApi } from '../api/resources';
import { useToast } from './ToastContext';

/**
 * Changement de mot de passe en libre-service — chaque section reçoit un
 * mot de passe par défaut à la création de son compte et peut le changer
 * elle-même ici (point 7 de la demande initiale). L'API existait déjà
 * (POST /auth/change-password) mais n'avait aucune interface avant ceci.
 */
export function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const { showError, showToast } = useToast();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!currentPassword || !newPassword) {
      setFormError('Veuillez renseigner votre mot de passe actuel et le nouveau.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setFormError('Les deux mots de passe ne correspondent pas.');
      return;
    }
    setSubmitting(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      showToast('Mot de passe changé. Veuillez vous reconnecter si vous êtes déconnecté(e) sur un autre appareil.', 'success');
      onClose();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 420, width: '100%' }}>
        <h3>Changer mon mot de passe</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Mot de passe actuel</label>
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              disabled={submitting}
              autoFocus
            />
          </div>
          <div className="field">
            <label>Nouveau mot de passe (10+ car., majuscule, minuscule, chiffre)</label>
            <input
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={submitting}
            />
          </div>
          <div className="field">
            <label>Confirmer le nouveau mot de passe</label>
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={submitting}
            />
          </div>
          {formError && <div className="field-error" style={{ marginBottom: 10 }}>{formError}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-line" onClick={onClose} disabled={submitting}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Enregistrement…' : 'Changer'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
