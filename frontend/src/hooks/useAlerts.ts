import { useQuery } from '@tanstack/react-query'
import apiClient from '../api/client'
import type { AlertsResponse } from '../types/alerts'

export function useAlerts(page = 1, pageSize = 50, etfTicker = '', changeType = '') {
  return useQuery<AlertsResponse>({
    queryKey: ['alerts', page, pageSize, etfTicker, changeType],
    queryFn: () =>
      apiClient
        .get('/api/alerts', {
          params: {
            page,
            page_size: pageSize,
            ...(etfTicker ? { etf_ticker: etfTicker } : {}),
            ...(changeType ? { change_type: changeType } : {}),
          },
        })
        .then(r => r.data),
    staleTime: 2 * 60 * 1000,
  })
}
