"""Unit tests for Trust Tier Transitions + Decay + Drift (Story 2.6).

Architecture reference: thestudioarc/06-reputation-engine.md lines 26-43, 90-98
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.reputation.decay import (
    DecayScheduler,
    apply_decay,
    compute_decay_factor,
)
from src.reputation.decay import (
    clear as clear_decay,
)
from src.reputation.drift import (
    DriftDirection,
    compute_drift,
    compute_drift_for_expert,
    compute_drift_score,
    get_drift_results,
)
from src.reputation.drift import (
    clear as clear_drift,
)
from src.reputation.tiers import (
    DRIFT_SUSTAINED_COUNT,
    TrustTier,
    compute_tier,
    compute_tier_transition,
    get_tier_transitions,
)
from src.reputation.tiers import (
    DriftDirection as TierDriftDirection,
)
from src.reputation.tiers import (
    clear as clear_tiers,
)


@pytest.fixture(autouse=True)
def _clean_stores() -> None:
    """Clear stores before each test."""
    clear_decay()
    clear_drift()
    clear_tiers()


# --- Trust Tier Tests ---


class TestTierComputation:
    """Test trust tier computation based on metrics."""

    def test_shadow_low_confidence(self) -> None:
        """Low confidence -> shadow tier."""
        tier = compute_tier(
            weight=0.7,
            confidence=0.2,  # Below 0.3 threshold
            sample_count=10,
            drift_direction=TierDriftDirection.STABLE,
        )
        assert tier == TrustTier.SHADOW

    def test_shadow_low_samples(self) -> None:
        """Low sample count -> shadow tier."""
        tier = compute_tier(
            weight=0.7,
            confidence=0.5,
            sample_count=3,  # Below 5 threshold
            drift_direction=TierDriftDirection.STABLE,
        )
        assert tier == TrustTier.SHADOW

    def test_probation_meets_thresholds(self) -> None:
        """Meets probation thresholds -> probation tier."""
        tier = compute_tier(
            weight=0.5,
            confidence=0.4,
            sample_count=7,
            drift_direction=TierDriftDirection.STABLE,
        )
        assert tier == TrustTier.PROBATION

    def test_trusted_meets_all_thresholds(self) -> None:
        """Meets all trusted thresholds -> trusted tier."""
        tier = compute_tier(
            weight=0.7,  # >= 0.6
            confidence=0.6,  # >= 0.5
            sample_count=15,  # >= 10
            drift_direction=TierDriftDirection.STABLE,  # Not declining
        )
        assert tier == TrustTier.TRUSTED

    def test_trusted_blocked_by_declining_drift(self) -> None:
        """Declining drift blocks trusted tier."""
        tier = compute_tier(
            weight=0.7,
            confidence=0.6,
            sample_count=15,
            drift_direction=TierDriftDirection.DECLINING,  # Blocks trusted
        )
        assert tier == TrustTier.PROBATION


class TestTierTransitions:
    """Test tier transition logic and signals."""

    def test_transition_emits_record(self) -> None:
        """Tier transition emits TierTransition record."""
        expert_id = uuid4()

        new_tier, transition = compute_tier_transition(
            expert_id=expert_id,
            context_key="repo:general:medium",
            current_tier=TrustTier.SHADOW,
            weight=0.5,
            confidence=0.4,
            sample_count=7,
            drift_direction=TierDriftDirection.STABLE,
        )

        assert new_tier == TrustTier.PROBATION
        assert transition is not None
        assert transition.old_tier == TrustTier.SHADOW
        assert transition.new_tier == TrustTier.PROBATION
        assert len(get_tier_transitions()) == 1

    def test_no_transition_if_tier_unchanged(self) -> None:
        """No transition record if tier unchanged."""
        expert_id = uuid4()

        new_tier, transition = compute_tier_transition(
            expert_id=expert_id,
            context_key="repo:general:medium",
            current_tier=TrustTier.PROBATION,
            weight=0.5,
            confidence=0.4,
            sample_count=7,
            drift_direction=TierDriftDirection.STABLE,
        )

        assert new_tier == TrustTier.PROBATION
        assert transition is None

    def test_sustained_decline_triggers_demotion(self) -> None:
        """Sustained decline triggers tier demotion."""
        expert_id = uuid4()

        # Simulate DRIFT_SUSTAINED_COUNT consecutive declines
        for _i in range(DRIFT_SUSTAINED_COUNT):
            new_tier, transition = compute_tier_transition(
                expert_id=expert_id,
                context_key="repo:general:medium",
                current_tier=TrustTier.TRUSTED,
                weight=0.65,
                confidence=0.6,
                sample_count=15,
                drift_direction=TierDriftDirection.DECLINING,
            )

        # After sustained decline, should demote
        assert new_tier == TrustTier.PROBATION
        assert transition is not None
        assert "decline" in transition.reason.lower()

    def test_sustained_improvement_triggers_promotion(self) -> None:
        """Sustained improvement can trigger promotion."""
        expert_id = uuid4()

        # Simulate DRIFT_SUSTAINED_COUNT consecutive improvements
        for _i in range(DRIFT_SUSTAINED_COUNT):
            new_tier, _transition = compute_tier_transition(
                expert_id=expert_id,
                context_key="repo:general:medium",
                current_tier=TrustTier.PROBATION,
                weight=0.7,  # Meets trusted threshold
                confidence=0.6,
                sample_count=15,
                drift_direction=TierDriftDirection.IMPROVING,
            )

        # After sustained improvement with thresholds met, should promote
        assert new_tier == TrustTier.TRUSTED

    def test_tier_changed_at_timestamp(self) -> None:
        """Transition records include timestamp."""
        expert_id = uuid4()

        _, transition = compute_tier_transition(
            expert_id=expert_id,
            context_key="repo:general:medium",
            current_tier=TrustTier.SHADOW,
            weight=0.5,
            confidence=0.4,
            sample_count=7,
            drift_direction=TierDriftDirection.STABLE,
        )

        assert transition is not None
        assert transition.timestamp is not None


# --- Decay Tests ---


class TestDecayComputation:
    """Test decay factor computation."""

    def test_no_decay_for_recent_activity(self) -> None:
        """No decay for recently active experts."""
        now = datetime.now(UTC)
        last_outcome = now - timedelta(days=1)

        factor = compute_decay_factor(last_outcome, now)
        assert factor > 0.99  # Minimal decay

    def test_decay_factor_reduces_over_time(self) -> None:
        """Decay factor reduces as time passes."""
        now = datetime.now(UTC)
        factor_30d = compute_decay_factor(now - timedelta(days=30), now)
        factor_60d = compute_decay_factor(now - timedelta(days=60), now)
        factor_90d = compute_decay_factor(now - timedelta(days=90), now)

        assert factor_30d > factor_60d > factor_90d
        # At half-life (90 days), factor should be ~0.5
        assert 0.45 <= factor_90d <= 0.55

    def test_decay_floor_respected(self) -> None:
        """Decay respects floor threshold."""
        expert_id = uuid4()
        now = datetime.now(UTC)

        result = apply_decay(
            expert_id=expert_id,
            context_key="repo:general:medium",
            current_weight=0.8,
            current_confidence=0.6,
            last_outcome_at=now - timedelta(days=180),
            now=now,
            decay_floor=0.3,
        )

        assert result.new_weight >= 0.3  # Floor respected

    def test_confidence_decays_with_weight(self) -> None:
        """Confidence decays along with weight."""
        expert_id = uuid4()
        now = datetime.now(UTC)

        result = apply_decay(
            expert_id=expert_id,
            context_key="repo:general:medium",
            current_weight=0.8,
            current_confidence=0.6,
            last_outcome_at=now - timedelta(days=90),  # Half-life
            now=now,
        )

        assert result.new_confidence < result.old_confidence


class TestDecayScheduler:
    """Test decay scheduler functionality."""

    def test_scheduler_processes_inactive_experts(self) -> None:
        """Scheduler processes experts past decay period."""
        now = datetime.now(UTC)
        expert_id = uuid4()

        # Mock weight record
        class MockWeight:
            def __init__(self) -> None:
                self.expert_id = expert_id
                self.context_key = "repo:general:medium"
                self.weight = 0.8
                self.confidence = 0.6
                self.last_indicator_at = now - timedelta(days=14)  # 2 weeks inactive

        weights_updated: list[tuple[str, float, float]] = []

        def mock_update(eid: str, ctx: str, w: float, c: float) -> None:
            weights_updated.append((ctx, w, c))

        scheduler = DecayScheduler(decay_period_days=7)
        results = scheduler.run_decay(
            get_all_weights_fn=lambda: [MockWeight()],
            update_weight_fn=mock_update,
            now=now,
        )

        assert len(results) == 1
        assert results[0].decay_applied is True
        assert len(weights_updated) == 1

    def test_scheduler_skips_active_experts(self) -> None:
        """Scheduler skips recently active experts."""
        now = datetime.now(UTC)

        class MockWeight:
            def __init__(self) -> None:
                self.expert_id = uuid4()
                self.context_key = "repo:general:medium"
                self.weight = 0.8
                self.confidence = 0.6
                self.last_indicator_at = now - timedelta(days=3)  # Active

        scheduler = DecayScheduler(decay_period_days=7)
        results = scheduler.run_decay(
            get_all_weights_fn=lambda: [MockWeight()],
            update_weight_fn=None,
            now=now,
        )

        assert len(results) == 0

    def test_scheduler_should_run_daily(self) -> None:
        """Scheduler should run once per day."""
        scheduler = DecayScheduler()

        assert scheduler.should_run() is True

        # Simulate run
        scheduler._last_run = datetime.now(UTC)
        assert scheduler.should_run() is False

        # After 24+ hours
        scheduler._last_run = datetime.now(UTC) - timedelta(hours=25)
        assert scheduler.should_run() is True


# --- Drift Tests ---


class TestDriftComputation:
    """Test drift direction computation."""

    def test_improving_positive_slope(self) -> None:
        """Positive slope -> improving drift."""
        # Steadily increasing weights with steep slope (> 0.05)
        weights = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

        direction = compute_drift(weights)
        assert direction == DriftDirection.IMPROVING

    def test_declining_negative_slope(self) -> None:
        """Negative slope -> declining drift."""
        # Steadily decreasing weights with steep slope (< -0.05)
        weights = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3]

        direction = compute_drift(weights)
        assert direction == DriftDirection.DECLINING

    def test_stable_flat_slope(self) -> None:
        """Flat slope -> stable drift."""
        # Roughly constant weights
        weights = [0.5, 0.51, 0.49, 0.5, 0.51, 0.5]

        direction = compute_drift(weights)
        assert direction == DriftDirection.STABLE

    def test_stable_insufficient_samples(self) -> None:
        """Insufficient samples -> stable drift."""
        weights = [0.5, 0.6]  # Only 2 samples

        direction = compute_drift(weights)
        assert direction == DriftDirection.STABLE

    def test_drift_uses_window(self) -> None:
        """Drift uses rolling window."""
        # Old data declining, recent data improving with steep slope
        weights = [0.7, 0.6, 0.5, 0.4, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

        direction = compute_drift(weights, window_size=5)
        # Last 5 are improving (0.4, 0.5, 0.6, 0.7, 0.8)
        assert direction == DriftDirection.IMPROVING


class TestDriftScore:
    """Test drift score computation."""

    def test_drift_score_positive_for_improving(self) -> None:
        """Drift score is positive for improving trend."""
        weights = [0.4, 0.5, 0.6, 0.7]
        score = compute_drift_score(weights)
        assert score > 0

    def test_drift_score_negative_for_declining(self) -> None:
        """Drift score is negative for declining trend."""
        weights = [0.7, 0.6, 0.5, 0.4]
        score = compute_drift_score(weights)
        assert score < 0

    def test_drift_score_near_zero_for_stable(self) -> None:
        """Drift score is near zero for stable trend."""
        weights = [0.5, 0.5, 0.5, 0.5]
        score = compute_drift_score(weights)
        assert -0.1 <= score <= 0.1


class TestDriftForExpert:
    """Test drift computation for specific experts."""

    def test_records_drift_result(self) -> None:
        """Drift computation records result."""
        expert_id = uuid4()
        weights = [0.4, 0.5, 0.6, 0.7]

        result = compute_drift_for_expert(
            expert_id=expert_id,
            context_key="repo:general:medium",
            weight_history=weights,
        )

        assert result.direction == DriftDirection.IMPROVING
        assert result.slope > 0
        assert len(get_drift_results()) == 1
