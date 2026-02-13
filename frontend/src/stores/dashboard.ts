import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as dashboardApi from '../api/dashboard'
import type { DashboardSummary } from '../api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const summary = ref<DashboardSummary | null>(null)
  const loading = ref(false)

  async function fetchSummary() {
    loading.value = true
    try {
      summary.value = await dashboardApi.getDashboardSummary()
    } finally {
      loading.value = false
    }
  }

  return { summary, loading, fetchSummary }
})
