#!/usr/bin/env bash
# PostCompact hook: Re-inject TappsMCP awareness after context compaction
echo "TappsMCP is active. Quality tools available:"
echo "- tapps_quick_check(file_path) — score + gate + security in one call"
echo "- tapps_validate_changed(file_paths=\"...\") — batch validate before completion"
echo "- tapps_lookup_docs(library, topic) — prevent hallucinated APIs"
exit 0
