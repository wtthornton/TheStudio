/** Dashboard API client utilities. */

const API_BASE = '/api/v1/dashboard'

function getToken(): string {
  return new URLSearchParams(window.location.search).get('token') ?? ''
}

function withToken(url: string): string {
  const token = getToken()
  return token ? `${url}${url.includes('?') ? '&' : '?'}token=${token}` : url
}

// --- Types ---

export interface TaskPacketRead {
  id: string
  repo: string
  issue_id: number
  status: string
  created_at: string
  updated_at: string
  stage_timings?: Record<string, { start?: string; end?: string; cost?: number; model?: string }>
  issue_title?: string | null
  issue_body?: string | null
  scope?: Record<string, unknown> | null
  risk_flags?: Record<string, boolean> | null
  complexity_index?: Record<string, unknown> | null
  pr_number?: number | null
  pr_url?: string | null
}

export interface TaskPacketDetail extends TaskPacketRead {
  cost_by_stage: { stage: string; cost: number; model: string | null }[]
  total_cost: number
}

export interface StageMetric {
  stage: string
  pass_rate: number | null
  avg_duration_seconds: number | null
  throughput: number
}

export interface StageMetricsResponse {
  window_hours: number
  stages: StageMetric[]
}

export interface GateEvidenceRead {
  id: string
  task_id: string
  stage: string
  result: string
  checks: Record<string, unknown>[] | null
  defect_category: string | null
  evidence_artifact: Record<string, unknown> | null
  created_at: string
}

export interface GateMetrics {
  window_hours: number
  total_gates: number
  pass_rate: number | null
  avg_issues: number | null
  top_failure_type: string | null
  loopback_rate: number | null
}

export interface ActivityEntry {
  id: string
  task_id: string
  stage: string
  activity_type: string
  subphase: string
  content: string
  detail: string
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface TriageTask extends TaskPacketRead {
  issue_title: string | null
  issue_body: string | null
  triage_enrichment: {
    file_count_estimate: number
    complexity_hint: 'low' | 'medium' | 'high'
    cost_estimate_range: { min: number; max: number }
  } | null
  rejection_reason: string | null
}

export type RejectionReason = 'duplicate' | 'out_of_scope' | 'needs_info' | 'wont_fix'

// --- API Functions ---

export async function fetchTasks(params: {
  offset?: number
  limit?: number
  status?: string
} = {}): Promise<{ items: TaskPacketRead[]; total: number; offset: number; limit: number }> {
  const query = new URLSearchParams()
  if (params.offset != null) query.set('offset', String(params.offset))
  if (params.limit != null) query.set('limit', String(params.limit))
  if (params.status) query.set('status', params.status)
  const qs = query.toString()
  const url = withToken(`${API_BASE}/tasks${qs ? `?${qs}` : ''}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.status}`)
  return res.json()
}

export async function fetchTaskDetail(taskId: string): Promise<TaskPacketDetail> {
  const url = withToken(`${API_BASE}/tasks/${taskId}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch task: ${res.status}`)
  return res.json()
}

export async function fetchStageMetrics(windowHours = 24): Promise<StageMetricsResponse> {
  const url = withToken(`${API_BASE}/stages/metrics?window_hours=${windowHours}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch metrics: ${res.status}`)
  return res.json()
}

export async function fetchTaskGates(taskId: string): Promise<GateEvidenceRead[]> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/gates`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch gates: ${res.status}`)
  return res.json()
}

export async function fetchGates(params: {
  offset?: number
  limit?: number
  result?: string
  stage?: string
  task_id?: string
} = {}): Promise<{ items: GateEvidenceRead[]; total: number }> {
  const query = new URLSearchParams()
  if (params.offset != null) query.set('offset', String(params.offset))
  if (params.limit != null) query.set('limit', String(params.limit))
  if (params.result) query.set('result', params.result)
  if (params.stage) query.set('stage', params.stage)
  if (params.task_id) query.set('task_id', params.task_id)
  const qs = query.toString()
  const url = withToken(`${API_BASE}/gates${qs ? `?${qs}` : ''}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch gates: ${res.status}`)
  return res.json()
}

export async function fetchGateDetail(gateId: string): Promise<GateEvidenceRead> {
  const url = withToken(`${API_BASE}/gates/${gateId}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch gate: ${res.status}`)
  return res.json()
}

export async function fetchGateMetrics(windowHours = 24): Promise<GateMetrics> {
  const url = withToken(`${API_BASE}/gates/metrics?window_hours=${windowHours}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch gate metrics: ${res.status}`)
  return res.json()
}

// --- Triage API (Epic 36) ---

export async function fetchTriageTasks(): Promise<{ items: TriageTask[]; total: number }> {
  const url = withToken(`${API_BASE}/tasks?status=triage&limit=100`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch triage tasks: ${res.status}`)
  return res.json()
}

export async function acceptTriageTask(taskId: string): Promise<{ task: TriageTask; workflow_started: boolean }> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/accept`)
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to accept task: ${res.status}`)
  return res.json()
}

export async function rejectTriageTask(taskId: string, reason: RejectionReason): Promise<TriageTask> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/reject`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) throw new Error(`Failed to reject task: ${res.status}`)
  return res.json()
}

export async function editTriageTask(taskId: string, fields: {
  issue_title?: string
  issue_body?: string
}): Promise<TriageTask> {
  const url = withToken(`${API_BASE}/tasks/${taskId}`)
  const res = await fetch(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fields),
  })
  if (!res.ok) throw new Error(`Failed to edit task: ${res.status}`)
  return res.json()
}

// --- Intent Review Types (Epic 36, Slice 2) ---

export interface IntentSpecRead {
  id: string
  taskpacket_id: string
  version: number
  goal: string
  constraints: string[]
  acceptance_criteria: string[]
  non_goals: string[]
  source: string
  created_at: string
}

export interface IntentResponse {
  current: IntentSpecRead
  versions: IntentSpecRead[]
}

export interface IntentActionResponse {
  status: string
}

// --- Intent Review API (Epic 36, Slice 2) ---

export async function fetchIntent(taskId: string): Promise<IntentResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/intent`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch intent: ${res.status}`)
  return res.json()
}

export async function approveIntent(taskId: string): Promise<IntentActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/intent/approve`)
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to approve intent: ${res.status}`)
  return res.json()
}

export async function rejectIntent(taskId: string, reason: string): Promise<IntentActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/intent/reject`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) throw new Error(`Failed to reject intent: ${res.status}`)
  return res.json()
}

export async function editIntent(taskId: string, spec: {
  goal: string
  constraints: string[]
  acceptance_criteria: string[]
  non_goals: string[]
}): Promise<IntentSpecRead> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/intent`)
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(spec),
  })
  if (!res.ok) throw new Error(`Failed to edit intent: ${res.status}`)
  return res.json()
}

export async function refineIntent(taskId: string, feedback: string): Promise<IntentSpecRead> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/intent/refine`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  })
  if (!res.ok) throw new Error(`Failed to refine intent: ${res.status}`)
  return res.json()
}

// --- Routing Review Types (Epic 36, Slice 3) ---

export interface ExpertSelectionRead {
  expert_id: string
  expert_class: string
  pattern: string
  reputation_weight: number
  reputation_confidence: number
  selection_score: number
  selection_reason: string
}

export interface RoutingResultRead {
  taskpacket_id: string
  selections: ExpertSelectionRead[]
  rationale: string
  budget_remaining: number
}

export interface RoutingActionResponse {
  status: string
}

// --- Routing Review API (Epic 36, Slice 3) ---

export async function fetchRouting(taskId: string): Promise<RoutingResultRead> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/routing`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch routing: ${res.status}`)
  return res.json()
}

export async function approveRouting(taskId: string): Promise<RoutingActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/routing/approve`)
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to approve routing: ${res.status}`)
  return res.json()
}

export async function overrideRouting(taskId: string, reason: string): Promise<RoutingActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/routing/override`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) throw new Error(`Failed to override routing: ${res.status}`)
  return res.json()
}

// --- Manual Task Creation (Epic 36, Slice 4) ---

export interface ManualTaskCreate {
  title: string
  description: string
  category?: string | null
  priority?: string | null
  acceptance_criteria?: string[] | null
  skip_triage?: boolean
}

export interface ManualTaskCreateResponse {
  task: TaskPacketRead
  workflow_started: boolean
}

export async function createManualTask(body: ManualTaskCreate): Promise<ManualTaskCreateResponse> {
  const url = withToken(`${API_BASE}/tasks`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Failed to create task: ${res.status}`)
  return res.json()
}

// --- Steering Audit Types (Epic 37 Slice 1) ---

export interface SteeringAuditLogRead {
  id: string
  task_id: string
  action: 'pause' | 'resume' | 'abort' | 'redirect' | 'retry'
  from_stage: string | null
  to_stage: string | null
  reason: string | null
  timestamp: string
  actor: string
}

// --- Steering API (Epic 37 Slice 1) ---

export interface SteeringActionResponse {
  task_id: string
  action: string
  status: string
}

export async function pauseTask(taskId: string): Promise<SteeringActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/pause`)
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to pause task: ${res.status}`)
  return res.json()
}

export async function resumeTask(taskId: string): Promise<SteeringActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/resume`)
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to resume task: ${res.status}`)
  return res.json()
}

export async function abortTask(taskId: string, reason?: string): Promise<SteeringActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/abort`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason ?? '' }),
  })
  if (!res.ok) throw new Error(`Failed to abort task: ${res.status}`)
  return res.json()
}

export async function redirectTask(
  taskId: string,
  targetStage: string,
  reason: string,
): Promise<SteeringActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/redirect`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_stage: targetStage, reason }),
  })
  if (!res.ok) throw new Error(`Failed to redirect task: ${res.status}`)
  return res.json()
}

export async function retryTask(taskId: string): Promise<SteeringActionResponse> {
  const url = withToken(`${API_BASE}/tasks/${taskId}/retry`)
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to retry task: ${res.status}`)
  return res.json()
}

export async function fetchTaskAudit(taskId: string, params: {
  limit?: number
  offset?: number
} = {}): Promise<SteeringAuditLogRead[]> {
  const query = new URLSearchParams()
  if (params.limit != null) query.set('limit', String(params.limit))
  if (params.offset != null) query.set('offset', String(params.offset))
  const qs = query.toString()
  const url = withToken(`${API_BASE}/tasks/${taskId}/audit${qs ? `?${qs}` : ''}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch audit log: ${res.status}`)
  return res.json()
}

// --- Trust Tier API ---

export type ConditionOperator =
  | 'equals'
  | 'not_equals'
  | 'less_than'
  | 'greater_than'
  | 'contains'
  | 'matches_glob'

export type AssignedTier = 'observe' | 'suggest' | 'execute'

export interface RuleCondition {
  field: string
  op: ConditionOperator
  value: string | number | boolean
}

export interface TrustTierRuleRead {
  id: string
  priority: number
  conditions: RuleCondition[]
  assigned_tier: AssignedTier
  active: boolean
  description: string | null
  created_at: string
  updated_at: string
}

export interface TrustTierRuleCreate {
  priority: number
  conditions: RuleCondition[]
  assigned_tier: AssignedTier
  active: boolean
  description?: string | null
}

export interface TrustTierRuleUpdate {
  priority?: number
  conditions?: RuleCondition[]
  assigned_tier?: AssignedTier
  active?: boolean
  description?: string | null
}

export interface SafeBoundsRead {
  max_auto_merge_lines: number | null
  max_auto_merge_cost: number | null
  max_loopbacks: number | null
  mandatory_review_patterns: string[]
  default_tier: string
  updated_at: string
}

export interface SafeBoundsUpdate {
  max_auto_merge_lines?: number | null
  max_auto_merge_cost?: number | null
  max_loopbacks?: number | null
  mandatory_review_patterns?: string[] | null
}

export interface DefaultTierRead {
  default_tier: AssignedTier
}

export async function fetchTrustRules(activeOnly = false): Promise<TrustTierRuleRead[]> {
  const url = withToken(`${API_BASE}/trust/rules${activeOnly ? '?active_only=true' : ''}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch trust rules: ${res.status}`)
  return res.json()
}

export async function createTrustRule(body: TrustTierRuleCreate): Promise<TrustTierRuleRead> {
  const url = withToken(`${API_BASE}/trust/rules`)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Failed to create trust rule: ${res.status}`)
  return res.json()
}

export async function updateTrustRule(
  ruleId: string,
  body: TrustTierRuleUpdate,
): Promise<TrustTierRuleRead> {
  const url = withToken(`${API_BASE}/trust/rules/${ruleId}`)
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Failed to update trust rule: ${res.status}`)
  return res.json()
}

export async function deleteTrustRule(ruleId: string): Promise<void> {
  const url = withToken(`${API_BASE}/trust/rules/${ruleId}`)
  const res = await fetch(url, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete trust rule: ${res.status}`)
}

export async function fetchSafetyBounds(): Promise<SafeBoundsRead> {
  const url = withToken(`${API_BASE}/trust/safety-bounds`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch safety bounds: ${res.status}`)
  return res.json()
}

export async function updateSafetyBounds(body: SafeBoundsUpdate): Promise<SafeBoundsRead> {
  const url = withToken(`${API_BASE}/trust/safety-bounds`)
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Failed to update safety bounds: ${res.status}`)
  return res.json()
}

export async function fetchDefaultTier(): Promise<DefaultTierRead> {
  const url = withToken(`${API_BASE}/trust/default-tier`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch default tier: ${res.status}`)
  return res.json()
}

export async function updateDefaultTier(tier: AssignedTier): Promise<DefaultTierRead> {
  const url = withToken(`${API_BASE}/trust/default-tier`)
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ default_tier: tier }),
  })
  if (!res.ok) throw new Error(`Failed to update default tier: ${res.status}`)
  return res.json()
}

// --- Activity API ---

export async function fetchTaskActivity(taskId: string, params: {
  offset?: number
  limit?: number
  activity_type?: string
  subphase?: string
  order?: 'asc' | 'desc'
} = {}): Promise<{ items: ActivityEntry[]; total: number }> {
  const query = new URLSearchParams()
  if (params.offset != null) query.set('offset', String(params.offset))
  if (params.limit != null) query.set('limit', String(params.limit))
  if (params.activity_type) query.set('activity_type', params.activity_type)
  if (params.subphase) query.set('subphase', params.subphase)
  if (params.order) query.set('order', params.order)
  const qs = query.toString()
  const url = withToken(`${API_BASE}/tasks/${taskId}/activity${qs ? `?${qs}` : ''}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch activity: ${res.status}`)
  return res.json()
}

// --- Budget API ---

export interface SpendEntry {
  key: string
  total_cost: number
  total_tokens_in: number
  total_tokens_out: number
  total_tokens: number
  call_count: number
  avg_latency_ms: number
  error_count: number
}

export interface BudgetSummary {
  window_hours: number
  total_cost: number
  total_calls: number
  total_cache_creation_tokens: number
  total_cache_read_tokens: number
  cache_hit_rate: number
}

export interface BudgetHistory {
  window_hours: number
  total_cost: number
  total_calls: number
  by_day: SpendEntry[]
  by_model: SpendEntry[]
}

export interface BudgetByStage {
  window_hours: number
  total_cost: number
  total_calls: number
  by_stage: SpendEntry[]
}

export interface BudgetByModel {
  window_hours: number
  total_cost: number
  total_calls: number
  by_model: SpendEntry[]
}

export interface BudgetConfig {
  daily_spend_warning: number
  weekly_budget_cap: number
  per_task_warning: number
  pause_on_budget_exceeded: boolean
  model_downgrade_on_approach: boolean
  downgrade_threshold_percent: number
  updated_at: string
}

export interface BudgetConfigUpdate {
  daily_spend_warning?: number
  weekly_budget_cap?: number
  per_task_warning?: number
  pause_on_budget_exceeded?: boolean
  model_downgrade_on_approach?: boolean
  downgrade_threshold_percent?: number
}

export async function fetchBudgetSummary(windowHours = 24): Promise<BudgetSummary> {
  const url = withToken(`${API_BASE}/budget/summary?window_hours=${windowHours}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch budget summary: ${res.status}`)
  return res.json()
}

export async function fetchBudgetHistory(windowHours = 168): Promise<BudgetHistory> {
  const url = withToken(`${API_BASE}/budget/history?window_hours=${windowHours}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch budget history: ${res.status}`)
  return res.json()
}

export async function fetchBudgetByStage(windowHours = 24): Promise<BudgetByStage> {
  const url = withToken(`${API_BASE}/budget/by-stage?window_hours=${windowHours}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch budget by stage: ${res.status}`)
  return res.json()
}

export async function fetchBudgetByModel(windowHours = 24): Promise<BudgetByModel> {
  const url = withToken(`${API_BASE}/budget/by-model?window_hours=${windowHours}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch budget by model: ${res.status}`)
  return res.json()
}

export async function fetchBudgetConfig(): Promise<BudgetConfig> {
  const url = withToken(`${API_BASE}/budget/config`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch budget config: ${res.status}`)
  return res.json()
}

export async function updateBudgetConfig(payload: BudgetConfigUpdate): Promise<BudgetConfig> {
  const url = withToken(`${API_BASE}/budget/config`)
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Failed to update budget config: ${res.status}`)
  return res.json()
}

// --- Notification API (Epic 37 Slice 5) ---

export type NotificationType = 'gate_fail' | 'cost_update' | 'steering_action' | 'trust_tier_assigned'

export interface NotificationRead {
  id: string
  type: NotificationType
  title: string
  message: string
  task_id: string | null
  read: boolean
  created_at: string
}

export interface NotificationListResponse {
  items: NotificationRead[]
  total: number
  unread_count: number
  limit: number
  offset: number
}

export async function fetchNotifications(params: {
  unread_only?: boolean
  type?: NotificationType
  limit?: number
  offset?: number
} = {}): Promise<NotificationListResponse> {
  const query = new URLSearchParams()
  if (params.unread_only) query.set('unread_only', 'true')
  if (params.type) query.set('type', params.type)
  if (params.limit != null) query.set('limit', String(params.limit))
  if (params.offset != null) query.set('offset', String(params.offset))
  const qs = query.toString()
  const url = withToken(`${API_BASE}/notifications${qs ? `?${qs}` : ''}`)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch notifications: ${res.status}`)
  return res.json()
}

export async function markNotificationRead(notificationId: string): Promise<NotificationRead> {
  const url = withToken(`${API_BASE}/notifications/${notificationId}/read`)
  const res = await fetch(url, { method: 'PATCH' })
  if (!res.ok) throw new Error(`Failed to mark notification read: ${res.status}`)
  return res.json()
}

export async function markAllNotificationsRead(): Promise<{ updated: number }> {
  const url = withToken(`${API_BASE}/notifications/mark-all-read`)
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to mark all notifications read: ${res.status}`)
  return res.json()
}
