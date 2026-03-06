"""Unit tests for Reputation Engine (Story 2.5).

Architecture reference: thestudioarc/06-reputation-engine.md
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.reputation.engine import (
    _compute_confidence,
    _compute_decay_factor,
    _compute_drift,
    _compute_trust_tier,
    _compute_weight,
    clear,
    get_all_weights,
    get_best_experts_for_context,
    get_expert_weights_for_router,
    get_weight,
    query_weights,
    update_weight,
)
from src.reputation.models import (
    CONFIDENCE_BASE,
    CONFIDENCE_MAX,
    DECAY_HALF_LIFE_DAYS,
    DriftSignal,
    TrustTier,
    WeightQuery,
    WeightUpdate,
)


@pytest.fixture(autouse=True)
def _clean_stores() -> None:
    """Clear in-memory stores before each test."""
    clear()


class TestConfidenceComputation:
    """Test confidence computation from sample size."""

    def test_zero_samples_returns_base(self) -> None:
        assert _compute_confidence(0) == CONFIDENCE_BASE

    def test_one_sample_above_base(self) -> None:
        conf = _compute_confidence(1)
        assert conf > CONFIDENCE_BASE

    def test_confidence_increases_with_samples(self) -> None:
        conf_5 = _compute_confidence(5)
        conf_10 = _compute_confidence(10)
        conf_50 = _compute_confidence(50)
        assert conf_5 < conf_10 < conf_50

    def test_confidence_capped_at_max(self) -> None:
        # Even with many samples, confidence should not exceed max
        conf = _compute_confidence(10000)
        assert conf <= CONFIDENCE_MAX

    def test_confidence_grows_logarithmically(self) -> None:
        # Logarithmic growth: doubling samples gives constant additive increase
        conf_10 = _compute_confidence(10)
        conf_20 = _compute_confidence(20)

        # But the percentage increase should decrease with more samples
        pct_increase_10_20 = (conf_20 - conf_10) / conf_10

        conf_100 = _compute_confidence(100)
        conf_200 = _compute_confidence(200)
        pct_increase_100_200 = (conf_200 - conf_100) / conf_100

        # Logarithmic growth: percentage increase decreases as base increases
        assert pct_increase_100_200 < pct_increase_10_20


class TestDecayFactor:
    """Test decay factor computation."""

    def test_no_last_indicator_returns_one(self) -> None:
        factor = _compute_decay_factor(None, datetime.now(UTC))
        assert factor == 1.0

    def test_same_day_no_decay(self) -> None:
        now = datetime.now(UTC)
        factor = _compute_decay_factor(now, now)
        assert factor == 1.0

    def test_half_life_decay(self) -> None:
        """After DECAY_HALF_LIFE_DAYS, factor should be ~0.5."""
        now = datetime.now(UTC)
        past = now - timedelta(days=DECAY_HALF_LIFE_DAYS)
        factor = _compute_decay_factor(past, now)
        assert 0.45 <= factor <= 0.55  # Allow some tolerance

    def test_double_half_life_decay(self) -> None:
        """After 2x half-life, factor should be ~0.25."""
        now = datetime.now(UTC)
        past = now - timedelta(days=DECAY_HALF_LIFE_DAYS * 2)
        factor = _compute_decay_factor(past, now)
        assert 0.2 <= factor <= 0.3

    def test_decay_always_positive(self) -> None:
        now = datetime.now(UTC)
        past = now - timedelta(days=365 * 5)  # 5 years ago
        factor = _compute_decay_factor(past, now)
        assert factor > 0


class TestWeightComputation:
    """Test weight normalization."""

    def test_zero_samples_neutral_weight(self) -> None:
        weight = _compute_weight(0.0, 0, 1.0)
        assert weight == 0.5

    def test_positive_raw_sum_increases_weight(self) -> None:
        weight = _compute_weight(1.0, 1, 1.0)
        assert weight > 0.5

    def test_negative_raw_sum_decreases_weight(self) -> None:
        weight = _compute_weight(-1.0, 1, 1.0)
        assert weight < 0.5

    def test_weight_bounded_zero_to_one(self) -> None:
        # Extreme positive
        weight_pos = _compute_weight(100.0, 10, 1.0)
        assert 0.0 <= weight_pos <= 1.0

        # Extreme negative
        weight_neg = _compute_weight(-100.0, 10, 1.0)
        assert 0.0 <= weight_neg <= 1.0

    def test_decay_reduces_weight_impact(self) -> None:
        weight_no_decay = _compute_weight(1.0, 1, 1.0)
        weight_with_decay = _compute_weight(1.0, 1, 0.5)
        # With decay, positive effect is reduced
        assert weight_with_decay < weight_no_decay


class TestDriftDetection:
    """Test drift signal computation."""

    def test_insufficient_history_stable(self) -> None:
        assert _compute_drift([]) == DriftSignal.STABLE
        assert _compute_drift([0.5]) == DriftSignal.STABLE
        assert _compute_drift([0.5, 0.5]) == DriftSignal.STABLE

    def test_improving_trend(self) -> None:
        # Clear upward trend
        history = [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75]
        assert _compute_drift(history) == DriftSignal.IMPROVING

    def test_declining_trend(self) -> None:
        # Clear downward trend
        history = [0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3]
        assert _compute_drift(history) == DriftSignal.DECLINING

    def test_stable_no_trend(self) -> None:
        # Flat or oscillating
        history = [0.5, 0.51, 0.49, 0.5, 0.51, 0.49, 0.5, 0.5, 0.51, 0.49]
        assert _compute_drift(history) == DriftSignal.STABLE


class TestTrustTierTransitions:
    """Test trust tier promotion and demotion."""

    def test_shadow_to_probation_promotion(self) -> None:
        tier = _compute_trust_tier(
            TrustTier.SHADOW, weight=0.5, confidence=0.4, sample_count=10
        )
        assert tier == TrustTier.PROBATION

    def test_shadow_stays_shadow_low_samples(self) -> None:
        tier = _compute_trust_tier(
            TrustTier.SHADOW, weight=0.5, confidence=0.4, sample_count=2
        )
        assert tier == TrustTier.SHADOW

    def test_shadow_stays_shadow_low_weight(self) -> None:
        tier = _compute_trust_tier(
            TrustTier.SHADOW, weight=0.1, confidence=0.4, sample_count=10
        )
        assert tier == TrustTier.SHADOW

    def test_probation_to_trusted_promotion(self) -> None:
        tier = _compute_trust_tier(
            TrustTier.PROBATION, weight=0.6, confidence=0.7, sample_count=25
        )
        assert tier == TrustTier.TRUSTED

    def test_probation_to_shadow_demotion(self) -> None:
        tier = _compute_trust_tier(
            TrustTier.PROBATION, weight=0.0, confidence=0.4, sample_count=10
        )
        assert tier == TrustTier.SHADOW

    def test_trusted_to_probation_demotion(self) -> None:
        tier = _compute_trust_tier(
            TrustTier.TRUSTED, weight=0.15, confidence=0.7, sample_count=15
        )
        assert tier == TrustTier.PROBATION


class TestWeightUpdateCreation:
    """Test creating new weight records."""

    def test_create_new_weight_record(self) -> None:
        expert_id = uuid4()
        update = WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="owner/repo:general:medium",
            normalized_weight=1.0,
        )

        result = update_weight(update)

        assert result.expert_id == expert_id
        assert result.context_key == "owner/repo:general:medium"
        assert result.sample_count == 1
        assert result.trust_tier == TrustTier.SHADOW
        assert result.weight > 0.5  # Positive indicator increases weight

    def test_create_stores_in_memory(self) -> None:
        expert_id = uuid4()
        update = WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="owner/repo:general:low",
            normalized_weight=0.5,
        )

        update_weight(update)

        stored = get_weight(expert_id, "owner/repo:general:low")
        assert stored is not None
        assert stored.expert_id == expert_id


class TestWeightUpdateIncremental:
    """Test incremental weight updates."""

    def test_multiple_updates_accumulate(self) -> None:
        expert_id = uuid4()
        context = "owner/repo:security:high"

        # First update
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key=context,
            normalized_weight=0.5,
        ))

        first = get_weight(expert_id, context)
        assert first is not None
        assert first.sample_count == 1

        # Second update
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key=context,
            normalized_weight=0.5,
        ))

        second = get_weight(expert_id, context)
        assert second is not None
        assert second.sample_count == 2

    def test_negative_updates_decrease_weight(self) -> None:
        expert_id = uuid4()
        context = "owner/repo:general:medium"

        # Positive update
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key=context,
            normalized_weight=1.0,
        ))
        after_positive = get_weight(expert_id, context)
        assert after_positive is not None

        # Negative update
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key=context,
            normalized_weight=-1.0,
        ))
        after_negative = get_weight(expert_id, context)
        assert after_negative is not None
        assert after_negative.weight < after_positive.weight

    def test_confidence_increases_with_updates(self) -> None:
        expert_id = uuid4()
        context = "owner/repo:general:medium"

        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key=context,
            normalized_weight=0.5,
        ))
        first_conf = get_weight(expert_id, context)
        assert first_conf is not None

        for _ in range(10):
            update_weight(WeightUpdate(
                expert_id=expert_id,
                expert_version=1,
                context_key=context,
                normalized_weight=0.5,
            ))

        later_conf = get_weight(expert_id, context)
        assert later_conf is not None
        assert later_conf.confidence > first_conf.confidence


class TestWeightQuery:
    """Test weight query functionality."""

    def test_query_by_expert_id(self) -> None:
        expert_1 = uuid4()
        expert_2 = uuid4()

        update_weight(WeightUpdate(
            expert_id=expert_1,
            expert_version=1,
            context_key="repo:general:medium",
            normalized_weight=0.5,
        ))
        update_weight(WeightUpdate(
            expert_id=expert_2,
            expert_version=1,
            context_key="repo:general:medium",
            normalized_weight=0.5,
        ))

        results = query_weights(WeightQuery(expert_id=expert_1))
        assert len(results) == 1
        assert results[0].expert_id == expert_1

    def test_query_by_context_key(self) -> None:
        expert_id = uuid4()

        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="repo:security:high",
            normalized_weight=0.5,
        ))
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="repo:general:low",
            normalized_weight=0.5,
        ))

        results = query_weights(WeightQuery(context_key="repo:security:high"))
        assert len(results) == 1
        assert results[0].context_key == "repo:security:high"

    def test_query_by_repo_prefix(self) -> None:
        expert_id = uuid4()

        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="owner/repo1:general:medium",
            normalized_weight=0.5,
        ))
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="owner/repo2:general:medium",
            normalized_weight=0.5,
        ))

        results = query_weights(WeightQuery(repo="owner/repo1"))
        assert len(results) == 1
        assert "repo1" in results[0].context_key

    def test_query_min_confidence_filter(self) -> None:
        expert_id = uuid4()

        # Single update = low confidence
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="repo:general:medium",
            normalized_weight=0.5,
        ))

        # Should not appear with high min_confidence
        results = query_weights(WeightQuery(min_confidence=0.9))
        assert len(results) == 0

    def test_query_sorted_by_weight(self) -> None:
        expert_high = uuid4()
        expert_low = uuid4()

        # Expert with high weight
        for _ in range(5):
            update_weight(WeightUpdate(
                expert_id=expert_high,
                expert_version=1,
                context_key="repo:general:medium",
                normalized_weight=1.0,
            ))

        # Expert with low weight
        for _ in range(5):
            update_weight(WeightUpdate(
                expert_id=expert_low,
                expert_version=1,
                context_key="repo:general:medium",
                normalized_weight=-1.0,
            ))

        results = query_weights(WeightQuery(context_key="repo:general:medium"))
        assert len(results) == 2
        assert results[0].expert_id == expert_high  # Higher weight first


class TestRouterConvenienceFunctions:
    """Test Router convenience query functions."""

    def test_get_expert_weights_for_router(self) -> None:
        expert_id = uuid4()

        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="repo1:general:medium",
            normalized_weight=0.5,
        ))
        update_weight(WeightUpdate(
            expert_id=expert_id,
            expert_version=1,
            context_key="repo2:security:high",
            normalized_weight=0.8,
        ))

        results = get_expert_weights_for_router(expert_id)
        assert len(results) == 2

    def test_get_best_experts_for_context(self) -> None:
        expert_1 = uuid4()
        expert_2 = uuid4()
        context = "repo:general:medium"

        for _ in range(5):
            update_weight(WeightUpdate(
                expert_id=expert_1,
                expert_version=1,
                context_key=context,
                normalized_weight=1.0,
            ))
            update_weight(WeightUpdate(
                expert_id=expert_2,
                expert_version=1,
                context_key=context,
                normalized_weight=0.5,
            ))

        results = get_best_experts_for_context(context, limit=1)
        assert len(results) == 1
        assert results[0].expert_id == expert_1  # Higher weight


class TestGetAllWeights:
    """Test getting all weights for admin UI."""

    def test_get_all_weights_returns_all(self) -> None:
        expert_1 = uuid4()
        expert_2 = uuid4()

        update_weight(WeightUpdate(
            expert_id=expert_1,
            expert_version=1,
            context_key="repo:general:medium",
            normalized_weight=0.5,
        ))
        update_weight(WeightUpdate(
            expert_id=expert_2,
            expert_version=1,
            context_key="repo:security:high",
            normalized_weight=0.8,
        ))

        all_weights = get_all_weights()
        assert len(all_weights) == 2
