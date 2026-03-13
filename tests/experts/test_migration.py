"""Tests for seed expert migration to file-based format (Story 26.4)."""

from pathlib import Path

import pytest

from src.experts.manifest import manifest_to_expert_create, parse_expert_manifest
from src.experts.scanner import scan_expert_directories
from src.experts.seed import SEED_EXPERTS

# Path to the experts directory at project root
EXPERTS_DIR = Path(__file__).resolve().parent.parent.parent / "experts"

# Map seed expert names to their directory names
SEED_DIR_MAP = {
    "security-review": "security-reviewer",
    "qa-validation": "qa-validation",
    "technical-review": "technical-review",
    "compliance-check": "compliance-check",
    "process-quality": "process-quality",
}


class TestExpertDirectoriesExist:
    """Test 1: all 5 expert directories exist with EXPERT.md files."""

    def test_experts_dir_exists(self) -> None:
        assert EXPERTS_DIR.is_dir(), f"experts/ directory not found at {EXPERTS_DIR}"

    @pytest.mark.parametrize("dir_name", SEED_DIR_MAP.values())
    def test_expert_dir_has_manifest(self, dir_name: str) -> None:
        expert_md = EXPERTS_DIR / dir_name / "EXPERT.md"
        assert expert_md.is_file(), f"EXPERT.md not found in experts/{dir_name}/"


class TestManifestsParse:
    """Test 2: each EXPERT.md parses successfully."""

    @pytest.mark.parametrize("dir_name", SEED_DIR_MAP.values())
    def test_manifest_parses(self, dir_name: str) -> None:
        manifest = parse_expert_manifest(EXPERTS_DIR / dir_name / "EXPERT.md")
        assert manifest.name
        assert manifest.expert_class
        assert manifest.capability_tags
        assert manifest.version_hash


class TestFieldsMatchSeed:
    """Test 3: each manifest's fields match the corresponding seed.py entry."""

    @pytest.mark.parametrize(
        "seed_expert",
        SEED_EXPERTS,
        ids=[e.name for e in SEED_EXPERTS],
    )
    def test_fields_match(self, seed_expert) -> None:
        dir_name = SEED_DIR_MAP[seed_expert.name]
        manifest = parse_expert_manifest(EXPERTS_DIR / dir_name / "EXPERT.md")

        assert manifest.name == seed_expert.name
        assert manifest.expert_class == seed_expert.expert_class
        assert set(manifest.capability_tags) == set(seed_expert.capability_tags)
        assert manifest.trust_tier == seed_expert.trust_tier


class TestManifestToExpertCreate:
    """Test 4: manifest_to_expert_create produces equivalent ExpertCreate."""

    @pytest.mark.parametrize(
        "seed_expert",
        SEED_EXPERTS,
        ids=[e.name for e in SEED_EXPERTS],
    )
    def test_expert_create_equivalent(self, seed_expert) -> None:
        dir_name = SEED_DIR_MAP[seed_expert.name]
        manifest = parse_expert_manifest(EXPERTS_DIR / dir_name / "EXPERT.md")
        ec = manifest_to_expert_create(manifest)

        assert ec.name == seed_expert.name
        assert ec.expert_class == seed_expert.expert_class
        assert set(ec.capability_tags) == set(seed_expert.capability_tags)
        assert ec.trust_tier == seed_expert.trust_tier
        assert ec.tool_policy == seed_expert.tool_policy
        # definition has version metadata not in seed
        assert "_version_hash" in ec.definition
        assert "_source_path" in ec.definition


class TestScannerFindsAll:
    """Test 5: scanner discovers all 5 experts."""

    def test_scan_finds_five(self) -> None:
        result = scan_expert_directories(EXPERTS_DIR)

        assert len(result.errors) == 0, f"Scan errors: {result.errors}"
        assert len(result.experts) == 5

        names = {e.manifest.name for e in result.experts}
        expected = {e.name for e in SEED_EXPERTS}
        assert names == expected


class TestToolPolicyMatch:
    """Verify tool_policy is preserved exactly."""

    @pytest.mark.parametrize(
        "seed_expert",
        SEED_EXPERTS,
        ids=[e.name for e in SEED_EXPERTS],
    )
    def test_tool_policy_matches(self, seed_expert) -> None:
        dir_name = SEED_DIR_MAP[seed_expert.name]
        manifest = parse_expert_manifest(EXPERTS_DIR / dir_name / "EXPERT.md")
        assert manifest.tool_policy == seed_expert.tool_policy
