interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 14, fontSize: '.88rem', color: 'var(--ink-soft)' }}>
      <span>
        Page {page} sur {totalPages} — {total} résultat{total > 1 ? 's' : ''}
      </span>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-line btn-sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Précédent
        </button>
        <button className="btn btn-line btn-sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Suivant
        </button>
      </div>
    </div>
  );
}
