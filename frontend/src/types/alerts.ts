export interface AlertItem {
  etf_ticker: string
  date_from: string
  date_to: string
  change_type: string
  component_identifier: string | null
  component_ticker: string | null
  component_name: string | null
  component_sector: string | null
  weight_old: number | null
  weight_new: number | null
  weight_delta: number | null
  shares_old: number | null
  shares_new: number | null
  detected_at: string | null
}

export interface AlertsResponse {
  alerts: AlertItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SearchResultItem {
  etf_ticker: string
  etf_name: string | null
  composition_date: string
  component_name: string | null
  component_identifier: string | null
  component_weight: number | null
  component_sector: string | null
  component_shares: number | null
}

export interface SearchResponse {
  component_ticker: string
  found_in: SearchResultItem[]
  total_etfs: number
}
