import { useEffect, useState, type FormEvent } from 'react';
import { usersApi, sectionsApi } from '../../api/resources';
import type { UserAdminOut, Section } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { useConfirm } from '../../components/ConfirmDialog';
import { LoadingState, ErrorState, EmptyState } from '../../components/UiStates';

function formatDate(iso: string | null): string {
  if (!iso) return 'Jamais';
  return new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function UsersPage() {
  const { showError, showToast } = useToast();
  const confirm = useConfirm();

  const [users, setUsers] = useState<UserAdminOut[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<UserAdminOut | null>(null);
  const [resetTarget, setResetTarget] = useState<UserAdminOut | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [u, s] = await Promise.all([usersApi.list(), sectionsApi.list(true)]);
      setUsers(u);
      setSections(s);
    } catch {
      setError('Impossible de charger les utilisateurs.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDeactivate(u: UserAdminOut) {
    const ok = await confirm({ title: 'Désactiver ce compte ?', message: `${u.full_name} ne pourra plus se connecter.`, danger: true, confirmLabel: 'Désactiver' });
    if (!ok) return;
    try {
      await usersApi.deactivate(u.id);
      showToast('Compte désactivé.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleReactivate(u: UserAdminOut) {
    try {
      await usersApi.reactivate(u.id);
      showToast('Compte réactivé.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  async function handleDelete(u: UserAdminOut) {
    const ok = await confirm({ title: 'Supprimer ce compte ?', message: `${u.full_name} sera définitivement supprimé.`, danger: true, confirmLabel: 'Supprimer' });
    if (!ok) return;
    try {
      await usersApi.remove(u.id);
      showToast('Compte supprimé.', 'success');
      load();
    } catch (err) {
      showError(err);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Utilisateurs</h1>
          <p>Comptes d'accès à l'administration et aux sections.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Nouvel utilisateur</button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && users.length === 0 && <EmptyState message="Aucun utilisateur." />}

      {!loading && !error && users.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Nom</th><th>Identifiant</th><th>E-mail</th><th>Rôle</th><th>Section</th><th>Statut</th><th>Dernière connexion</th><th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.username}</td>
                  <td>{u.email || '—'}</td>
                  <td>{u.role === 'ADMIN' ? 'Administration' : 'Section'}</td>
                  <td>{u.section_name || '—'}</td>
                  <td><span className={`badge ${u.is_active ? 'badge-published' : 'badge-refused'}`}>{u.is_active ? 'Actif' : 'Inactif'}</span></td>
                  <td>{formatDate(u.last_login_at)}</td>
                  <td>
                    <div className="section-actions">
                      <button className="btn btn-line btn-sm" onClick={() => setEditing(u)}>Modifier</button>
                      <button className="btn btn-line btn-sm" onClick={() => setResetTarget(u)}>Réinitialiser mdp</button>
                      {u.is_active ? (
                        <button className="btn btn-danger btn-sm" onClick={() => handleDeactivate(u)}>Désactiver</button>
                      ) : (
                        <button className="btn btn-primary btn-sm" onClick={() => handleReactivate(u)}>Réactiver</button>
                      )}
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(u)}>Supprimer</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && <UserFormModal sections={sections} onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />}
      {editing && <UserFormModal existing={editing} sections={sections} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />}
      {resetTarget && <ResetPasswordModal user={resetTarget} onClose={() => setResetTarget(null)} onDone={() => setResetTarget(null)} />}
    </div>
  );
}

function UserFormModal({
  existing,
  sections,
  onClose,
  onDone,
}: {
  existing?: UserAdminOut;
  sections: Section[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { showError, showToast } = useToast();
  const [username, setUsername] = useState(existing?.username || '');
  const [email, setEmail] = useState(existing?.email || '');
  const [fullName, setFullName] = useState(existing?.full_name || '');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'ADMIN' | 'SECTION'>((existing?.role as 'ADMIN' | 'SECTION') || 'SECTION');
  const [sectionId, setSectionId] = useState(existing?.section_id || '');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!existing && (!username.trim() || !fullName.trim() || !password)) {
      setFormError("L'identifiant, le nom complet et le mot de passe sont obligatoires.");
      return;
    }
    if (role === 'SECTION' && !sectionId) {
      setFormError('Veuillez choisir une section pour un compte de type Section.');
      return;
    }
    setSubmitting(true);
    try {
      if (existing) {
        await usersApi.update(existing.id, { full_name: fullName.trim(), role, section_id: role === 'SECTION' ? sectionId : null });
        showToast('Utilisateur mis à jour.', 'success');
      } else {
        await usersApi.create({
          username: username.trim().toLowerCase(),
          email: email.trim() || undefined,
          full_name: fullName.trim(),
          password,
          role,
          section_id: role === 'SECTION' ? sectionId : null,
        });
        showToast('Utilisateur créé.', 'success');
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
        <h3>{existing ? "Modifier l'utilisateur" : 'Nouvel utilisateur'}</h3>
        <form onSubmit={handleSubmit}>
          {!existing && (
            <div className="field">
              <label>Identifiant de connexion (ex. « nda », sans espace)</label>
              <input value={username} onChange={(e) => setUsername(e.target.value)} disabled={submitting} autoFocus />
            </div>
          )}
          <div className="field">
            <label>E-mail (optionnel)</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={submitting || !!existing} autoFocus={!!existing} />
          </div>
          <div className="field">
            <label>Nom complet</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} disabled={submitting} />
          </div>
          {!existing && (
            <div className="field">
              <label>Mot de passe initial (10+ car., majuscule, minuscule, chiffre)</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={submitting} />
            </div>
          )}
          <div className="field">
            <label>Rôle</label>
            <select value={role} onChange={(e) => setRole(e.target.value as 'ADMIN' | 'SECTION')} disabled={submitting}>
              <option value="SECTION">Section</option>
              <option value="ADMIN">Administration</option>
            </select>
          </div>
          {role === 'SECTION' && (
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

function ResetPasswordModal({ user, onClose, onDone }: { user: UserAdminOut; onClose: () => void; onDone: () => void }) {
  const { showError, showToast } = useToast();
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!password) {
      setFormError('Veuillez saisir un nouveau mot de passe.');
      return;
    }
    setSubmitting(true);
    try {
      await usersApi.resetPassword(user.id, password);
      showToast(`Mot de passe de ${user.full_name} réinitialisé.`, 'success');
      onDone();
    } catch (err) {
      showError(err);
      setSubmitting(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1500, padding: 16 }}>
      <div className="card" style={{ maxWidth: 420, width: '100%' }}>
        <h3>Réinitialiser le mot de passe</h3>
        <p style={{ color: 'var(--ink-soft)' }}>Pour {user.full_name} ({user.username}).</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Nouveau mot de passe (10+ car., majuscule, minuscule, chiffre)</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={submitting} autoFocus />
          </div>
          {formError && <div className="field-error" style={{ marginBottom: 10 }}>{formError}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-line" onClick={onClose} disabled={submitting}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Envoi…' : 'Réinitialiser'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
