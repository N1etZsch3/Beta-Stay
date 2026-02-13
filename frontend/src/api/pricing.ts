import { request } from './request'

export interface PricingRecord {
  id: number
  property_id: number
  target_date: string
  conservative_price: number
  suggested_price: number
  aggressive_price: number
  calculation_details?: Record<string, any>
  created_at: string
}

export function calculatePricing(data: { property_id: number; target_date: string; base_price?: number }) {
  return request<PricingRecord>({ url: '/pricing/calculate', method: 'POST', data })
}

export function listPricingRecords(propertyId: number) {
  return request<PricingRecord[]>({ url: `/pricing/records/${propertyId}` })
}
