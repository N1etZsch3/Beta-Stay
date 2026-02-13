import { request } from './request'

export interface DashboardSummary {
  property_count: number
  recent_pricing_count: number
  feedback_count: number
  properties: Array<{
    id: number
    name: string
    address: string
    room_type: string
    area: number
    min_price: number | null
    max_price: number | null
    latest_suggested_price: number | null
    latest_pricing_date: string | null
  }>
}

export function getDashboardSummary() {
  return request<DashboardSummary>({ url: '/dashboard/summary' })
}
