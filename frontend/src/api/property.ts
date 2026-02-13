import { request } from './request'

export interface Property {
  id: number
  name: string
  address: string
  room_type: string
  area: number
  facilities: Record<string, any>
  description: string | null
  min_price: number | null
  max_price: number | null
  expected_return_rate: number | null
  vacancy_tolerance: number | null
}

export function listProperties() {
  return request<Property[]>({ url: '/property' })
}

export function getProperty(id: number) {
  return request<Property>({ url: `/property/${id}` })
}

export function createProperty(data: Partial<Property>) {
  return request<Property>({ url: '/property', method: 'POST', data })
}

export function updateProperty(id: number, data: Partial<Property>) {
  return request<Property>({ url: `/property/${id}`, method: 'PUT', data })
}

export function deleteProperty(id: number) {
  return request({ url: `/property/${id}`, method: 'DELETE' })
}
