import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

interface ConfirmOptions {
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
}

interface PendingConfirm extends ConfirmOptions {
  resolve: (value: boolean) => void;
}

interface ConfirmContextValue {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextValue | undefined>(undefined);

// Fournit une confirmation modale cohérente pour toute action destructive
// (suppression, désactivation de compte, refus...) — jamais un simple
// window.confirm(), pour rester dans le style visuel de l'application et
// afficher un message précis sur ce qui va être supprimé/modifié.
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<PendingConfirm | null>(null);

  const confirm = useCallback(
    (options: ConfirmOptions) =>
      new Promise<boolean>((resolve) => {
        setPending({ ...options, resolve });
      }),
    []
  );

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {pending && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(10,56,73,.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
          }}
        >
          <div className="card" style={{ maxWidth: 420, width: '90%' }}>
            <h3>{pending.title}</h3>
            <p style={{ color: 'var(--ink-soft)' }}>{pending.message}</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 18 }}>
              <button
                className="btn btn-line"
                onClick={() => {
                  pending.resolve(false);
                  setPending(null);
                }}
              >
                Annuler
              </button>
              <button
                className={pending.danger ? 'btn btn-danger' : 'btn btn-primary'}
                onClick={() => {
                  pending.resolve(true);
                  setPending(null);
                }}
              >
                {pending.confirmLabel || 'Confirmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): (options: ConfirmOptions) => Promise<boolean> {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error('useConfirm doit être utilisé à l\'intérieur de <ConfirmProvider>.');
  return ctx.confirm;
}
