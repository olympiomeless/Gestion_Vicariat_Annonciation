// Client API centralisé : ajoute le jeton d'accès sur chaque requête, gère le
// rafraîchissement automatique via le cookie httpOnly de refresh token (voir
// backend/app/api/v1/auth.py), et normalise les erreurs pour l'affichage.

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';

let accessToken: string | null = null;
let onAuthLost: (() => void) | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (token) {
    sessionStorage.setItem('vicariat_access_token', token);
  } else {
    sessionStorage.removeItem('vicariat_access_token');
  }
}

export function getAccessToken(): string | null {
  if (accessToken) return accessToken;
  const stored = sessionStorage.getItem('vicariat_access_token');
  if (stored) accessToken = stored;
  return accessToken;
}

// Appelé une fois par AuthProvider : permet au client API de déclencher une
// déconnexion (retour à /login) quand la session ne peut plus être maintenue.
export function registerAuthLostHandler(handler: () => void) {
  onAuthLost = handler;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(' ');
    }
    return `Erreur ${res.status}`;
  } catch {
    return `Erreur ${res.status}`;
  }
}

export async function attemptTokenRefresh(): Promise<boolean> {
  return tryRefresh();
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });
        if (!res.ok) return false;
        const data = await res.json();
        setAccessToken(data.access_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

interface RequestOptions extends RequestInit {
  skipAuthRetry?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (res.status === 401 && !options.skipAuthRetry && path !== '/auth/refresh') {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request<T>(path, { ...options, skipAuthRetry: true });
    }
    setAccessToken(null);
    if (onAuthLost) onAuthLost();
    throw new ApiError(401, 'Session expirée. Veuillez vous reconnecter.');
  }

  if (!res.ok) {
    const message = await extractErrorMessage(res);
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return (await res.json()) as T;
  }
  return undefined as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  postForm: <T>(path: string, formData: FormData) => request<T>(path, { method: 'POST', body: formData }),
  putForm: <T>(path: string, formData: FormData) => request<T>(path, { method: 'PUT', body: formData }),
};

// Upload avec suivi de progression réel (XMLHttpRequest, seul moyen
// d'observer la progression d'un envoi depuis le navigateur — fetch ne le
// permet pas encore de façon standard).
export function uploadWithProgress<T>(
  path: string,
  method: 'POST' | 'PUT',
  formData: FormData,
  onProgress: (percent: number) => void
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, `${API_BASE_URL}${path}`);
    xhr.withCredentials = true;
    const token = getAccessToken();
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status === 401) {
        const refreshed = await tryRefresh();
        if (refreshed) {
          try {
            const result = await uploadWithProgress<T>(path, method, formData, onProgress);
            resolve(result);
          } catch (err) {
            reject(err);
          }
          return;
        }
        setAccessToken(null);
        if (onAuthLost) onAuthLost();
        reject(new ApiError(401, 'Session expirée. Veuillez vous reconnecter.'));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(xhr.responseText ? JSON.parse(xhr.responseText) : (undefined as T));
        } catch {
          resolve(undefined as T);
        }
      } else {
        let message = `Erreur ${xhr.status}`;
        try {
          const body = JSON.parse(xhr.responseText);
          if (typeof body.detail === 'string') message = body.detail;
        } catch {
          /* ignore */
        }
        reject(new ApiError(xhr.status, message));
      }
    };

    xhr.onerror = () => reject(new ApiError(0, 'Erreur réseau — impossible de joindre le serveur.'));
    xhr.send(formData);
  });
}

export function fileDownloadUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

// Les endpoints de téléchargement/affichage de fichiers exigent une session
// authentifiée : un simple <a href> ne suffit pas (pas d'en-tête
// Authorization). On récupère le fichier en mémoire puis on déclenche
// l'enregistrement via une URL d'objet temporaire.
export async function downloadFile(path: string, suggestedFilename: string): Promise<void> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    credentials: 'include',
  });
  if (!res.ok) {
    throw new ApiError(res.status, await extractErrorMessage(res));
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = suggestedFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// Pour prévisualiser une image protégée (galerie) dans une balise <img> :
// on récupère le blob et on retourne une URL d'objet à passer en `src`.
// L'appelant doit révoquer l'URL (URL.revokeObjectURL) quand elle n'est plus utile.
export async function fetchAsObjectUrl(path: string): Promise<string> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    credentials: 'include',
  });
  if (!res.ok) {
    throw new ApiError(res.status, await extractErrorMessage(res));
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export { API_BASE_URL };
