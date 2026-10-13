export function LoadingState({ label = 'Chargement…' }: { label?: string }) {
  return <p style={{ color: 'var(--ink-faint)', padding: '24px 0' }}>{label}</p>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="card" style={{ borderColor: 'var(--brick)', background: 'var(--brick-soft)', color: 'var(--brick)' }}>
      {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <p style={{ color: 'var(--ink-faint)', padding: '24px 0' }}>{message}</p>;
}
