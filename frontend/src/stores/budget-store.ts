/** Zustand store for budget dashboard — Epic 37 Slice 4. */

import { create } from 'zustand'
import {
  fetchBudgetSummary,
  fetchBudgetHistory,
  fetchBudgetByStage,
  fetchBudgetByModel,
  fetchBudgetConfig,
  updateBudgetConfig,
} from '../lib/api'
import type {
  BudgetSummary,
  BudgetHistory,
  BudgetByStage,
  BudgetByModel,
  BudgetConfig,
  BudgetConfigUpdate,
} from '../lib/api'

export type Period = '1d' | '7d' | '30d'

export const PERIOD_HOURS: Record<Period, number> = {
  '1d': 24,
  '7d': 168,
  '30d': 720,
}

export interface BudgetState {
  period: Period
  summary: BudgetSummary | null
  history: BudgetHistory | null
  byStage: BudgetByStage | null
  byModel: BudgetByModel | null
  config: BudgetConfig | null
  loading: boolean
  saving: boolean
  error: string | null
}

export interface BudgetActions {
  setPeriod: (period: Period) => void
  loadAll: () => Promise<void>
  loadConfig: () => Promise<void>
  saveConfig: (payload: BudgetConfigUpdate) => Promise<void>
  clearError: () => void
}

const initialState: BudgetState = {
  period: '7d',
  summary: null,
  history: null,
  byStage: null,
  byModel: null,
  config: null,
  loading: false,
  saving: false,
  error: null,
}

export const useBudgetStore = create<BudgetState & BudgetActions>((set, get) => ({
  ...initialState,

  setPeriod: (period) => {
    set({ period })
    void get().loadAll()
  },

  loadAll: async () => {
    const { period } = get()
    const hours = PERIOD_HOURS[period]
    set({ loading: true, error: null })
    try {
      const [summary, history, byStage, byModel, config] = await Promise.all([
        fetchBudgetSummary(hours),
        fetchBudgetHistory(hours),
        fetchBudgetByStage(hours),
        fetchBudgetByModel(hours),
        fetchBudgetConfig(),
      ])
      set({ summary, history, byStage, byModel, config, loading: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load budget data',
        loading: false,
      })
    }
  },

  loadConfig: async () => {
    try {
      const config = await fetchBudgetConfig()
      set({ config })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to load budget config' })
    }
  },

  saveConfig: async (payload) => {
    set({ saving: true, error: null })
    try {
      const config = await updateBudgetConfig(payload)
      set({ config, saving: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to save budget config',
        saving: false,
      })
    }
  },

  clearError: () => set({ error: null }),
}))
