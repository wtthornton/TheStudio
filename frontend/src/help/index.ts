/**
 * Help content index — static ?raw imports for all 11 tab help articles.
 *
 * Vite resolves ?raw imports at build time; they must be static string literals.
 * Add a new entry here whenever a new tab is created.
 *
 * Epic 45.4: initial stubs — full content authored in Epic 45.6.
 */

import pipelineMd from './pipeline.md?raw'
import triageMd from './triage.md?raw'
import intentMd from './intent.md?raw'
import routingMd from './routing.md?raw'
import boardMd from './board.md?raw'
import trustMd from './trust.md?raw'
import budgetMd from './budget.md?raw'
import activityMd from './activity.md?raw'
import analyticsMd from './analytics.md?raw'
import reputationMd from './reputation.md?raw'
import reposMd from './repos.md?raw'
// Epic 45.7: cross-cutting concept articles (searchable, not tab-specific)
import conceptTrustTiersMd from './concept-trust-tiers.md?raw'
import conceptWebhooksMd from './concept-webhooks.md?raw'
import conceptEvidenceBundlesMd from './concept-evidence-bundles.md?raw'
import conceptPipelineStagesMd from './concept-pipeline-stages.md?raw'

/**
 * Maps App tab keys to their markdown help content string.
 * The 'api' tab is intentionally omitted — it renders its own Scalar docs.
 * Cross-cutting concept articles (prefixed 'concept-') are indexed for search
 * but are not directly associated with any tab.
 */
export const HELP_CONTENT: Record<string, string> = {
  pipeline: pipelineMd,
  triage: triageMd,
  intent: intentMd,
  routing: routingMd,
  board: boardMd,
  trust: trustMd,
  budget: budgetMd,
  activity: activityMd,
  analytics: analyticsMd,
  reputation: reputationMd,
  repos: reposMd,
  // Cross-cutting concept articles (Epic 45.7)
  'concept-trust-tiers': conceptTrustTiersMd,
  'concept-webhooks': conceptWebhooksMd,
  'concept-evidence-bundles': conceptEvidenceBundlesMd,
  'concept-pipeline-stages': conceptPipelineStagesMd,
}

/** Titles for each tab's help panel header. */
export const HELP_TITLES: Record<string, string> = {
  pipeline: 'Pipeline Dashboard',
  triage: 'Triage Queue',
  intent: 'Intent Review',
  routing: 'Routing Review',
  board: 'Backlog Board',
  trust: 'Trust Tiers',
  budget: 'Budget Dashboard',
  activity: 'Activity Log',
  analytics: 'Analytics',
  reputation: 'Reputation & Outcomes',
  repos: 'Repository Settings',
  // Cross-cutting concept articles (Epic 45.7)
  'concept-trust-tiers': 'Concept: Trust Tiers',
  'concept-webhooks': 'Concept: Webhooks',
  'concept-evidence-bundles': 'Concept: Evidence Bundles',
  'concept-pipeline-stages': 'Concept: Pipeline Stages',
}
