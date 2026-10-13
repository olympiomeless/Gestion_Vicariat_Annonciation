type Status = 'EN_ATTENTE' | 'PUBLIE' | 'REFUSE' | 'BROUILLON' | 'SOUMIS';

const LABELS: Record<Status, string> = {
  EN_ATTENTE: 'En attente',
  SOUMIS: 'Soumis',
  PUBLIE: 'Publié',
  REFUSE: 'Refusé',
  BROUILLON: 'Brouillon',
};

const CLASSES: Record<Status, string> = {
  EN_ATTENTE: 'badge-pending',
  SOUMIS: 'badge-pending',
  PUBLIE: 'badge-published',
  REFUSE: 'badge-refused',
  BROUILLON: 'badge-draft',
};

export function StatusBadge({ status }: { status: string }) {
  const key = (status as Status) in LABELS ? (status as Status) : undefined;
  if (!key) return <span className="badge badge-draft">{status}</span>;
  return <span className={`badge ${CLASSES[key]}`}>{LABELS[key]}</span>;
}
