# Pipeline Latency Baseline

## Date

2026-03-12 (initial measurement)

## Environment

- Python 3.12+
- Mock providers (no external services)
- Temporal test environment (in-process)
- OS: Windows 11 / Linux (CI)

## Methodology

Latency measured via `time.perf_counter()` wrapping the full pipeline
execution in `tests/integration/test_full_pipeline.py::TestPipelineLatency`.

All 9 stages use mock activity implementations that return immediately
with realistic data shapes. No network I/O, no LLM calls, no database
queries.

### How to reproduce

```bash
pytest tests/integration/test_full_pipeline.py::TestPipelineLatency -v -s
```

The `TIMING: total=...` line in stdout shows the measured duration.

## Baseline Results

| Stage | Mock Duration | Notes |
|-------|--------------|-------|
| Intake | <1ms | Pure function (evaluate_eligibility) |
| Context | <1ms | Mock — returns static data |
| Intent | <1ms | Mock — returns static data |
| Router | <1ms | Pure function (route) |
| Assembler | <1ms | Mock — returns static data |
| Implement | <1ms | Mock — returns static data |
| Verify | <1ms | Mock — returns passed |
| QA | <1ms | Mock — returns passed |
| Publish | <1ms | Mock — returns PR data |
| **Total** | **<2s** | Dominated by Temporal test env startup |

## Expected Variance

- Mock providers: near-zero per-stage latency
- Temporal test environment startup: 500ms-2s (one-time per test session)
- Real providers (future): 10-100x slower due to LLM calls, DB queries, subprocess execution
- CI environment: may be slower due to resource constraints

## Assertion

The test asserts `total < 5 seconds` to allow headroom for CI variance
while catching regressions that would indicate a real performance issue.
