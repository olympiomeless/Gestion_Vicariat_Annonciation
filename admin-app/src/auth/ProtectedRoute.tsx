import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import type { RoleName } from '../api/types';

export function homeForRole(role: RoleName): string {
  return role === 'ADMIN' ? '/admin' : '/section';
}

export function ProtectedRoute({ roles, children }: { roles: RoleName[]; children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-faint)' }}>
        Chargement de votre session…
      </div>
    );
  }

  if (!user) {
    // On mémorise la page visée (ex. un lien direct « Documents » envoyé
    // depuis le site vitrine) pour y renvoyer l'utilisateur juste après sa
    // connexion, au lieu de le laisser sur son tableau de bord par défaut.
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (!roles.includes(user.role)) {
    // Connecté, mais pas le bon rôle pour cet espace : renvoi vers son
    // propre espace plutôt qu'une page d'erreur — jamais un accès silencieux.
    return <Navigate to={homeForRole(user.role)} replace />;
  }

  return <>{children}</>;
}
