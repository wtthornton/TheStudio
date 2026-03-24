/**
 * PromptObject — Canonical TypeScript interface for prompt-driven AI actions.
 *
 * Per SG 8.2, every prompt-driven action preserves these fields in UI and payload.
 * Modes map to trust tiers: draft (Observe), suggest (Suggest), execute (Execute).
 *
 * Epic 55.1
 */

export interface PromptObject {
  /** What outcome the user wants */
  goal: string
  /** Relevant repo/task/environment context */
  context: string
  /** Non-goals, policy bounds, budget/time constraints */
  constraints: string
  /** How the user defines an acceptable result */
  success_criteria: string
  /** Trust tier mode: draft (observe), suggest, or execute */
  mode: 'draft' | 'suggest' | 'execute'
}
