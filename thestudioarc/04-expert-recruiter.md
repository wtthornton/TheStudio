# 04 — Expert Recruiter

## Purpose

The Expert Recruiter manages expert supply for the Agent Plane.
It ensures the system can always obtain qualified domain reasoning when the Expert Router requests a capability.

This component exists so expert creation is controlled, auditable, and safe.
Without a Recruiter, expert creation would be ad hoc and would quickly lead to duplicated experts, tool overreach, and untrustworthy reputation signals.

## Intent

The intent of the Expert Recruiter is to:
- keep the Expert Library coherent as the number of experts grows into the hundreds
- prevent uncontrolled expert sprawl and redundant experts
- create new experts only when needed and only in a safe trust tier
- ensure every expert is created from a repeatable pattern, not invented from scratch
- preserve governance boundaries, especially for compliance and high-risk domains

The Recruiter is responsible for supply. The Router is responsible for selection.

## Plane Placement

Agent Plane: Expert Recruiter Agent

Platform Plane: Expert Library (persistence, versioning, governance enforcement)

## Skills

The Recruiter operates as a skill-pack oriented agent. It must be able to convert capability gaps into a versioned expert definition that is safe to invoke.

Core capabilities:
- capability gap detection and de-duplication
- template selection and specialization
- expert pack construction (behavior, scope, outputs)
- tool policy binding and trust tier assignment
- qualification and probation workflow design
- expert lifecycle management (versioning and retirement)

## Key Inputs

- capability request from Expert Router (domain, subdomain, class, constraints, risk tier)
- TaskPacket context pointers and standards
- Expert Library contents (existing experts, versions, metadata)
- Template catalog (vetted expert patterns)
- governance rules (POLICIES.md and guardrails)

## Key Outputs

- selected existing expert candidate set when available
- newly created expert definition and initial version when missing
- trust tier assignment and eligibility flags
- tool boundary recommendation for the expert
- creation rationale and trace anchors for audit and later evaluation

## Diagram

![Expert Creation Flow](assets/expert-recruiter-creation-flow.svg)

## How new experts are created

The system should never create experts from a blank prompt.
New experts must be created using a controlled pipeline that produces predictable behavior and safe defaults.

### Step 1: Capability request intake

The Recruiter receives a request from the Router that includes:
- required expert class (technical, business, partner, QA, compliance, service)
- required capability tags (domain and subdomain)
- constraints (allowed tools, read only vs write, risk tier)
- reason for gap (no experts found, all candidates ineligible, low confidence)

The Recruiter must normalize the request so it can be matched against the library consistently.

### Step 2: Search and de-duplication

The Recruiter searches the Expert Library to determine whether a suitable expert already exists.
It should look for:
- exact match by class and domain
- close match by subdomain
- a broader expert that can be safely scoped down for this request
- a deprecated expert that should be revived as a new version

If an expert exists but is missing a small capability, the Recruiter should prefer creating a new version of that expert over creating a brand new expert identity.

### Step 3: Template selection

If no suitable expert exists, the Recruiter selects a template from the Template Catalog.
Templates are curated patterns such as:
- Security review expert
- Partner integration expert
- QA validation expert
- Pricing and packaging expert
- Data migration expert
- Service specialist expert

Templates define:
- expected outputs
- common failure modes
- default tool boundaries
- evaluation rubric
- escalation triggers

Template selection rules:
- choose the narrowest template that fits the capability request
- prefer a template that matches the risk tier
- for compliance domains, only use curated compliance templates

### Step 4: Expert pack construction

The Recruiter constructs the expert definition as an expert pack:
- name and description (must be discoverable and unambiguous)
- scope boundaries (what is in scope and out of scope)
- operating procedure (step-by-step)
- expected output structure (recommendations, risks, validations, assumptions)
- edge cases and failure modes
- tool allowlist and denied tools
- trust tier and eligibility flags
- references and pointers to standards or service packs

Important: the pack is written for the Assembler and QA to consume, not for conversational elegance.

### Step 5: Tool policy binding

The Recruiter binds a tool policy to the expert.
Tool access must be minimal by default.

Typical patterns:
- Experts are read only by default
- Experts may call retrieval tools and analysis tools
- Experts should not have repo write tools
- Experts should not have direct publishing tools

High-risk tool boundaries:
- any tool that can change code, publish PRs, or access sensitive systems should be denied for experts unless explicitly approved

### Step 6: Qualification harness

Before registering a new expert as eligible, the Recruiter runs a qualification harness.
This is not deep implementation testing. It is fast safety and usability checks such as:
- the expert produces outputs in the expected structure
- the expert stays within scope and does not request forbidden tools
- the expert includes risks and validations, not only recommendations
- the expert identifies when it is uncertain and requests missing inputs explicitly

If qualification fails, the expert is not registered as eligible.

### Step 7: Trust tier assignment

Newly created experts start in a limited tier:
- shadow: outputs collected but not used automatically
- probation: outputs may influence plans but weight is capped
- trusted: reserved for experts that have proven outcomes over time

Recruiter assigns initial tier and marks promotion rules as owned by the Reputation Engine.

Hard rule:
- compliance experts do not start as trusted
- high-risk domains require curated experts or human escalation triggers

### Step 8: Register and return eligibility

Once qualified, the Recruiter registers the expert in the Expert Library:
- new expert identity or new version
- metadata, policy, and tier
- creation rationale and links to the originating capability request

The Recruiter returns to the Router:
- expert id and version
- tier and eligibility flags
- any warnings or constraints

## Creation guardrails

These guardrails prevent expert sprawl and unsafe behavior.

- Do not create a new expert identity when a version update is sufficient.
- Do not create broad experts. Scope must be narrow and testable.
- Generated experts start in shadow or probation.
- For compliance, prefer curated or human-backed experts.
- Tool policies must be minimal and explicit.
- All creations must be traceable to a Router capability request and TaskPacket context key.

## Signals and learning hooks

The Recruiter must emit or record the following for the learning system:
- expert_created event with capability tags and tier
- expert_version_created event when an existing expert is updated
- recruitment_reason (missing capability, low confidence, new domain)
- template_used and constraints applied

These hooks help the Reputation Engine learn which templates and creation choices produce reliable experts over time.

## Examples of when to create vs not create

Create a new expert when:
- a partner API integration repeatedly fails due to missing domain knowledge
- billing or pricing rules require domain consistency and repeated guidance
- a service becomes a hot spot with frequent issues and unique invariants

Do not create a new expert when:
- the issue can be solved by attaching a Service Context Pack
- the capability is a one-off question that does not justify maintenance
- a broader expert exists and can be scoped safely

## Failure handling

Common failure modes and required behavior:
- no template exists: create a template request and route to human review, do not invent a broad expert
- conflicting governance rules: block creation and return to Router with escalation trigger
- qualification fails: register as inactive or discard and report failure reason
- tool policy conflict: deny tool access, propose alternative approach

## References

- Agent Skills specification: https://agentskills.io/specification
- Integrating skills: https://agentskills.io/integrate-skills

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).
