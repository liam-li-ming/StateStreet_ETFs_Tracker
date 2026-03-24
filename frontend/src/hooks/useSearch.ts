import { useQuery } from '@tanstack/react-query'
import apiClient from '../api/client'
import type { SearchResponse } from '../types/alerts'

export function useSearch(component: string) {
  return useQuery<SearchResponse>({
    queryKey: ['search', component],
    queryFn: () =>
      apiClient.get('/api/search', { params: { component } }).then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: component.trim().length >= 1,
  })
}
