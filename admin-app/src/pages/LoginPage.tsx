import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../api/client';
import { homeForRole } from '../auth/ProtectedRoute';

export default function LoginPage() {
  const { user, isLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isLoading && user) {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate to={from || homeForRole(user.role)} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError('Veuillez renseigner votre identifiant et votre mot de passe.');
      return;
    }
    setSubmitting(true);
    try {
      const loggedInUser = await login(username.trim(), password);
      navigate(homeForRole(loggedInUser.role), { replace: true });
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 400)) {
        setError('Identifiant ou mot de passe incorrect.');
      } else if (err instanceof ApiError && err.status === 429) {
        setError('Trop de tentatives. Veuillez réessayer dans quelques minutes.');
      } else {
        setError('Connexion impossible pour le moment. Veuillez réessayer.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(160deg, var(--primary) 0%, var(--primary-strong) 100%)',
        padding: 20,
      }}
    >
      <div className="card" style={{ maxWidth: 420, width: '100%', background: '#fff' }}>
        <div style={{ textAlign: 'center', marginBottom: 22 }}>
          <div style={{ fontFamily: 'Fraunces, serif', fontSize: '1.4rem', color: 'var(--primary)', fontWeight: 700 }}>
            Vicariat de l'Annonciation
          </div>
          <p style={{ color: 'var(--ink-faint)', marginTop: 4 }}>Cœurs Vaillants — Âmes Vaillantes</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="username">Identifiant</label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={submitting}
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">Mot de passe</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
            />
          </div>

          {error && (
            <div className="card" style={{ borderColor: 'var(--brick)', background: 'var(--brick-soft)', color: 'var(--brick)', padding: '10px 14px', marginBottom: 14 }}>
              {error}
            </div>
          )}

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
            {submitting ? 'Connexion…' : 'Se connecter'}
          </button>
        </form>
      </div>
    </div>
  );
}
