import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as propertyApi from '../api/property'
import type { Property } from '../api/property'

export const usePropertyStore = defineStore('property', () => {
  const properties = ref<Property[]>([])
  const currentProperty = ref<Property | null>(null)
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      properties.value = await propertyApi.listProperties()
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: number) {
    loading.value = true
    try {
      currentProperty.value = await propertyApi.getProperty(id)
    } finally {
      loading.value = false
    }
  }

  async function create(data: Partial<Property>) {
    const prop = await propertyApi.createProperty(data)
    properties.value.unshift(prop)
    return prop
  }

  async function update(id: number, data: Partial<Property>) {
    const prop = await propertyApi.updateProperty(id, data)
    const idx = properties.value.findIndex(p => p.id === id)
    if (idx !== -1) properties.value[idx] = prop
    if (currentProperty.value?.id === id) currentProperty.value = prop
    return prop
  }

  async function remove(id: number) {
    await propertyApi.deleteProperty(id)
    properties.value = properties.value.filter(p => p.id !== id)
    if (currentProperty.value?.id === id) currentProperty.value = null
  }

  return { properties, currentProperty, loading, fetchList, fetchOne, create, update, remove }
})
