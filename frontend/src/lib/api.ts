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
