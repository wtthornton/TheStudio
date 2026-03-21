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
