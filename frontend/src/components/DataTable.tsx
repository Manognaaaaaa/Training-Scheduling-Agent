import type { ReactNode } from 'react'

export interface Column<T> {
  key: string
  header: string
  /** Server-side sort field. Omit to make the column not sortable. */
  sortKey?: string
  render: (row: T) => ReactNode
  className?: string
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[] | undefined
  rowKey: (row: T) => number | string
  total: number
  page: number
  pageSize: number
  /** Current sort, e.g. 'name' or '-name'. */
  sort: string
  onSort: (sort: string) => void
  onPage: (page: number) => void
  loading?: boolean
  emptyText?: string
  onRowClick?: (row: T) => void
}

/** Table with server-side paging and sortable headers. The parent owns page / sort state. */
export default function DataTable<T>({
  columns, rows, rowKey, total, page, pageSize, sort, onSort, onPage, loading, emptyText = 'Nothing to show.', onRowClick,
}: Props<T>) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const sortField = sort.replace(/^-/, '')
  const descending = sort.startsWith('-')

  function clickHeader(sortKey: string) {
    onSort(sortField === sortKey && !descending ? `-${sortKey}` : sortKey)
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={`px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 ${c.className ?? ''}`}
                >
                  {c.sortKey ? (
                    <button className="inline-flex items-center gap-1 uppercase hover:text-slate-900" onClick={() => clickHeader(c.sortKey!)}>
                      {c.header}
                      <span className="text-slate-400">{sortField === c.sortKey ? (descending ? '▼' : '▲') : ''}</span>
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={`divide-y divide-slate-100 ${loading && rows ? 'opacity-60' : ''}`}>
            {rows === undefined && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-sm text-slate-500">Loading…</td>
              </tr>
            )}
            {rows?.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-sm text-slate-500">{emptyText}</td>
              </tr>
            )}
            {rows?.map((row) => (
              <tr
                key={rowKey(row)}
                className={onRowClick ? 'cursor-pointer hover:bg-slate-50' : ''}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((c) => (
                  <td key={c.key} className={`px-3 py-2 text-sm ${c.className ?? ''}`}>{c.render(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-slate-200 px-3 py-2 text-sm text-slate-600">
        <span>
          {total === 0 ? '0 results' : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`}
        </span>
        <div className="flex items-center gap-2">
          <button className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            Previous
          </button>
          <span>Page {page} / {pages}</span>
          <button className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
