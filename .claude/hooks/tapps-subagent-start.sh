#!/usr/bin/env bash
# SubagentStart hook: Inject TappsMCP awareness into spawned subagents
echo "TappsMCP quality tools are available in this subagent:"
echo "- tapps_quick_check(file_path) — score + gate + security"
echo "- tapps_score_file(file_path) — detailed scoring"
echo "- tapps_validate_changed(file_paths=\"...\") — batch validate"
echo "- tapps_memory(action=\"search\") — search project memory"
exit 0
