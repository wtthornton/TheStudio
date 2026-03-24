/** Zustand store for trust tier configuration — Epic 37 Slice 3. */

import { create } from 'zustand'
import {
  fetchTrustRules,
  createTrustRule,
  updateTrustRule,
  deleteTrustRule,
  fetchSafetyBounds,
  updateSafetyBounds,
  fetchDefaultTier,
  updateDefaultTier,
} from '../lib/api'
import type {
  TrustTierRuleRead,
  TrustTierRuleCreate,
  TrustTierRuleUpdate,
  SafeBoundsRead,
  AssignedTier,
} from '../lib/api'

export type { TrustTierRuleRead, AssignedTier }

export interface TrustState {
  rules: TrustTierRuleRead[]
  safetyBounds: SafeBoundsRead | null
  defaultTier: AssignedTier
  loading: boolean
  saving: boolean
  error: string | null
  /** ID of rule currently being edited; null = add-new mode when form is open. */
  editingRuleId: string | null
  ruleFormOpen: boolean
}

export interface TrustActions {
  /** Load all data (rules + safety bounds + default tier) from the API. */
  load: () => Promise<void>
  /** Create a new rule. */
  addRule: (rule: TrustTierRuleCreate) => Promise<void>
  /** Update an existing rule. */
  saveRule: (ruleId: string, patch: TrustTierRuleUpdate) => Promise<void>
  /** Delete a rule by ID. */
  removeRule: (ruleId: string) => Promise<void>
  /** Toggle the active flag on a rule optimistically then sync. */
  toggleRuleActive: (ruleId: string, active: boolean) => Promise<void>
  /** Update safety bounds. */
  saveSafetyBounds: (bounds: Partial<SafeBoundsRead>) => Promise<void>
  /** Update the default tier. */
  saveDefaultTier: (tier: AssignedTier) => Promise<void>
  /** Open the rule form in edit mode. */
  openEditRule: (ruleId: string | null) => void
  /** Close the rule form. */
  closeRuleForm: () => void
  /** Clear the current error. */
  clearError: () => void
}

const initialState: TrustState = {
  rules: [],
  safetyBounds: null,
  defaultTier: 'observe',
  loading: false,
  saving: false,
  error: null,
  editingRuleId: null,
  ruleFormOpen: false,
}

export const useTrustStore = create<TrustState & TrustActions>((set) => ({
  ...initialState,

  load: async () => {
    set({ loading: true, error: null })
    try {
      const [rules, bounds, tierResult] = await Promise.all([
        fetchTrustRules(),
        fetchSafetyBounds(),
        fetchDefaultTier(),
      ])
      set({
        rules,
        safetyBounds: bounds,
        defaultTier: tierResult.default_tier,
        loading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load trust configuration',
        loading: false,
      })
    }
  },

  addRule: async (rule) => {
    set({ saving: true, error: null })
    try {
      const created = await createTrustRule(rule)
      set((s) => ({
        rules: [...s.rules, created].sort((a, b) => a.priority - b.priority),
        saving: false,
        ruleFormOpen: false,
        editingRuleId: null,
      }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to create rule', saving: false })
    }
  },

  saveRule: async (ruleId, patch) => {
    set({ saving: true, error: null })
    try {
      const updated = await updateTrustRule(ruleId, patch)
      set((s) => ({
        rules: s.rules
          .map((r) => (r.id === ruleId ? updated : r))
          .sort((a, b) => a.priority - b.priority),
        saving: false,
        ruleFormOpen: false,
        editingRuleId: null,
      }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to update rule', saving: false })
    }
  },

  removeRule: async (ruleId) => {
    set({ saving: true, error: null })
    try {
      await deleteTrustRule(ruleId)
      set((s) => ({ rules: s.rules.filter((r) => r.id !== ruleId), saving: false }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to delete rule', saving: false })
    }
  },

  toggleRuleActive: async (ruleId, active) => {
    // Optimistic update
    set((s) => ({
      rules: s.rules.map((r) => (r.id === ruleId ? { ...r, active } : r)),
    }))
    try {
      const updated = await updateTrustRule(ruleId, { active })
      set((s) => ({ rules: s.rules.map((r) => (r.id === ruleId ? updated : r)) }))
    } catch (err) {
      // Revert on failure
      set((s) => ({
        rules: s.rules.map((r) => (r.id === ruleId ? { ...r, active: !active } : r)),
        error: err instanceof Error ? err.message : 'Failed to toggle rule',
      }))
    }
  },

  saveSafetyBounds: async (bounds) => {
    set({ saving: true, error: null })
    try {
      const updated = await updateSafetyBounds({
        max_auto_merge_lines: bounds.max_auto_merge_lines,
        max_auto_merge_cost: bounds.max_auto_merge_cost,
        max_loopbacks: bounds.max_loopbacks,
        mandatory_review_patterns: bounds.mandatory_review_patterns,
      })
      set({ safetyBounds: updated, saving: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to update safety bounds',
        saving: false,
      })
    }
  },

  saveDefaultTier: async (tier) => {
    set({ saving: true, error: null })
    try {
      const result = await updateDefaultTier(tier)
      set({ defaultTier: result.default_tier, saving: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to update default tier',
        saving: false,
      })
    }
  },

  openEditRule: (ruleId) => {
    set({ editingRuleId: ruleId, ruleFormOpen: true, error: null })
  },

  closeRuleForm: () => {
    set({ ruleFormOpen: false, editingRuleId: null, error: null })
  },

  clearError: () => set({ error: null }),
}))

/** Selector: find a rule by ID. */
export function selectRule(
  state: TrustState,
  ruleId: string | null,
): TrustTierRuleRead | undefined {
  if (!ruleId) return undefined
  return state.rules.find((r) => r.id === ruleId)
}
