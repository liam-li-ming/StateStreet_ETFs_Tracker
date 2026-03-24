interface Props {
  page: number
  totalPages: number
  onPage: (p: number) => void
}

export function Pagination({ page, totalPages, onPage }: Props) {
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center gap-2 justify-center pt-4">
      <button
        onClick={() => onPage(page - 1)}
        disabled={page === 1}
        className="rounded border px-3 py-1 text-sm disabled:opacity-40 hover:bg-gray-100"
      >
        ← Prev
      </button>
      <span className="text-sm text-gray-600">
        Page {page} of {totalPages}
      </span>
      <button
        onClick={() => onPage(page + 1)}
        disabled={page === totalPages}
        className="rounded border px-3 py-1 text-sm disabled:opacity-40 hover:bg-gray-100"
      >
        Next →
      </button>
    </div>
  )
}
