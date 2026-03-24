import { useQuery } from '@tanstack/react-query'
import apiClient from '../api/client'
import type { CompositionResponse } from '../types/etf'
import type { CompareResponse, ChangesResponse } from '../types/comparison'

export function useComposition(ticker: string, date: string, limit = 100) {
  return useQuery<CompositionResponse>({
    queryKey: ['composition', ticker, date, limit],
    queryFn: () =>
      apiClient
        .get(`/api/etfs/${ticker}/compositions/${date}`, { params: { limit } })
        .then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: !!ticker && !!date,
  })
}

export function useCompare(ticker: string, date1: string, date2: string) {
  return useQuery<CompareResponse>({
    queryKey: ['compare', ticker, date1, date2],
    queryFn: () =>
      apiClient
        .get(`/api/etfs/${ticker}/compare`, { params: { date1, date2 } })
        .then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: !!ticker && !!date1 && !!date2 && date1 !== date2,
  })
}

export function useEtfChanges(ticker: string) {
  return useQuery<ChangesResponse>({
    queryKey: ['changes', ticker],
    queryFn: () => apiClient.get(`/api/etfs/${ticker}/changes`).then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: !!ticker,
  })
}
