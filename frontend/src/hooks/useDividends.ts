import { useQuery } from '@tanstack/react-query'
import apiClient from '../api/client'
import type { DividendsResponse } from '../types/dividends'

export function useDividends(page = 1, pageSize = 50, etfTicker = '') {
  return useQuery<DividendsResponse>({
    queryKey: ['dividends', page, pageSize, etfTicker],
    queryFn: () =>
      apiClient
        .get('/api/dividends', {
          params: {
            page,
            page_size: pageSize,
            ...(etfTicker ? { etf_ticker: etfTicker } : {}),
          },
        })
        .then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
}
