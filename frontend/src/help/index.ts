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

/**
 * Maps App tab keys to their markdown help content string.
 * The 'api' tab is intentionally omitted — it renders its own Scalar docs.
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
}
