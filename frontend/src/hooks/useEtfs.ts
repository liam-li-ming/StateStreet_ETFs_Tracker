import { useQuery } from '@tanstack/react-query'
import apiClient from '../api/client'
import type { EtfListResponse, EtfDetailResponse } from '../types/etf'

export function useEtfs(q = '') {
  return useQuery<EtfListResponse>({
    queryKey: ['etfs', q],
    queryFn: () => apiClient.get('/api/etfs', { params: q ? { q } : {} }).then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

export function useEtfDetail(ticker: string, limit = 50) {
  return useQuery<EtfDetailResponse>({
    queryKey: ['etf', ticker, limit],
    queryFn: () => apiClient.get(`/api/etfs/${ticker}`, { params: { limit } }).then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: !!ticker,
  })
}
