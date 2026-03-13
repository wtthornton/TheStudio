"""Tests for expert context file integration (Story 26.6)."""

from pathlib import Path

import pytest

from src.assembler.assembler import format_expert_context
from src.experts.manifest import ManifestParseError, parse_expert_manifest
from src.experts.scanner import scan_expert_directories

MANIFEST_WITH_CONTEXT = """\
---
name: ctx-expert
class: technical
capability_tags:
  - review
description: Expert with context files.
context_files:
  - checklist.md
---

System prompt.
"""

MANIFEST_NO_CONTEXT = """\
---
name: plain-expert
class: technical
capability_tags:
  - review
description: Expert without context files.
---

System prompt.
"""


def _write_expert_with_context(
    base: Path, name: str, manifest: str, context_files: dict[str, str] | None = None
) -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "EXPERT.md").write_text(manifest, encoding="utf-8")
    if context_files:
        for fname, content in context_files.items():
            (d / fname).write_text(content, encoding="utf-8")
    return d


class TestManifestContextValidation:
    """Tests for path validation in context_files."""

    def test_valid_context_files(self, tmp_path: Path) -> None:
        """Test 1: manifest with existing context files parses OK."""
        d = _write_expert_with_context(
            tmp_path, "good", MANIFEST_WITH_CONTEXT,
            {"checklist.md": "# Checklist\n- Item 1\n"},
        )
        manifest = parse_expert_manifest(d / "EXPERT.md")
        assert manifest.context_files == ["checklist.md"]

    def test_absolute_path_rejected(self, tmp_path: Path) -> None:
        """Test 3: absolute path in context_files fails validation."""
        content = """\
---
name: abs-path
class: technical
capability_tags:
  - review
description: Bad paths.
context_files:
  - /etc/passwd
---

Body.
"""
        f = tmp_path / "EXPERT.md"
        f.write_text(content, encoding="utf-8")
        with pytest.raises(ManifestParseError, match="validation failed"):
            parse_expert_manifest(f)

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Test 4: .. path traversal in context_files fails validation."""
        content = """\
---
name: traversal
class: technical
capability_tags:
  - review
description: Bad paths.
context_files:
  - ../../secrets.md
---

Body.
"""
        f = tmp_path / "EXPERT.md"
        f.write_text(content, encoding="utf-8")
        with pytest.raises(ManifestParseError, match="validation failed"):
            parse_expert_manifest(f)


class TestScannerContextValidation:
    """Tests for scanner context file existence checks."""

    def test_missing_context_file_produces_error(self, tmp_path: Path) -> None:
        """Test 2: manifest referencing non-existent file produces scan error."""
        _write_expert_with_context(
            tmp_path, "missing-ctx", MANIFEST_WITH_CONTEXT,
            # Don't create checklist.md
        )
        result = scan_expert_directories(tmp_path)
        assert len(result.experts) == 0
        assert len(result.errors) == 1
        assert "context file not found" in result.errors[0].error.lower()

    def test_existing_context_file_passes(self, tmp_path: Path) -> None:
        """Context files that exist pass scanner validation."""
        _write_expert_with_context(
            tmp_path, "good-ctx", MANIFEST_WITH_CONTEXT,
            {"checklist.md": "# Checklist content"},
        )
        result = scan_expert_directories(tmp_path)
        assert len(result.experts) == 1
        assert len(result.errors) == 0


class TestContextInDefinition:
    """Test 5: context file contents stored in definition."""

    def test_context_stored_in_supporting_files(self, tmp_path: Path) -> None:
        _write_expert_with_context(
            tmp_path, "ctx-expert", MANIFEST_WITH_CONTEXT,
            {"checklist.md": "# Step 1\n- Do thing\n"},
        )
        result = scan_expert_directories(tmp_path)
        expert = result.experts[0]

        # Supporting files should include checklist.md
        sf_names = {sf.relative_path for sf in expert.supporting_files}
        assert "checklist.md" in sf_names

        # Content should be readable
        checklist = next(
            sf for sf in expert.supporting_files
            if sf.relative_path == "checklist.md"
        )
        assert "Step 1" in checklist.content


class TestAssemblerContextFormatting:
    """Tests 6-7: Assembler context file injection."""

    def test_format_expert_context_with_files(self) -> None:
        """Test 6: context files are formatted with delimiters."""
        definition = {
            "context_files": {
                "checklist.md": "# Checklist\n- Item 1\n",
                "rules.md": "# Rules\n- Rule A\n",
            }
        }
        formatted = format_expert_context(definition)
        assert "--- Expert Context: checklist.md ---" in formatted
        assert "# Checklist" in formatted
        assert "--- End Expert Context ---" in formatted
        assert "--- Expert Context: rules.md ---" in formatted

    def test_format_expert_context_no_files(self) -> None:
        """Test 7: expert without context_files returns empty string."""
        assert format_expert_context({}) == ""
        assert format_expert_context({"context_files": {}}) == ""

    def test_format_expert_context_non_dict(self) -> None:
        """Handles legacy empty list gracefully."""
        assert format_expert_context({"context_files": []}) == ""


class TestMultipleContextFiles:
    """Test 8: multiple context files."""

    def test_multiple_files_collected(self, tmp_path: Path) -> None:
        content = """\
---
name: multi-ctx
class: technical
capability_tags:
  - review
description: Multi context.
context_files:
  - a.md
  - b.yaml
---

System prompt.
"""
        _write_expert_with_context(
            tmp_path, "multi-ctx", content,
            {"a.md": "# File A", "b.yaml": "key: value"},
        )
        result = scan_expert_directories(tmp_path)
        assert len(result.experts) == 1
        sf_names = {sf.relative_path for sf in result.experts[0].supporting_files}
        assert "a.md" in sf_names
        assert "b.yaml" in sf_names


class TestRealSecurityReviewer:
    """Verify the security-reviewer expert with its context file."""

    def test_security_reviewer_has_context(self) -> None:
        experts_dir = Path(__file__).resolve().parent.parent.parent / "experts"
        result = scan_expert_directories(experts_dir)
        sec = next(
            e for e in result.experts
            if e.manifest.name == "security-review"
        )
        assert "owasp-top-10-checklist.md" in sec.manifest.context_files
        owasp = next(
            sf for sf in sec.supporting_files
            if sf.relative_path == "owasp-top-10-checklist.md"
        )
        assert "OWASP" in owasp.content
