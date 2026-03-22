"""Dashboard task list API — paginated TaskPacket listing with filters."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.events import _verify_token
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketCreate, TaskPacketRead, TaskPacketRow, TaskPacketStatus
from src.models.taskpacket_crud import create as create_taskpacket
from src.models.taskpacket_crud import get_by_id as get_taskpacket_by_id
from src.publisher.evidence_payload import EvidencePayload, TaskSummary

logger = logging.getLogger(__name__)
router = APIRouter()


class StageCost(BaseModel):
    """Cost breakdown for a single pipeline stage."""

    stage: str
    cost: float = 0.0
    model: str | None = None


class TaskPacketDetail(TaskPacketRead):
    """Extended TaskPacket with per-stage cost and model info."""

    cost_by_stage: list[StageCost] = Field(default_factory=list)
    total_cost: float = 0.0


class ManualTaskCreate(BaseModel):
    """Request body for manually creating a task from the dashboard."""

    title: str = Field(..., min_length=1, max_length=500, description="Task title")
    description: str = Field(..., min_length=1, description="Task description (Markdown)")
    category: str | None = Field(None, max_length=100, description="Optional category tag")
    priority: str | None = Field(
        None, max_length=50, description="Optional priority (e.g. 'high', 'medium', 'low')"
    )
    acceptance_criteria: list[str] | None = Field(
        None, description="Optional acceptance criteria lines"
    )
    skip_triage: bool = Field(
        False, description="When True, bypasses TRIAGE and starts the workflow immediately"
    )


class ManualTaskCreateResponse(BaseModel):
    """Response after manually creating a task."""

    task: TaskPacketRead
    workflow_started: bool


@router.post("/tasks", status_code=201)
async def create_manual_task(
    body: ManualTaskCreate,
    session: AsyncSession = Depends(get_session),
) -> ManualTaskCreateResponse:
    """Create a task manually from the planning dashboard.

    When ``skip_triage=False`` (default) the task is created in **TRIAGE** status
    and must be accepted via ``POST /tasks/{id}/accept`` before the pipeline starts.

    When ``skip_triage=True`` the task is created in **RECEIVED** status and the
    Temporal workflow is started immediately.

    Optional fields (category, priority, acceptance_criteria) are stored in
    ``triage_enrichment`` so the triage queue UI can display them.
    """
    # Build triage enrichment with optional metadata
    enrichment: dict[str, Any] = {"source": "manual"}
    if body.category is not None:
        enrichment["category"] = body.category
    if body.priority is not None:
        enrichment["priority"] = body.priority
    if body.acceptance_criteria:
        enrichment["acceptance_criteria"] = [ac for ac in body.acceptance_criteria if ac.strip()]

    # Use a UUID-based delivery_id for uniqueness; repo="__manual__" marks origin
    delivery_id = f"manual-{uuid4()}"
    task_data = TaskPacketCreate(
        repo="__manual__",
        issue_id=0,
        delivery_id=delivery_id,
        source_name="manual",
        issue_title=body.title,
        issue_body=body.description,
        triage_enrichment=enrichment,
    )

    workflow_started = False

    if body.skip_triage:
        # Create in RECEIVED and fire the Temporal workflow immediately
        taskpacket = await create_taskpacket(
            session, task_data, initial_status=TaskPacketStatus.RECEIVED
        )
        try:
            from src.ingress.workflow_trigger import start_workflow

            await start_workflow(
                taskpacket.id,
                taskpacket.correlation_id,
                repo=taskpacket.repo,
                issue_title=body.title,
                issue_body=body.description,
            )
            workflow_started = True
        except Exception:
            logger.exception(
                "Failed to start Temporal workflow for manual task %s", taskpacket.id
            )
    else:
        # Create in TRIAGE for human review before pipeline entry
        taskpacket = await create_taskpacket(
            session, task_data, initial_status=TaskPacketStatus.TRIAGE
        )

    return ManualTaskCreateResponse(task=taskpacket, workflow_started=workflow_started)


@router.get("/tasks")
async def list_tasks(
    token: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: TaskPacketStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    repo: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List TaskPackets with pagination and optional filters.

    Returns JSON with ``items`` (array of TaskPacketRead) and ``total`` count.
    Requires ``?token=`` query param when ``dashboard_token`` is set.
    """
    _verify_token(token)

    # Build base query
    stmt = select(TaskPacketRow)
    count_stmt = select(func.count()).select_from(TaskPacketRow)

    # Apply filters
    if status is not None:
        stmt = stmt.where(TaskPacketRow.status == status)
        count_stmt = count_stmt.where(TaskPacketRow.status == status)
    if created_after is not None:
        stmt = stmt.where(TaskPacketRow.created_at >= created_after)
        count_stmt = count_stmt.where(TaskPacketRow.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(TaskPacketRow.created_at <= created_before)
        count_stmt = count_stmt.where(TaskPacketRow.created_at <= created_before)
    if repo is not None:
        stmt = stmt.where(TaskPacketRow.repo == repo)
        count_stmt = count_stmt.where(TaskPacketRow.repo == repo)

    # Get total count
    total = (await session.execute(count_stmt)).scalar_one()

    # Apply ordering and pagination
    stmt = stmt.order_by(TaskPacketRow.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    return {
        "items": [TaskPacketRead.model_validate(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


def _extract_cost_by_stage(stage_timings: dict[str, Any] | None) -> list[StageCost]:
    """Build per-stage cost list from stage_timings metadata.

    Stage timings may include optional ``cost`` and ``model`` keys per stage.
    Returns an empty list when no timings are available.
    """
    if not stage_timings:
        return []
    stages: list[StageCost] = []
    for name, data in stage_timings.items():
        if not isinstance(data, dict):
            continue
        stages.append(
            StageCost(
                stage=name,
                cost=data.get("cost", 0.0),
                model=data.get("model"),
            )
        )
    return stages


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    token: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> TaskPacketDetail:
    """Get a single TaskPacket by ID with stage timestamps and cost breakdown.

    Returns 404 when the task ID is not found.
    """
    _verify_token(token)

    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")

    base = TaskPacketRead.model_validate(row)
    cost_by_stage = _extract_cost_by_stage(row.stage_timings)
    total_cost = sum(s.cost for s in cost_by_stage)

    return TaskPacketDetail(
        **base.model_dump(),
        cost_by_stage=cost_by_stage,
        total_cost=total_cost,
    )


# ---------------------------------------------------------------------------
# Stage metrics aggregation (S1.B4)
# ---------------------------------------------------------------------------

PIPELINE_STAGES = [
    "intake",
    "context",
    "intent",
    "router",
    "assembler",
    "implement",
    "verify",
    "qa",
    "publish",
]

# Statuses that indicate a task completed successfully past verification.
_PASS_STATUSES = {
    TaskPacketStatus.VERIFICATION_PASSED,
    TaskPacketStatus.PUBLISHED,
    TaskPacketStatus.AWAITING_APPROVAL,
}


class StageMetric(BaseModel):
    """Metrics for a single pipeline stage."""

    stage: str
    pass_rate: float | None = None  # 0.0-1.0, None when no data
    avg_duration_seconds: float | None = None
    throughput: int = 0  # tasks that entered this stage in the window


class StageMetricsResponse(BaseModel):
    """Aggregate pipeline stage metrics over a time window."""

    window_hours: int
    stages: list[StageMetric]


def _compute_stage_metrics(
    rows: list[Any],
    stages: list[str] | None = None,
) -> list[StageMetric]:
    """Compute per-stage pass rate, avg duration, and throughput from rows.

    Each row must expose ``stage_timings`` (dict | None) and ``status``.
    """
    stages = stages or PIPELINE_STAGES
    # Accumulators per stage
    counts: dict[str, int] = dict.fromkeys(stages, 0)
    durations: dict[str, list[float]] = {s: [] for s in stages}
    passes: dict[str, int] = dict.fromkeys(stages, 0)

    for row in rows:
        timings = row.stage_timings
        if not timings or not isinstance(timings, dict):
            continue
        status = row.status
        for stage in stages:
            sdata = timings.get(stage)
            if not isinstance(sdata, dict) or "start" not in sdata:
                continue
            counts[stage] += 1
            # Duration
            start_str = sdata.get("start")
            end_str = sdata.get("end")
            if start_str and end_str:
                try:
                    start_dt = datetime.fromisoformat(start_str)
                    end_dt = datetime.fromisoformat(end_str)
                    dur = (end_dt - start_dt).total_seconds()
                    if dur >= 0:
                        durations[stage].append(dur)
                except (ValueError, TypeError):
                    pass
            # Pass rate: count as pass if task status is a success status
            if status in _PASS_STATUSES:
                passes[stage] += 1

    result: list[StageMetric] = []
    for stage in stages:
        total = counts[stage]
        dur_list = durations[stage]
        result.append(
            StageMetric(
                stage=stage,
                pass_rate=passes[stage] / total if total > 0 else None,
                avg_duration_seconds=(
                    sum(dur_list) / len(dur_list) if dur_list else None
                ),
                throughput=total,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Historical comparison query (Story 36.20 — stretch)
# ---------------------------------------------------------------------------

MIN_SIMILAR_TASKS = 5  # minimum count before comparison data is returned


class StageDurationStats(BaseModel):
    """Average duration stats for a single pipeline stage."""

    stage: str
    avg_duration_seconds: float


class HistoricalComparisonResponse(BaseModel):
    """Stats from similar past TaskPackets.

    ``available`` is False when fewer than 5 similar tasks exist.
    All aggregate fields are None when available=False.
    """

    available: bool
    similar_count: int = 0
    avg_complexity_score: float | None = None
    common_risk_flags: list[str] | None = None  # flags present in >50% of similar tasks
    pass_rate: float | None = None  # fraction that reached a success status
    avg_loopback_count: float | None = None
    stage_durations: list[StageDurationStats] | None = None


def _extract_complexity_band(complexity_index: dict[str, Any] | None) -> str | None:
    """Extract the band string (low/medium/high/critical) from a complexity_index dict."""
    if not complexity_index or not isinstance(complexity_index, dict):
        return None
    return complexity_index.get("band")


def _build_comparison(rows: list[Any]) -> HistoricalComparisonResponse:
    """Compute aggregate statistics from a list of similar TaskPacketRows."""
    if len(rows) < MIN_SIMILAR_TASKS:
        return HistoricalComparisonResponse(available=False, similar_count=len(rows))

    count = len(rows)

    # Avg complexity score
    scores: list[float] = []
    for r in rows:
        ci = r.complexity_index
        if isinstance(ci, dict):
            s = ci.get("score")
            if isinstance(s, (int, float)):
                scores.append(float(s))
    avg_score = sum(scores) / len(scores) if scores else None

    # Common risk flags (present in >50% of tasks that have risk_flags)
    flag_counts: dict[str, int] = {}
    tasks_with_flags = 0
    for r in rows:
        rf = r.risk_flags
        if isinstance(rf, dict):
            tasks_with_flags += 1
            for flag, value in rf.items():
                if value:
                    flag_counts[flag] = flag_counts.get(flag, 0) + 1
    threshold = max(1, tasks_with_flags // 2)
    common_flags = sorted(f for f, c in flag_counts.items() if c > threshold) or None

    # Pass rate
    pass_statuses = {
        TaskPacketStatus.VERIFICATION_PASSED,
        TaskPacketStatus.PUBLISHED,
        TaskPacketStatus.AWAITING_APPROVAL,
    }
    passed = sum(1 for r in rows if r.status in pass_statuses)
    pass_rate = passed / count

    # Avg loopback count
    avg_loopbacks = sum(r.loopback_count for r in rows) / count

    # Avg stage durations from stage_timings
    dur_sums: dict[str, list[float]] = {}
    for r in rows:
        timings = r.stage_timings
        if not isinstance(timings, dict):
            continue
        for stage, sdata in timings.items():
            if not isinstance(sdata, dict):
                continue
            start_str = sdata.get("start")
            end_str = sdata.get("end")
            if start_str and end_str:
                try:
                    start_dt = datetime.fromisoformat(start_str)
                    end_dt = datetime.fromisoformat(end_str)
                    dur = (end_dt - start_dt).total_seconds()
                    if dur >= 0:
                        dur_sums.setdefault(stage, []).append(dur)
                except (ValueError, TypeError):
                    pass
    stage_durations = [
        StageDurationStats(stage=s, avg_duration_seconds=sum(durs) / len(durs))
        for s, durs in sorted(dur_sums.items())
        if durs
    ] or None

    return HistoricalComparisonResponse(
        available=True,
        similar_count=count,
        avg_complexity_score=avg_score,
        common_risk_flags=common_flags,
        pass_rate=pass_rate,
        avg_loopback_count=avg_loopbacks,
        stage_durations=stage_durations,
    )


@router.get("/tasks/{task_id}/comparison")
async def historical_comparison(
    task_id: UUID,
    token: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> HistoricalComparisonResponse:
    """Return historical stats from similar past TaskPackets.

    Similarity is defined as:
    1. Same repo AND same complexity band (primary match)
    2. Falls back to same complexity band only (secondary match)

    Returns ``available: false`` when fewer than 5 similar tasks exist.
    The requesting task itself is always excluded from the comparison set.
    """
    _verify_token(token)

    target = await session.get(TaskPacketRow, task_id)
    if target is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")

    complexity_band = _extract_complexity_band(target.complexity_index)

    # Build query: exclude the target task; only completed/processed tasks
    # (i.e. tasks that have moved beyond RECEIVED) to get meaningful stats.
    terminal_statuses = {
        TaskPacketStatus.VERIFICATION_PASSED,
        TaskPacketStatus.VERIFICATION_FAILED,
        TaskPacketStatus.PUBLISHED,
        TaskPacketStatus.AWAITING_APPROVAL,
        TaskPacketStatus.AWAITING_APPROVAL_EXPIRED,
        TaskPacketStatus.REJECTED,
        TaskPacketStatus.FAILED,
    }

    base_stmt = (
        select(TaskPacketRow)
        .where(TaskPacketRow.id != task_id)
        .where(TaskPacketRow.status.in_(list(terminal_statuses)))
    )

    # Primary: same repo + same complexity band (if band is known)
    if complexity_band and target.repo:
        # Filter by repo first (cheap) — band filtering done in Python
        repo_stmt = base_stmt.where(TaskPacketRow.repo == target.repo)
        result = await session.execute(repo_stmt)
        repo_rows = [
            r
            for r in result.scalars().all()
            if _extract_complexity_band(r.complexity_index) == complexity_band
        ]
        if len(repo_rows) >= MIN_SIMILAR_TASKS:
            return _build_comparison(repo_rows)

    # Secondary: same complexity band across all repos
    if complexity_band:
        result = await session.execute(base_stmt)
        band_rows = [
            r
            for r in result.scalars().all()
            if _extract_complexity_band(r.complexity_index) == complexity_band
        ]
        if len(band_rows) >= MIN_SIMILAR_TASKS:
            return _build_comparison(band_rows)

    # Fallback: same repo only (no band info or not enough band-matched tasks)
    if target.repo:
        repo_stmt = base_stmt.where(TaskPacketRow.repo == target.repo)
        result = await session.execute(repo_stmt)
        repo_rows_all = list(result.scalars().all())
        if len(repo_rows_all) >= MIN_SIMILAR_TASKS:
            return _build_comparison(repo_rows_all)

    # Not enough data for any similarity dimension
    return HistoricalComparisonResponse(available=False, similar_count=0)


@router.get("/stages/metrics")
async def stage_metrics(
    token: str | None = Query(None),
    window_hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
) -> StageMetricsResponse:
    """Per-stage pass rate, avg duration, and throughput over a configurable window.

    Query params:
    - ``window_hours``: lookback window in hours (default 24, max 720).
    - ``token``: auth token (required when dashboard_token is configured).
    """
    _verify_token(token)

    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    stmt = (
        select(TaskPacketRow)
        .where(TaskPacketRow.stage_timings.isnot(None))
        .where(TaskPacketRow.created_at >= cutoff)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    return StageMetricsResponse(
        window_hours=window_hours,
        stages=_compute_stage_metrics(rows),
    )


# ---------------------------------------------------------------------------
# Evidence payload endpoint (Epic 38 Story 38.7)
# ---------------------------------------------------------------------------


def _build_evidence_payload(task: TaskPacketRead) -> EvidencePayload:
    """Build an EvidencePayload from a TaskPacketRead.

    Populates the task_summary section from stored TaskPacket fields.
    Sections that require runtime data not persisted in the DB (intent,
    gate_results, cost_breakdown, provenance) are left as None.
    """
    task_summary = TaskSummary(
        taskpacket_id=task.id,
        correlation_id=task.correlation_id,
        repo=task.repo,
        issue_id=task.issue_id,
        issue_title=task.issue_title,
        status=task.status.value,
        trust_tier=task.task_trust_tier.value if task.task_trust_tier is not None else None,
        loopback_count=task.loopback_count,
        created_at=task.created_at,
        updated_at=task.updated_at,
        pr_number=task.pr_number,
        pr_url=task.pr_url,
    )
    return EvidencePayload(
        generated_at=datetime.now(UTC),
        task_summary=task_summary,
    )


@router.get("/tasks/{task_id}/evidence", response_model=EvidencePayload)
async def get_task_evidence(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EvidencePayload:
    """Return a structured EvidencePayload JSON document for a TaskPacket.

    The payload includes the task summary (id, status, repo, issue, trust tier,
    PR details) populated from the stored TaskPacket record.  Sections that
    require runtime data not persisted in the database (intent, gate_results,
    cost_breakdown, provenance) are omitted (null) and will be enriched by the
    Evidence Explorer frontend via other endpoints once available.

    Returns 404 when the task ID is not found.

    Epic 38, Story 38.7.
    """
    task = await get_taskpacket_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")

    return _build_evidence_payload(task)
