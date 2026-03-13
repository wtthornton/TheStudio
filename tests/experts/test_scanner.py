"""Tests for expert directory scanner (Story 26.2)."""

from pathlib import Path

import pytest

from src.experts.scanner import scan_expert_directories

# --- Helper to create EXPERT.md files ---

VALID_MANIFEST = """\
---
name: {name}
class: technical
capability_tags:
  - review
description: Expert {name}.
---

System prompt for {name}.
"""


def _write_expert(base: Path, name: str, content: str | None = None) -> Path:
    """Create an expert directory with an EXPERT.md file."""
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "EXPERT.md").write_text(
        content or VALID_MANIFEST.format(name=name), encoding="utf-8"
    )
    return d


class TestScanSingleExpert:
    """Test 1: scan directory with one valid expert."""

    def test_single_valid_expert(self, tmp_path: Path) -> None:
        _write_expert(tmp_path, "alpha")

        result = scan_expert_directories(tmp_path)

        assert len(result.experts) == 1
        assert len(result.errors) == 0
        assert result.experts[0].manifest.name == "alpha"
        assert result.experts[0].directory == tmp_path / "alpha"


class TestScanMultipleExperts:
    """Test 2: scan directory with multiple valid experts."""

    def test_multiple_valid_experts(self, tmp_path: Path) -> None:
        _write_expert(tmp_path, "alpha")
        _write_expert(tmp_path, "beta")

        result = scan_expert_directories(tmp_path)

        assert len(result.experts) == 2
        assert len(result.errors) == 0
        names = {e.manifest.name for e in result.experts}
        assert names == {"alpha", "beta"}


class TestScanEmptyDirectory:
    """Test 3: scan empty directory."""

    def test_empty_base_directory(self, tmp_path: Path) -> None:
        result = scan_expert_directories(tmp_path)

        assert len(result.experts) == 0
        assert len(result.errors) == 0


class TestScanMixedValidInvalid:
    """Test 4: valid experts still load when one has an invalid manifest."""

    def test_invalid_manifest_skipped(self, tmp_path: Path) -> None:
        _write_expert(tmp_path, "good")
        _write_expert(tmp_path, "bad", content="no frontmatter here")

        result = scan_expert_directories(tmp_path)

        assert len(result.experts) == 1
        assert result.experts[0].manifest.name == "good"
        assert len(result.errors) == 1
        assert result.errors[0].directory == tmp_path / "bad"


class TestScanNoExpertMd:
    """Test 5: subdirectory without EXPERT.md is silently skipped."""

    def test_no_expert_md_skipped(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "no-manifest"
        empty_dir.mkdir()
        (empty_dir / "README.md").write_text("Not an expert.", encoding="utf-8")

        result = scan_expert_directories(tmp_path)

        assert len(result.experts) == 0
        assert len(result.errors) == 0


class TestSupportingFiles:
    """Tests 6-8: supporting file collection."""

    def test_supporting_files_collected(self, tmp_path: Path) -> None:
        """Test 6: .md, .json, .yaml, .yml files are collected."""
        d = _write_expert(tmp_path, "alpha")
        (d / "checklist.md").write_text("# Checklist", encoding="utf-8")
        (d / "rules.yaml").write_text("key: value", encoding="utf-8")
        (d / "config.json").write_text("{}", encoding="utf-8")
        (d / "extra.yml").write_text("a: 1", encoding="utf-8")

        result = scan_expert_directories(tmp_path)

        assert len(result.experts) == 1
        files = result.experts[0].supporting_files
        assert len(files) == 4
        names = {f.relative_path for f in files}
        assert names == {"checklist.md", "rules.yaml", "config.json", "extra.yml"}

    def test_expert_md_excluded(self, tmp_path: Path) -> None:
        """Test 7: EXPERT.md is not in supporting files."""
        d = _write_expert(tmp_path, "alpha")
        (d / "other.md").write_text("Other content", encoding="utf-8")

        result = scan_expert_directories(tmp_path)

        files = result.experts[0].supporting_files
        assert len(files) == 1
        assert files[0].relative_path == "other.md"

    def test_non_matching_files_excluded(self, tmp_path: Path) -> None:
        """Test 8: .py, .txt, etc. are not collected."""
        d = _write_expert(tmp_path, "alpha")
        (d / "helper.py").write_text("print('hi')", encoding="utf-8")
        (d / "notes.txt").write_text("notes", encoding="utf-8")
        (d / "image.png").write_bytes(b"\x89PNG")

        result = scan_expert_directories(tmp_path)

        assert len(result.experts[0].supporting_files) == 0


class TestDuplicateNames:
    """Test 9: duplicate expert names across directories."""

    def test_duplicate_names_produce_errors(self, tmp_path: Path) -> None:
        _write_expert(tmp_path, "dir-a", content=VALID_MANIFEST.format(name="same-name"))
        _write_expert(tmp_path, "dir-b", content=VALID_MANIFEST.format(name="same-name"))

        result = scan_expert_directories(tmp_path)

        assert len(result.experts) == 1  # first one kept
        assert len(result.errors) == 1
        assert "Duplicate" in result.errors[0].error
        assert "same-name" in result.errors[0].error


class TestMissingBasePath:
    """Test 10: non-existent base path raises ValueError."""

    def test_nonexistent_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            scan_expert_directories(tmp_path / "nonexistent")

    def test_file_path_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "afile.txt"
        f.write_text("not a directory", encoding="utf-8")

        with pytest.raises(ValueError, match="not a directory"):
            scan_expert_directories(f)


class TestSupportingFileContent:
    """Verify supporting file contents are read correctly."""

    def test_content_is_read(self, tmp_path: Path) -> None:
        d = _write_expert(tmp_path, "alpha")
        (d / "checklist.md").write_text("# Step 1\n- Do thing\n", encoding="utf-8")

        result = scan_expert_directories(tmp_path)

        files = result.experts[0].supporting_files
        assert files[0].content == "# Step 1\n- Do thing\n"
