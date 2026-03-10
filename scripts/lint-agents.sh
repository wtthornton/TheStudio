#!/usr/bin/env bash
# lint-agents.sh — Validate agent and persona markdown files
# Checks: YAML frontmatter, required fields, body sections, content length
# Exit codes: 0 = clean or warnings only, 1 = errors found
set -euo pipefail

ERRORS=0
WARNINGS=0
ERROR_MSGS=()
WARN_MSGS=()

REQUIRED_FIELDS=("name" "description")
RECOMMENDED_FIELDS=("tools" "model" "maturity")
# Section detection: look for headings containing these keywords (case-insensitive)
RECOMMENDED_SECTIONS=("voice|tone|communication|style" "scope|coverage|pipeline|stage" "role|identity|mission|job")

add_error() {
    ERROR_MSGS+=("ERROR $1: $2")
    ((ERRORS++)) || true
}

add_warn() {
    WARN_MSGS+=("WARN  $1: $2")
    ((WARNINGS++)) || true
}

lint_file() {
    local file="$1"
    local basename
    basename=$(basename "$file")

    # Skip non-markdown files
    if [[ ! "$file" == *.md ]]; then
        return
    fi

    # Check frontmatter exists (file must start with ---)
    local first_line
    first_line=$(head -n 1 "$file")
    if [[ "$first_line" != "---" ]]; then
        add_error "$basename" "No YAML frontmatter (file must start with ---)"
        return
    fi

    # Extract frontmatter (between first and second ---)
    local frontmatter
    frontmatter=$(awk 'BEGIN{found=0} /^---$/{found++; if(found==2) exit; next} found==1{print}' "$file")

    if [[ -z "$frontmatter" ]]; then
        add_error "$basename" "Empty or malformed YAML frontmatter"
        return
    fi

    # Validate YAML frontmatter is parseable
    if ! echo "$frontmatter" | python -c "import sys, yaml; yaml.safe_load(sys.stdin.read())" 2>/dev/null; then
        add_error "$basename" "YAML frontmatter is not valid YAML"
        return
    fi

    # Check required fields
    for field in "${REQUIRED_FIELDS[@]}"; do
        if ! echo "$frontmatter" | grep -qE "^${field}:"; then
            add_error "$basename" "Missing required field: ${field}"
        fi
    done

    # Check recommended fields
    for field in "${RECOMMENDED_FIELDS[@]}"; do
        if ! echo "$frontmatter" | grep -qE "^${field}:"; then
            add_warn "$basename" "Missing recommended field: ${field}"
        fi
    done

    # Extract body (everything after second ---)
    local body
    body=$(awk 'BEGIN{found=0} /^---$/{found++; next} found>=2{print}' "$file")

    # Check body has meaningful content (>50 words)
    local word_count
    word_count=$(echo "$body" | wc -w | tr -d ' ')
    if [[ "$word_count" -lt 50 ]]; then
        add_error "$basename" "Body has only ${word_count} words (minimum 50 required)"
    fi

    # Check recommended body sections (by heading keywords)
    for section_pattern in "${RECOMMENDED_SECTIONS[@]}"; do
        if ! echo "$body" | grep -qiE "^#+.*($section_pattern)"; then
            # Also check for bold text patterns like **Role:** or **Voice:**
            if ! echo "$body" | grep -qiE "^\*\*.*($section_pattern)"; then
                # Also check for the keyword appearing in the first paragraph (for files without headings)
                local first_para
                first_para=$(echo "$body" | head -n 5)
                if ! echo "$first_para" | grep -qiE "($section_pattern)"; then
                    add_warn "$basename" "Missing recommended section matching: ${section_pattern}"
                fi
            fi
        fi
    done
}

# Determine files to lint
FILES=()
if [[ $# -gt 0 ]]; then
    # Lint specific files passed as arguments
    FILES=("$@")
else
    # Default: scan agent and persona directories
    for f in .claude/agents/*.md; do
        [[ -f "$f" ]] && FILES+=("$f")
    done
    # Only lint the three core persona files (not reference docs like TEAM.md, TRAINING.md)
    for f in thestudioarc/personas/saga-epic-creator.md \
             thestudioarc/personas/meridian-vp-success.md \
             thestudioarc/personas/helm-planner-dev-manager.md; do
        [[ -f "$f" ]] && FILES+=("$f")
    done
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No files to lint."
    exit 0
fi

# Lint each file
for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        lint_file "$file"
    else
        add_error "$file" "File not found"
    fi
done

# Print results
for msg in "${ERROR_MSGS[@]+"${ERROR_MSGS[@]}"}"; do
    echo "$msg"
done
for msg in "${WARN_MSGS[@]+"${WARN_MSGS[@]}"}"; do
    echo "$msg"
done

echo ""
echo "Summary: ${#FILES[@]} files checked, ${ERRORS} errors, ${WARNINGS} warnings"

if [[ $ERRORS -gt 0 ]]; then
    exit 1
else
    exit 0
fi
