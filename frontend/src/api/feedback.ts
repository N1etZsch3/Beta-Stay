import { request } from './request'

export interface Feedback {
  id: number
  pricing_record_id: number
  feedback_type: string
  actual_price: number | null
  note: string | null
  created_at: string
}

export function createFeedback(data: { pricing_record_id: number; feedback_type: string; actual_price?: number; note?: string }) {
  return request<Feedback>({ url: '/feedback', method: 'POST', data })
}

export function listFeedbackByProperty(propertyId: number) {
  return request<Feedback[]>({ url: `/feedback/by-property/${propertyId}` })
}
