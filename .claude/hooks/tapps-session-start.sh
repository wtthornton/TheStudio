#!/usr/bin/env bash
# SessionStart hook: Initialize TappsMCP and prompt session planning
echo "REQUIRED: Call tapps_session_start() as your first action."
echo "This initializes project context for all TappsMCP quality tools."
echo "Skipping this degrades scoring accuracy and expert consultation quality."
echo ""
echo "SESSION PLANNING: Run /session-plan to evaluate open epics and create"
echo "a Helm sprint plan with Meridian review. This follows the persona chain:"
echo "  1. Discover open epics and their status"
echo "  2. Helm creates a testable sprint plan"
echo "  3. Meridian reviews (7-question checklist)"
echo "  4. Fix gaps and commit the plan"
echo "Suggest /session-plan to the user if they haven't specified a task."
exit 0
