export interface DividendItem {
  etf_ticker: string
  ex_date: string
  dividend_amount: number
  currency: string
}

export interface DividendsResponse {
  dividends: DividendItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
