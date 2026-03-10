#!/usr/bin/env python3
"""agent-catalog.py — Generate a summary table of all agents from frontmatter.

Reads YAML frontmatter from .claude/agents/*.md and produces a markdown table
or JSON output showing agent name, description, model, maturity, last validated,
and coverage.

Usage:
    python scripts/agent-catalog.py          # Markdown table to stdout
    python scripts/agent-catalog.py --json   # JSON output to stdout
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def parse_frontmatter(file_path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def collect_agents(root: Path) -> list[dict]:
    """Collect agent metadata from all .claude/agents/*.md files."""
    agents_dir = root / ".claude" / "agents"
    agents = []
    for md_file in sorted(agents_dir.glob("*.md")):
        fm = parse_frontmatter(md_file)
        if fm is None:
            continue
        # Flatten description (remove newlines from block scalars)
        desc = fm.get("description", "")
        if isinstance(desc, str):
            desc = " ".join(desc.split())
        # Truncate description for table readability
        short_desc = desc[:60] + "..." if len(desc) > 60 else desc
        agents.append({
            "name": fm.get("name", md_file.stem),
            "description": short_desc,
            "full_description": desc,
            "model": fm.get("model", "-"),
            "maturity": fm.get("maturity", "-"),
            "last_validated": fm.get("last_validated", "-"),
            "coverage": fm.get("coverage", "-"),
            "file": str(md_file.relative_to(root)),
        })
    return agents


def format_markdown(agents: list[dict]) -> str:
    """Format agents as a markdown table."""
    lines = [
        "# Agent Catalog",
        "",
        f"Generated from `.claude/agents/*.md` frontmatter. {len(agents)} agents total.",
        "",
        "| Name | Model | Maturity | Last Validated | Coverage |",
        "|------|-------|----------|----------------|----------|",
    ]
    for a in agents:
        lines.append(
            f"| {a['name']} | {a['model']} | {a['maturity']} "
            f"| {a['last_validated']} | {a['coverage']} |"
        )
    lines.append("")

    # Summary counts
    maturity_counts: dict[str, int] = {}
    for a in agents:
        m = a["maturity"]
        maturity_counts[m] = maturity_counts.get(m, 0) + 1
    lines.append("## Summary")
    lines.append("")
    for tier, count in sorted(maturity_counts.items()):
        lines.append(f"- **{tier}**: {count} agent(s)")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    agents = collect_agents(root)

    if not agents:
        print("No agent files found in .claude/agents/")
        return 1

    if "--json" in sys.argv:
        print(json.dumps(agents, indent=2, default=str))
    else:
        print(format_markdown(agents))

    return 0


if __name__ == "__main__":
    sys.exit(main())
