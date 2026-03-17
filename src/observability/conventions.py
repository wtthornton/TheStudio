"""Span naming conventions and standard attribute keys for TheStudio."""

# Span name patterns: {component}.{action}
SPAN_INGRESS_RECEIVE = "ingress.webhook_receive"
SPAN_CONTEXT_ENRICH = "context.enrich"
SPAN_INTENT_BUILD = "intent.build"
SPAN_AGENT_IMPLEMENT = "agent.implement"
SPAN_AGENT_LOOPBACK = "agent.loopback"
SPAN_VERIFICATION_RUN = "verification.run"
SPAN_VERIFICATION_CHECK = "verification.check"
SPAN_PUBLISHER_PUBLISH = "publisher.publish"
SPAN_INTENT_REFINE = "intent.refine"
SPAN_OUTCOME_INGEST = "outcome.ingest"

# Container lifecycle spans (Epic 25 Story 25.7)
SPAN_CONTAINER_LIFECYCLE = "container.lifecycle"
SPAN_CONTAINER_LAUNCH = "container.launch"
SPAN_CONTAINER_WAIT = "container.wait"
SPAN_CONTAINER_COLLECT = "container.collect_results"
SPAN_CONTAINER_CLEANUP = "container.cleanup"

# Container span attribute keys
ATTR_CONTAINER_ID = "thestudio.container.id"
ATTR_CONTAINER_IMAGE = "thestudio.container.image"
ATTR_CONTAINER_CPU_LIMIT = "thestudio.container.cpu_limit"
ATTR_CONTAINER_MEMORY_MB = "thestudio.container.memory_mb"
ATTR_CONTAINER_TIMEOUT = "thestudio.container.timeout_seconds"
ATTR_CONTAINER_EXIT_CODE = "thestudio.container.exit_code"
ATTR_CONTAINER_OOM_KILLED = "thestudio.container.oom_killed"
ATTR_CONTAINER_LAUNCH_MS = "thestudio.container.launch_ms"
ATTR_CONTAINER_WAIT_MS = "thestudio.container.wait_ms"
ATTR_CONTAINER_TOTAL_MS = "thestudio.container.total_ms"
ATTR_CONTAINER_TIMED_OUT = "thestudio.container.timed_out"
ATTR_REPO_TIER = "thestudio.repo_tier"

# Approval chat spans (Epic 24 Story 24.6)
SPAN_APPROVAL_REVIEW_CONTEXT = "approval.review_context"
SPAN_APPROVAL_CHAT_MESSAGE = "approval.chat_message"
SPAN_APPROVAL_LLM_RESPONSE = "approval.llm_response"
SPAN_APPROVAL_APPROVE = "approval.approve"
SPAN_APPROVAL_REJECT = "approval.reject"

# Standard span attribute keys
ATTR_CORRELATION_ID = "thestudio.correlation_id"
ATTR_TASKPACKET_ID = "thestudio.taskpacket_id"
ATTR_REPO = "thestudio.repo"
ATTR_STATUS = "thestudio.status"
ATTR_OUTCOME = "thestudio.outcome"
ATTR_AUTO_MERGE_ENABLED = "thestudio.auto_merge_enabled"
ATTR_MERGE_METHOD = "thestudio.merge_method"
ATTR_EXECUTE_TIER_ACTIVE = "thestudio.execute_tier_active"
