import { useState } from 'react'

/** Page + sort state for a DataTable. Changing the sort goes back to page 1. */
export function useTableState(defaultSort: string, pageSize = 25) {
  const [page, setPage] = useState(1)
  const [sort, setSortRaw] = useState(defaultSort)
  const setSort = (value: string) => {
    setSortRaw(value)
    setPage(1)
  }
  return { page, setPage, sort, setSort, pageSize }
}
