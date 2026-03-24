export interface EtfInfo {
  ticker: string
  name: string | null
  domicile: string | null
  gross_expense_ratio: string | null
  nav: string | null
  aum: string | null
  last_updated: string | null
}

export interface EtfListResponse {
  etfs: EtfInfo[]
  total: number
}

export interface HoldingItem {
  component_identifier: string | null
  component_name: string | null
  component_ticker: string | null
  component_weight: number | null
  component_sector: string | null
  component_shares: number | null
  component_currency: string | null
  component_sedol: string | null
}

export interface EtfDetailResponse extends EtfInfo {
  latest_composition_date: string | null
  available_dates: string[]
  holdings_count: number
  holdings: HoldingItem[]
  holdings_truncated: boolean
}

export interface CompositionResponse {
  ticker: string
  composition_date: string
  nav: number | null
  shares_outstanding: number | null
  total_net_assets: number | null
  holdings_count: number
  holdings: HoldingItem[]
  holdings_truncated: boolean
}
