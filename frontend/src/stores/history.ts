import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as pricingApi from '../api/pricing'
import * as feedbackApi from '../api/feedback'
import type { PricingRecord } from '../api/pricing'
import type { Feedback } from '../api/feedback'

export const useHistoryStore = defineStore('history', () => {
  const pricingRecords = ref<PricingRecord[]>([])
  const feedbacks = ref<Feedback[]>([])
  const loading = ref(false)

  async function fetchByProperty(propertyId: number) {
    loading.value = true
    try {
      const [records, fbs] = await Promise.all([
        pricingApi.listPricingRecords(propertyId),
        feedbackApi.listFeedbackByProperty(propertyId),
      ])
      pricingRecords.value = records
      feedbacks.value = fbs
    } finally {
      loading.value = false
    }
  }

  return { pricingRecords, feedbacks, loading, fetchByProperty }
})
