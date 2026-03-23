"""Progressive context loading for large fix plans (CLI parity).

Trims fix_plan-style markdown to the active epic section plus the next N
unchecked ``- [ ]`` items, reducing prompt tokens for multi-epic plans.
"""

from __future__ import annotations

import re


def estimate_tokens(text: str, chars_per_token: int = 4) -> int:
    """Rough token estimate using a character heuristic (CLI-style)."""
    if chars_per_token < 1:
        chars_per_token = 4
    stripped = text.replace("\r\n", "\n")
    return max(0, (len(stripped) + chars_per_token - 1) // chars_per_token)


_SECTION_HEADING = re.compile(r"^##\s+.+$", re.MULTILINE)
_UNCHECKED = re.compile(r"^(\s*)- \[ \]\s+(.*)$", re.MULTILINE)


def build_progressive_context(plan: str, max_items: int = 10) -> str:
    """Return trimmed plan: active ``##`` section + up to *max_items* unchecked tasks.

    Chooses the last ``##`` section that still contains a ``- [ ]`` item; if none
    do, uses the last section. Elides other sections with short marker lines.
    """
    if not plan.strip():
        return plan

    max_items = max(1, max_items)
    lines = plan.splitlines(keepends=True)
    headings: list[int] = []
    for i, line in enumerate(lines):
        if _SECTION_HEADING.match(line.rstrip("\n")):
            headings.append(i)

    if not headings:
        return _trim_unchecked_only(plan, max_items)

    # Pick section: prefer last section that still has unchecked items.
    chosen_idx = len(headings) - 1
    for idx in range(len(headings) - 1, -1, -1):
        start = headings[idx]
        end = headings[idx + 1] if idx + 1 < len(headings) else len(lines)
        if _UNCHECKED.search("".join(lines[start:end])):
            chosen_idx = idx
            break

    start = headings[chosen_idx]
    end = headings[chosen_idx + 1] if chosen_idx + 1 < len(headings) else len(lines)
    section = "".join(lines[start:end])
    trimmed = _limit_unchecked_in_text(section, max_items)

    out: list[str] = []
    if start > 0:
        out.append("(Earlier fix_plan sections omitted for context — see repo for full plan.)\n\n")
    out.append(trimmed.rstrip() + "\n")
    if end < len(lines):
        out.append("\n(Later fix_plan sections omitted.)\n")
    return "".join(out)


def _trim_unchecked_only(plan: str, max_items: int) -> str:
    matches = list(_UNCHECKED.finditer(plan))
    if len(matches) <= max_items:
        return plan
    last_end = 0
    chunks: list[str] = []
    for m in matches[:max_items]:
        chunks.append(plan[last_end : m.end()])
        last_end = m.end()
    skipped = len(matches) - max_items
    return (
        "".join(chunks) + f"\n({skipped} additional unchecked items omitted.)\n" + plan[last_end:]
    )


def _limit_unchecked_in_text(section: str, max_items: int) -> str:
    matches = list(_UNCHECKED.finditer(section))
    if len(matches) <= max_items:
        return section
    cutoff = matches[max_items].start()
    skipped = len(matches) - max_items
    return section[:cutoff].rstrip() + f"\n\n({skipped} unchecked items omitted in this section.)\n"
