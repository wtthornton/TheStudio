#!/usr/bin/env bash
# SessionStart hook: Remind agent to initialize TappsMCP
echo "REQUIRED: Call tapps_session_start() as your first action."
echo "This initializes project context for all TappsMCP quality tools."
echo "Skipping this degrades scoring accuracy and expert consultation quality."
exit 0
