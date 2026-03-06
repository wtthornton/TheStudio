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

# Standard span attribute keys
ATTR_CORRELATION_ID = "thestudio.correlation_id"
ATTR_TASKPACKET_ID = "thestudio.taskpacket_id"
ATTR_REPO = "thestudio.repo"
ATTR_STATUS = "thestudio.status"
ATTR_OUTCOME = "thestudio.outcome"
