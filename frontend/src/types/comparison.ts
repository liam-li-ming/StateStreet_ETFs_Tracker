export interface AddedComponent {
  component_identifier: string | null
  component_name: string | null
  component_ticker: string | null
  weight_new: number | null
  shares_new: number | null
  component_sector: string | null
  component_currency: string | null
}

export interface RemovedComponent {
  component_identifier: string | null
  component_name: string | null
  component_ticker: string | null
  weight_old: number | null
  shares_old: number | null
  component_sector: string | null
  component_currency: string | null
}

export interface WeightChange {
  component_identifier: string | null
  component_name: string | null
  component_ticker: string | null
  weight_old: number | null
  weight_new: number | null
  weight_delta: number | null
  component_sector: string | null
  shares_old: number | null
  shares_new: number | null
  shares_delta: number | null
}

export interface CompareResponse {
  ticker: string
  date1: string
  date2: string
  summary: {
    added_count: number
    removed_count: number
    weight_changes_count: number
  }
  added: AddedComponent[]
  removed: RemovedComponent[]
  weight_changes: WeightChange[]
}

export interface ChangeEvent {
  date_from: string
  date_to: string
  change_type: string
  component_identifier: string | null
  component_name: string | null
  component_ticker: string | null
  component_sector: string | null
  weight_old: number | null
  weight_new: number | null
  weight_delta: number | null
}

export interface ChangesResponse {
  ticker: string
  changes: ChangeEvent[]
}
