"""Expert directory scanner — discovers file-based expert definitions.

Scans immediate subdirectories of a base path for EXPERT.md manifests,
parses them into ExpertManifest objects, and collects supporting files.

Architecture reference: docs/epics/stories/story-26.2-expert-directory-scanner.md
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.experts.manifest import ExpertManifest, ManifestParseError, parse_expert_manifest

logger = logging.getLogger(__name__)

EXPERT_FILENAME = "EXPERT.md"
SUPPORTING_EXTENSIONS = {".md", ".json", ".yaml", ".yml"}


@dataclass
class SupportingFile:
    """A file found alongside EXPERT.md in an expert directory."""

    relative_path: str
    content: str


@dataclass
class ScannedExpert:
    """An expert discovered by the directory scanner."""

    manifest: ExpertManifest
    directory: Path
    supporting_files: list[SupportingFile] = field(default_factory=list)


@dataclass
class ScanError:
    """A directory that failed to parse during scanning."""

    directory: Path
    error: str


@dataclass
class ScanResult:
    """Result of scanning a base directory for expert definitions."""

    experts: list[ScannedExpert] = field(default_factory=list)
    errors: list[ScanError] = field(default_factory=list)


def _collect_supporting_files(directory: Path) -> list[SupportingFile]:
    """Collect supporting files from an expert directory.

    Includes .md (except EXPERT.md), .json, .yaml, .yml files.
    Non-recursive — only files directly in the directory.
    """
    supporting: list[SupportingFile] = []
    for f in sorted(directory.iterdir()):
        if not f.is_file():
            continue
        if f.name == EXPERT_FILENAME:
            continue
        if f.suffix.lower() not in SUPPORTING_EXTENSIONS:
            continue
        content = f.read_text(encoding="utf-8")
        supporting.append(SupportingFile(relative_path=f.name, content=content))
    return supporting


def scan_expert_directories(base_path: Path) -> ScanResult:
    """Scan a base directory for expert definitions.

    Performs a shallow scan of immediate subdirectories. Each subdirectory
    with a valid EXPERT.md is parsed into a ScannedExpert. Invalid manifests
    are recorded as errors. Directories without EXPERT.md are skipped.

    Args:
        base_path: Directory containing expert subdirectories.

    Returns:
        ScanResult with discovered experts and any errors.

    Raises:
        ValueError: If base_path does not exist or is not a directory.
    """
    if not base_path.exists():
        raise ValueError(f"Base path does not exist: {base_path}")
    if not base_path.is_dir():
        raise ValueError(f"Base path is not a directory: {base_path}")

    subdirs = sorted(d for d in base_path.iterdir() if d.is_dir())
    logger.info(
        "Scanning expert directories",
        extra={"base_path": str(base_path), "subdirectory_count": len(subdirs)},
    )

    result = ScanResult()
    seen_names: dict[str, Path] = {}

    for subdir in subdirs:
        expert_file = subdir / EXPERT_FILENAME
        if not expert_file.exists():
            logger.info(
                "Skipping directory — no EXPERT.md",
                extra={"directory": str(subdir)},
            )
            continue

        try:
            manifest = parse_expert_manifest(expert_file)
        except ManifestParseError as e:
            logger.warning(
                "Skipping directory — invalid manifest",
                extra={"directory": str(subdir), "error": e.detail},
            )
            result.errors.append(ScanError(directory=subdir, error=e.detail))
            continue

        # Check for duplicate names
        if manifest.name in seen_names:
            logger.warning(
                "Duplicate expert name",
                extra={
                    "expert_name": manifest.name,
                    "directory_1": str(seen_names[manifest.name]),
                    "directory_2": str(subdir),
                },
            )
            result.errors.append(
                ScanError(
                    directory=subdir,
                    error=f"Duplicate expert name '{manifest.name}' "
                    f"(also in {seen_names[manifest.name].name})",
                )
            )
            continue

        # Validate context_files references exist
        context_error = False
        for ctx_path in manifest.context_files:
            ctx_file = subdir / ctx_path
            if not ctx_file.is_file():
                result.errors.append(
                    ScanError(
                        directory=subdir,
                        error=f"Referenced context file not found: {ctx_path}",
                    )
                )
                context_error = True
        if context_error:
            continue

        supporting = _collect_supporting_files(subdir)
        seen_names[manifest.name] = subdir

        logger.info(
            "Parsed expert manifest",
            extra={"expert_name": manifest.name, "version_hash": manifest.version_hash},
        )

        result.experts.append(
            ScannedExpert(
                manifest=manifest,
                directory=subdir,
                supporting_files=supporting,
            )
        )

    return result
