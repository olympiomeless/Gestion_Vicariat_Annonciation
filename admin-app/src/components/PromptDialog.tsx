import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

interface PromptOptions {
  title: string;
  message?: ReactNode;
  label?: string;
  confirmLabel?: string;
  placeholder?: string;
}

interface PendingPrompt extends PromptOptions {
  resolve: (value: string | null) => void;
}

interface PromptContextValue {
  prompt: (options: PromptOptions) => Promise<string | null>;
}

const PromptContext = createContext<PromptContextValue | undefined>(undefined);

// Utilisé pour toute action qui exige une justification texte de la part de
// l'administrateur (motif de refus d'un document / d'une actualité / d'une
// activité / d'une photo) — jamais un window.prompt().
export function PromptProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<PendingPrompt | null>(null);
  const [value, setValue] = useState('');

  const prompt = useCallback(
    (options: PromptOptions) =>
      new Promise<string | null>((resolve) => {
        setValue('');
        setPending({ ...options, resolve });
      }),
    []
  );

  function submit() {
    if (!pending) return;
    const trimmed = value.trim();
    if (!trimmed) return;
    pending.resolve(trimmed);
    setPending(null);
  }

  function cancel() {
    if (!pending) return;
    pending.resolve(null);
    setPending(null);
  }

  return (
    <PromptContext.Provider value={{ prompt }}>
      {children}
      {pending && (
        <div
          role="dialog"
          aria-modal="true"
          style={{ position: 'fixed', inset: 0, background: 'rgba(10,56,73,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}
        >
          <div className="card" style={{ maxWidth: 440, width: '90%' }}>
            <h3>{pending.title}</h3>
            {pending.message && <p style={{ color: 'var(--ink-soft)' }}>{pending.message}</p>}
            <div className="field" style={{ marginTop: 10 }}>
              {pending.label && <label>{pending.label}</label>}
              <textarea
                rows={3}
                autoFocus
                value={value}
                placeholder={pending.placeholder}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') cancel();
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
              <button className="btn btn-line" onClick={cancel}>
                Annuler
              </button>
              <button className="btn btn-danger" onClick={submit} disabled={!value.trim()}>
                {pending.confirmLabel || 'Valider'}
              </button>
            </div>
          </div>
        </div>
      )}
    </PromptContext.Provider>
  );
}

export function usePrompt(): (options: PromptOptions) => Promise<string | null> {
  const ctx = useContext(PromptContext);
  if (!ctx) throw new Error("usePrompt doit être utilisé à l'intérieur de <PromptProvider>.");
  return ctx.prompt;
}
