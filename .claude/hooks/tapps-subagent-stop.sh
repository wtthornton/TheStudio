#!/usr/bin/env bash
# SubagentStop hook: Remind parent to validate subagent modifications
echo "Subagent completed. If Python files were modified, run tapps_quick_check on each changed file."
exit 0
