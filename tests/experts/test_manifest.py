"""Tests for expert manifest parsing (Story 26.1)."""

from pathlib import Path

import pytest

from src.experts.expert import ExpertClass, TrustTier
from src.experts.manifest import (
    ExpertManifest,
    ManifestParseError,
    compute_version_hash,
    manifest_to_expert_create,
    parse_expert_manifest,
)

# --- Fixtures: sample EXPERT.md content ---

FULL_MANIFEST = """\
---
name: security-reviewer
class: security
capability_tags:
  - auth
  - secrets
  - crypto
trust_tier: probation
description: >
  Review code changes for security vulnerabilities.
constraints:
  - Read-only access to repository
  - Must cite OWASP references
tool_policy:
  allowed_suites: [repo_read, analysis]
  read_only: true
context_files:
  - owasp-checklist.md
---

You are a security review expert.

Focus on authentication, secret handling, and injection prevention.
"""

MINIMAL_MANIFEST = """\
---
name: minimal-expert
class: technical
capability_tags:
  - code_quality
description: A minimal expert for testing.
---

Review code for quality.
"""


@pytest.fixture
def tmp_expert_dir(tmp_path: Path) -> Path:
    """Create a temporary expert directory with a full EXPERT.md."""
    expert_dir = tmp_path / "security-reviewer"
    expert_dir.mkdir()
    (expert_dir / "EXPERT.md").write_text(FULL_MANIFEST, encoding="utf-8")
    (expert_dir / "owasp-checklist.md").write_text("# OWASP\n- Check 1\n", encoding="utf-8")
    return expert_dir


@pytest.fixture
def tmp_minimal_dir(tmp_path: Path) -> Path:
    """Create a temporary expert directory with a minimal EXPERT.md."""
    expert_dir = tmp_path / "minimal-expert"
    expert_dir.mkdir()
    (expert_dir / "EXPERT.md").write_text(MINIMAL_MANIFEST, encoding="utf-8")
    return expert_dir


class TestParseExpertManifest:
    """Tests for parse_expert_manifest()."""

    def test_parse_full_manifest(self, tmp_expert_dir: Path) -> None:
        manifest = parse_expert_manifest(tmp_expert_dir / "EXPERT.md")

        assert manifest.name == "security-reviewer"
        assert manifest.expert_class == ExpertClass.SECURITY
        assert manifest.capability_tags == ["auth", "secrets", "crypto"]
        assert manifest.trust_tier == TrustTier.PROBATION
        assert "security vulnerabilities" in manifest.description
        assert manifest.constraints == [
            "Read-only access to repository",
            "Must cite OWASP references",
        ]
        assert manifest.tool_policy == {
            "allowed_suites": ["repo_read", "analysis"],
            "read_only": True,
        }
        assert manifest.context_files == ["owasp-checklist.md"]
        assert "security review expert" in manifest.system_prompt_template
        assert manifest.version_hash  # non-empty
        assert manifest.source_path.name == "EXPERT.md"

    def test_parse_minimal_manifest(self, tmp_minimal_dir: Path) -> None:
        manifest = parse_expert_manifest(tmp_minimal_dir / "EXPERT.md")

        assert manifest.name == "minimal-expert"
        assert manifest.expert_class == ExpertClass.TECHNICAL
        assert manifest.capability_tags == ["code_quality"]
        assert manifest.trust_tier == TrustTier.SHADOW  # default
        assert manifest.constraints == []
        assert manifest.tool_policy == {}
        assert manifest.context_files == []
        assert "Review code for quality" in manifest.system_prompt_template

    def test_reject_missing_name(self, tmp_path: Path) -> None:
        content = """\
---
class: technical
capability_tags:
  - review
description: Missing name field.
---

Body text.
"""
        f = tmp_path / "EXPERT.md"
        f.write_text(content, encoding="utf-8")

        with pytest.raises(ManifestParseError, match="validation failed"):
            parse_expert_manifest(f)

    def test_reject_missing_class(self, tmp_path: Path) -> None:
        content = """\
---
name: no-class
capability_tags:
  - review
description: Missing class field.
---

Body text.
"""
        f = tmp_path / "EXPERT.md"
        f.write_text(content, encoding="utf-8")

        with pytest.raises(ManifestParseError, match="validation failed"):
            parse_expert_manifest(f)

    def test_reject_empty_capability_tags(self, tmp_path: Path) -> None:
        content = """\
---
name: empty-tags
class: technical
capability_tags: []
description: Empty tags.
---

Body text.
"""
        f = tmp_path / "EXPERT.md"
        f.write_text(content, encoding="utf-8")

        with pytest.raises(ManifestParseError, match="validation failed"):
            parse_expert_manifest(f)

    def test_reject_invalid_class(self, tmp_path: Path) -> None:
        content = """\
---
name: bad-class
class: nonexistent
capability_tags:
  - tag
description: Invalid class.
---

Body text.
"""
        f = tmp_path / "EXPERT.md"
        f.write_text(content, encoding="utf-8")

        with pytest.raises(ManifestParseError, match="validation failed"):
            parse_expert_manifest(f)

    def test_reject_invalid_trust_tier(self, tmp_path: Path) -> None:
        content = """\
---
name: bad-tier
class: technical
capability_tags:
  - tag
description: Invalid tier.
trust_tier: ultimate
---

Body text.
"""
        f = tmp_path / "EXPERT.md"
        f.write_text(content, encoding="utf-8")

        with pytest.raises(ManifestParseError, match="validation failed"):
            parse_expert_manifest(f)

    def test_reject_no_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "EXPERT.md"
        f.write_text("Just plain markdown, no frontmatter.", encoding="utf-8")

        with pytest.raises(ManifestParseError, match="frontmatter"):
            parse_expert_manifest(f)

    def test_reject_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestParseError, match="cannot read file"):
            parse_expert_manifest(tmp_path / "nonexistent.md")

    def test_error_includes_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_text("no frontmatter", encoding="utf-8")

        with pytest.raises(ManifestParseError) as exc_info:
            parse_expert_manifest(f)

        assert exc_info.value.file_path == f
        assert "bad.md" in str(exc_info.value)


class TestVersionHash:
    """Tests for compute_version_hash()."""

    def test_hash_stability(self) -> None:
        content = "same content"
        assert compute_version_hash(content) == compute_version_hash(content)

    def test_hash_sensitivity(self) -> None:
        assert compute_version_hash("content A") != compute_version_hash("content B")

    def test_cross_platform_line_endings(self) -> None:
        unix = "line1\nline2\nline3"
        windows = "line1\r\nline2\r\nline3"
        mac_classic = "line1\rline2\rline3"

        assert compute_version_hash(unix) == compute_version_hash(windows)
        assert compute_version_hash(unix) == compute_version_hash(mac_classic)

    def test_hash_changes_with_content(self, tmp_expert_dir: Path) -> None:
        f = tmp_expert_dir / "EXPERT.md"
        m1 = parse_expert_manifest(f)

        # Modify the file
        content = f.read_text(encoding="utf-8")
        f.write_text(content + "\nExtra line.", encoding="utf-8")
        m2 = parse_expert_manifest(f)

        assert m1.version_hash != m2.version_hash


class TestManifestToExpertCreate:
    """Tests for manifest_to_expert_create()."""

    def test_maps_all_fields(self, tmp_expert_dir: Path) -> None:
        manifest = parse_expert_manifest(tmp_expert_dir / "EXPERT.md")
        ec = manifest_to_expert_create(manifest)

        assert ec.name == "security-reviewer"
        assert ec.expert_class == ExpertClass.SECURITY
        assert ec.capability_tags == ["auth", "secrets", "crypto"]
        assert "security vulnerabilities" in ec.scope_description
        assert ec.tool_policy == {
            "allowed_suites": ["repo_read", "analysis"],
            "read_only": True,
        }
        assert ec.trust_tier == TrustTier.PROBATION

        # definition dict
        assert ec.definition["_version_hash"] == manifest.version_hash
        assert ec.definition["scope_boundaries"] == manifest.constraints
        assert "security review expert" in ec.definition["system_prompt_template"]
        assert ec.definition["context_files"] == {}  # populated later by scanner
        assert "_source_path" in ec.definition

    def test_minimal_manifest_mapping(self, tmp_minimal_dir: Path) -> None:
        manifest = parse_expert_manifest(tmp_minimal_dir / "EXPERT.md")
        ec = manifest_to_expert_create(manifest)

        assert ec.name == "minimal-expert"
        assert ec.expert_class == ExpertClass.TECHNICAL
        assert ec.trust_tier == TrustTier.SHADOW
        assert ec.definition["scope_boundaries"] == []
        assert ec.definition["context_files"] == {}
