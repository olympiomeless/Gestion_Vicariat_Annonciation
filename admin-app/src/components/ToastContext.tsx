import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

interface ToastItem {
  id: number;
  message: string;
  kind: 'info' | 'success' | 'error';
}

interface ToastContextValue {
  showToast: (message: string, kind?: ToastItem['kind']) => void;
  showError: (err: unknown) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const idRef = useRef(0);

  const showToast = useCallback((message: string, kind: ToastItem['kind'] = 'info') => {
    const id = ++idRef.current;
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => {
      setToasts((t) => t.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  const showError = useCallback(
    (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Une erreur inattendue est survenue.';
      showToast(message, 'error');
    },
    [showToast]
  );

  return (
    <ToastContext.Provider value={{ showToast, showError }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind === 'error' ? 'toast-error' : t.kind === 'success' ? 'toast-success' : ''}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast doit être utilisé à l\'intérieur de <ToastProvider>.');
  return ctx;
}
