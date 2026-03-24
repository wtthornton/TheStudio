/**
 * Tour Registry — Epic 47.2
 *
 * Central registry of all product tours.  Each entry declares the tour's
 * identifier, human-readable label, and the localStorage key used to persist
 * completion state.  Step arrays are injected at runtime by each tour module
 * (47.3 – 47.7) so this file stays import-cycle free.
 *
 * Adding a new tour
 * -----------------
 *   1. Add an entry to TOUR_REGISTRY below.
 *   2. Create your step array in the appropriate component file.
 *   3. Call `useTourState(tourId).start(steps)` from a TourBeacon or menu item.
 *
 * Pipeline tour steps added by Epic 47.3.
 * Triage tour steps added by Epic 47.5.
 * Analytics tour steps added by Epic 47.6.
 * Repo-Trust steps will be added by Epic 47.7.
 */

import type { Step } from 'react-joyride'

// ── Types ─────────────────────────────────────────────────────────────────────

/** Unique identifier for each registered tour. */
export type TourId = 'pipeline' | 'triage' | 'analytics' | 'repo-trust'

/** Static metadata for a single tour. */
export interface TourMeta {
  /** Stable string key used in localStorage and analytics. */
  id: TourId
  /** Human-readable name shown in HelpMenu and tour beacons. */
  label: string
  /** Short description shown in the Guided Tours section. */
  description: string
  /** localStorage key that stores whether the tour has been completed. */
  storageKey: string
}

// ── Registry ──────────────────────────────────────────────────────────────────

/**
 * Ordered list of all tours.  The order controls the display order in HelpMenu.
 * Epics 47.3 – 47.7 will populate step definitions; registration here is
 * intentionally step-free.
 */
export const TOUR_REGISTRY: readonly TourMeta[] = [
  {
    id: 'pipeline',
    label: 'Pipeline Overview',
    description: 'Walk through the 9-stage pipeline rail, stage nodes, gates, and activity stream.',
    storageKey: 'studio:tour:pipeline:completed',
  },
  {
    id: 'triage',
    label: 'Triage Queue',
    description: 'Learn how to review incoming issues, accept or reject them, and inspect intent.',
    storageKey: 'studio:tour:triage:completed',
  },
  {
    id: 'analytics',
    label: 'Analytics & Reputation',
    description: 'Explore KPIs, throughput charts, bottleneck detection, and expert reputation.',
    storageKey: 'studio:tour:analytics:completed',
  },
  {
    id: 'repo-trust',
    label: 'Repo & Trust Tiers',
    description: 'Configure repositories, trust tiers, and budget controls.',
    storageKey: 'studio:tour:repo-trust:completed',
  },
] as const

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Look up a tour by id.  Returns undefined if not found. */
export function getTourMeta(id: TourId): TourMeta | undefined {
  return TOUR_REGISTRY.find((t) => t.id === id)
}

/** Returns true if the given localStorage key indicates tour completion. */
export function isTourCompleted(storageKey: string): boolean {
  try {
    return localStorage.getItem(storageKey) === 'true'
  } catch {
    // localStorage may be unavailable in SSR or restricted environments
    return false
  }
}

/** Marks a tour as completed in localStorage. */
export function markTourCompleted(storageKey: string): void {
  try {
    localStorage.setItem(storageKey, 'true')
  } catch {
    // silently ignore quota or security errors
  }
}

/** Clears the completion flag so the tour can be replayed. */
export function resetTourCompletion(storageKey: string): void {
  try {
    localStorage.removeItem(storageKey)
  } catch {
    // silently ignore
  }
}

/** Resets ALL tour completion flags.  Used by "Restart all tours" menu item. */
export function resetAllTours(): void {
  for (const tour of TOUR_REGISTRY) {
    resetTourCompletion(tour.storageKey)
  }
}

// ── Repo & Trust Tour Steps (Epic 47.7) ───────────────────────────────────────

/**
 * Five-step guided tour of the Repos & Trust tabs.
 *
 * Targets use `data-tour` attributes added to:
 *   RepoSettings.tsx        → data-tour="repo-selector"  (fleet health table)
 *   RepoSettings.tsx        → data-tour="repo-config"    (per-repo config form)
 *   TrustConfiguration.tsx  → data-tour="trust-tier"     (default tier selector)
 *   TrustConfiguration.tsx  → data-tour="trust-rules"    (rule list header)
 *   BudgetDashboard.tsx     → data-tour="budget-dashboard" (budget header row)
 */
export const REPO_TRUST_TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="repo-selector"]',
    title: 'Fleet Health Table',
    content:
      'This table shows every repository connected to TheStudio. The health dot indicates current activity: green = active with recent tasks, yellow = idle, red = degraded or paused. Click any row to open its configuration panel below.',
    disableBeacon: true,
    placement: 'bottom',
  },
  {
    target: '[data-tour="repo-config"]',
    title: 'Repository Configuration',
    content:
      'After selecting a repo from the table, its full configuration loads here. You can update the default trust tier for that repository, adjust webhook settings, or change its active status. Changes take effect immediately.',
    placement: 'top',
  },
  {
    target: '[data-tour="trust-tier"]',
    title: 'Default Trust Tier',
    content:
      'The default trust tier is the fallback applied to every task when no rule matches. Observe = read-only reporting, Suggest = agent proposes changes that need human approval, Execute = agent applies changes automatically. Start conservative and raise the tier as confidence grows.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="trust-rules"]',
    title: 'Trust Tier Rules',
    content:
      'Rules override the default tier based on task properties — complexity index, risk flags, repository name, or file count. Rules are evaluated in ascending priority order and the first match wins. Use rules to automatically tighten trust for high-risk work.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="budget-dashboard"]',
    title: 'Budget Controls',
    content:
      'Track LLM API spend across the pipeline in real time. Set a weekly budget cap, per-task cost warning, and auto-pause threshold. The period selector lets you compare spend over 1, 7, or 30 days. Keeping an eye on costs here prevents surprise invoices.',
    placement: 'bottom',
  },
]

// ── Analytics Tour Steps (Epic 47.6) ──────────────────────────────────────────

/**
 * Five-step guided tour of the Analytics tab.
 *
 * Targets use `data-tour` attributes added to:
 *   Analytics.tsx        → data-tour="analytics-period" (header row)
 *   Analytics.tsx        → data-tour="analytics-kpis"   (SummaryCards wrapper)
 *   Analytics.tsx        → data-tour="analytics-throughput" (ThroughputChart wrapper)
 *   Analytics.tsx        → data-tour="analytics-bottleneck" (BottleneckBars wrapper)
 *   Analytics.tsx        → data-tour="analytics-expert-table" (ExpertTable wrapper)
 */
export const ANALYTICS_TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="analytics-period"]',
    title: 'Period Selector',
    content:
      'Choose the time window for all analytics data: last 7, 30, or 90 days. Every chart and KPI on this page updates instantly when you switch periods.',
    disableBeacon: true,
    placement: 'bottom',
  },
  {
    target: '[data-tour="analytics-kpis"]',
    title: 'Key Performance Indicators',
    content:
      'Four headline metrics at a glance: Tasks Completed, Average Pipeline Time (intake to draft PR), PR Merge Rate, and Total Spend. Use these to track pipeline health over time.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="analytics-throughput"]',
    title: 'Throughput Chart',
    content:
      'A daily bar chart of completed tasks. Spikes show busy days; flat lines reveal blocked periods. Hover a bar to see the exact count and compare against your moving average.',
    placement: 'top',
  },
  {
    target: '[data-tour="analytics-bottleneck"]',
    title: 'Bottleneck Analysis',
    content:
      'Horizontal bars show average time spent in each pipeline stage. The longest bar is your current bottleneck. The variance indicator flags stages with unpredictable durations worth investigating.',
    placement: 'top',
  },
  {
    target: '[data-tour="analytics-expert-table"]',
    title: 'Expert Reputation Table',
    content:
      'Every expert agent\'s performance at a glance: trust tier, average weight in the assembler, total samples, confidence, and drift trend. Click any row for a detailed expert profile and historical weight chart.',
    placement: 'top',
  },
]

// ── Triage Tour Steps (Epic 47.5) ─────────────────────────────────────────────

/**
 * Five-step guided tour of the Triage tab.
 *
 * Targets use `data-tour` attributes added to:
 *   TriageQueue.tsx  → data-tour="triage-queue", data-tour="triage-list"
 *   TriageCard.tsx   → data-tour="triage-card", data-tour="triage-actions"
 *   IntentEditor.tsx → data-tour="intent-editor"
 *   RoutingPreview.tsx → data-tour="routing-preview"
 */
export const TRIAGE_TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="triage-queue"]',
    title: 'Triage Queue',
    content:
      'This is your triage queue — all GitHub issues that have been received by the webhook and are waiting for your review before entering the pipeline. Only issues you accept will be processed.',
    disableBeacon: true,
    placement: 'bottom',
  },
  {
    target: '[data-tour="triage-card"]',
    title: 'Issue Card',
    content:
      'Each card represents one incoming issue. It shows the issue title, a short description, and enrichment signals like complexity estimate, file count, and cost range computed by the Context stage.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="triage-actions"]',
    title: 'Accept or Reject',
    content:
      '"Accept & Plan" sends the issue into the full pipeline. "Edit" lets you adjust the title or body before accepting. "Reject" closes the issue with a reason (duplicate, out of scope, needs info, or won\'t fix).',
    placement: 'top',
  },
  {
    target: '[data-tour="intent-editor"]',
    title: 'Intent Editor',
    content:
      'Once an issue passes the Intent Builder stage, its Intent Specification appears here. Review, approve, edit, or request AI refinement before the Router assigns expert agents.',
    placement: 'left',
  },
  {
    target: '[data-tour="routing-preview"]',
    title: 'Routing Preview',
    content:
      'After intent is approved, the Router stage selects the best expert agents for the task. Review their selection rationale here, add or remove experts, then approve routing to continue.',
    placement: 'left',
  },
]

// ── Pipeline Tour Steps (Epic 47.3) ───────────────────────────────────────────

/**
 * Six-step guided tour of the pipeline tab.
 *
 * Targets use `data-tour` attributes added to:
 *   PipelineStatus.tsx  → data-tour="pipeline-rail"
 *   StageNode.tsx       → data-tour="stage-node", data-tour="active-pulse"
 *   GateInspector.tsx   → data-tour="gate-inspector"
 *   ActivityStream.tsx  → data-tour="activity-stream"
 *   Minimap.tsx         → data-tour="minimap"
 */
export const PIPELINE_TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="pipeline-rail"]',
    title: 'The Pipeline Rail',
    content:
      'This 9-stage rail shows the full journey of every GitHub issue — from Intake all the way to a draft PR on GitHub. Each stage runs automatically in sequence.',
    disableBeacon: true,
    placement: 'bottom',
  },
  {
    target: '[data-tour="stage-node"]',
    title: 'Stage Nodes',
    content:
      'Each circle represents one pipeline stage. The ring color indicates health: indigo = active, green = passed, red = failed, gray = idle. The badge shows how many tasks are queued.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="active-pulse"]',
    title: 'Active Pulse',
    content:
      'A pulsing stage has tasks currently in progress. Hover any node to see its average duration, pass rate, and the IDs of tasks currently running through it.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="gate-inspector"]',
    title: 'Gate Inspector',
    content:
      'Every stage transition records pass/fail evidence here. Use the filters to find failures, click a row to inspect individual checks, and trace loopbacks back to their root cause.',
    placement: 'top',
  },
  {
    target: '[data-tour="activity-stream"]',
    title: 'Activity Stream',
    content:
      'Watch the agent work in real time — file reads, edits, test runs, and LLM calls appear as they happen. Filter by type or search for specific content to zero in on what matters.',
    placement: 'top',
  },
  {
    target: '[data-tour="minimap"]',
    title: 'Task Minimap',
    content:
      'The minimap tracks every active TaskPacket across all stages. Click a card to jump to that task, or drag to scroll when many tasks are in flight at once.',
    placement: 'top',
  },
]
