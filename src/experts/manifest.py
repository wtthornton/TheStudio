"""Expert manifest parsing — EXPERT.md files with YAML frontmatter.

Parses file-based expert definitions into validated ExpertManifest models.
Each EXPERT.md has YAML frontmatter (identity, class, capabilities) and
a markdown body (system prompt template).

Architecture reference: docs/epics/epic-26-file-based-expert-packaging.md
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from src.experts.expert import ExpertClass, ExpertCreate, TrustTier

logger = logging.getLogger(__name__)


class ManifestParseError(Exception):
    """Raised when an EXPERT.md file cannot be parsed."""

    def __init__(self, file_path: Path, detail: str) -> None:
        self.file_path = file_path
        self.detail = detail
        super().__init__(f"{file_path}: {detail}")


def compute_version_hash(content: str) -> str:
    """Compute SHA-256 hash of EXPERT.md content for version tracking."""
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ExpertManifest(BaseModel):
    """Validated representation of an EXPERT.md file."""

    name: str
    expert_class: ExpertClass = Field(alias="class")
    capability_tags: list[str]
    description: str
    trust_tier: TrustTier = TrustTier.SHADOW
    constraints: list[str] = Field(default_factory=list)
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    context_files: list[str] = Field(default_factory=list)
    system_prompt_template: str = ""
    version_hash: str = ""
    source_path: Path = Path(".")

    model_config = {"populate_by_name": True}

    @field_validator("capability_tags")
    @classmethod
    def capability_tags_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("capability_tags must not be empty")
        return v


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split EXPERT.md content into YAML frontmatter and markdown body.

    Frontmatter is delimited by --- on its own line. Content before the
    first --- is ignored. Content after the second --- is the body.
    """
    lines = content.split("\n")
    fence_indices: list[int] = []
    for i, line in enumerate(lines):
        if line.strip() == "---":
            fence_indices.append(i)
            if len(fence_indices) == 2:
                break

    if len(fence_indices) < 2:
        raise ValueError("EXPERT.md must contain YAML frontmatter delimited by ---")

    frontmatter = "\n".join(lines[fence_indices[0] + 1 : fence_indices[1]])
    body = "\n".join(lines[fence_indices[1] + 1 :]).strip()
    return frontmatter, body


def parse_expert_manifest(file_path: Path) -> ExpertManifest:
    """Parse an EXPERT.md file into a validated ExpertManifest.

    Args:
        file_path: Absolute or relative path to the EXPERT.md file.

    Returns:
        Validated ExpertManifest with computed version_hash and source_path.

    Raises:
        ManifestParseError: If the file cannot be read, parsed, or validated.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ManifestParseError(file_path, f"cannot read file: {e}") from e

    try:
        frontmatter_str, body = _split_frontmatter(content)
    except ValueError as e:
        raise ManifestParseError(file_path, str(e)) from e

    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        raise ManifestParseError(file_path, f"invalid YAML: {e}") from e

    if not isinstance(frontmatter, dict):
        raise ManifestParseError(file_path, "YAML frontmatter must be a mapping")

    frontmatter["system_prompt_template"] = body
    frontmatter["version_hash"] = compute_version_hash(content)
    frontmatter["source_path"] = file_path.resolve()

    try:
        return ExpertManifest.model_validate(frontmatter)
    except Exception as e:
        raise ManifestParseError(file_path, f"validation failed: {e}") from e


def manifest_to_expert_create(manifest: ExpertManifest) -> ExpertCreate:
    """Convert an ExpertManifest to an ExpertCreate for database registration.

    Maps manifest fields to ExpertCreate per Epic 26 Appendix B.
    The definition dict stores scope_boundaries, system_prompt_template,
    context_files data, and version_hash for change detection.
    """
    return ExpertCreate(
        name=manifest.name,
        expert_class=manifest.expert_class,
        capability_tags=manifest.capability_tags,
        scope_description=manifest.description,
        tool_policy=manifest.tool_policy,
        trust_tier=manifest.trust_tier,
        definition={
            "scope_boundaries": manifest.constraints,
            "system_prompt_template": manifest.system_prompt_template,
            "context_files": {},  # populated by scanner when context file contents are loaded
            "version_hash": manifest.version_hash,
            "source_path": str(manifest.source_path),
        },
    )
