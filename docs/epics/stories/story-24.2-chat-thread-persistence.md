# Story 24.2 — Approval Chat Thread Persistence

> **As a** platform operator,
> **I want** chat threads between reviewers and the system persisted in the database,
> **so that** every approval decision has an auditable conversation history.

**Purpose:** The chat thread is the audit trail. Without persistence, there is no record of what questions the reviewer asked, what answers they received, or whether the conversation informed their decision. This story delivers the database schema and CRUD layer that the chat API (Story 24.3) builds on.

**Intent:** Create SQLAlchemy models for `approval_chat` and `approval_chat_message`, an Alembic migration, and CRUD functions for creating, reading, and resolving chat threads.

**Points:** 5 | **Size:** M
**Epic:** 24 — Chat Interface for Approval Workflows
**Sprint:** 1 (Stories 24.1-24.3)
**Depends on:** None (parallel with 24.1)

---

## Description

Two tables are needed. `approval_chat` represents a conversation thread tied to a specific TaskPacket approval. There is at most one active chat per TaskPacket (enforced by unique partial index on `taskpacket_id` where `status = 'active'`). `approval_chat_message` stores individual messages in the thread, with roles (user, assistant, system) matching the standard chat completion convention.

Chat threads have a lifecycle: `active` (during approval wait), `resolved` (after approve/reject), `expired` (after 7-day timeout). The CRUD layer handles transitions.

## Tasks

- [ ] Create `src/approval/chat_models.py`:
  - `ChatStatus` StrEnum: `active`, `resolved`, `expired`
  - `MessageRole` StrEnum: `user`, `assistant`, `system`
  - `ApprovalChat` SQLAlchemy model:
    - `id: Mapped[UUID]` — PK, default uuid4
    - `taskpacket_id: Mapped[UUID]` — FK to taskpackets.id, not null
    - `created_by: Mapped[str]` — user who initiated the chat
    - `status: Mapped[ChatStatus]` — default `active`
    - `created_at: Mapped[datetime]` — server default now
    - `resolved_at: Mapped[datetime | None]` — set on resolve/expire
    - Relationship to messages
  - `ApprovalChatMessage` SQLAlchemy model:
    - `id: Mapped[UUID]` — PK, default uuid4
    - `chat_id: Mapped[UUID]` — FK to approval_chat.id, not null
    - `role: Mapped[MessageRole]` — user/assistant/system
    - `content: Mapped[str]` — message text, not null
    - `created_at: Mapped[datetime]` — server default now
    - Index on `(chat_id, created_at)` for ordered retrieval
- [ ] Create Alembic migration:
  - `approval_chat` table
  - `approval_chat_message` table
  - Unique partial index on `approval_chat(taskpacket_id)` WHERE `status = 'active'`
  - FK constraints with CASCADE delete on messages when chat is deleted
- [ ] Create `src/approval/chat_crud.py`:
  - `async create_chat(session, taskpacket_id: UUID, created_by: str) -> ApprovalChat`
    - Creates new chat with status=active
    - If active chat exists for taskpacket_id, returns existing (idempotent)
  - `async get_chat_by_taskpacket(session, taskpacket_id: UUID) -> ApprovalChat | None`
    - Returns the active chat for a taskpacket, or None
  - `async add_message(session, chat_id: UUID, role: MessageRole, content: str) -> ApprovalChatMessage`
    - Adds a message to the chat thread
    - Raises ValueError if chat is not active
  - `async get_messages(session, chat_id: UUID, limit: int = 50) -> list[ApprovalChatMessage]`
    - Returns messages ordered by created_at, limited to most recent `limit`
  - `async get_message_count(session, chat_id: UUID) -> int`
    - Returns total message count for a chat
  - `async resolve_chat(session, chat_id: UUID) -> ApprovalChat`
    - Sets status=resolved, resolved_at=now
    - Idempotent: resolving an already-resolved chat is a no-op
  - `async expire_chat(session, chat_id: UUID) -> ApprovalChat`
    - Sets status=expired, resolved_at=now
    - Used by timeout handling
- [ ] Write tests in `tests/approval/test_chat_crud.py`:
  - Test create_chat creates new chat
  - Test create_chat is idempotent (returns existing active chat)
  - Test get_chat_by_taskpacket returns active chat
  - Test get_chat_by_taskpacket returns None when no active chat
  - Test add_message persists message
  - Test add_message raises on non-active chat
  - Test get_messages returns ordered messages
  - Test get_messages respects limit
  - Test get_message_count returns correct count
  - Test resolve_chat transitions status
  - Test resolve_chat is idempotent
  - Test expire_chat transitions status

## Acceptance Criteria

- [ ] Both SQLAlchemy models create valid tables
- [ ] Alembic migration runs forward and backward cleanly
- [ ] Unique partial index prevents multiple active chats per TaskPacket
- [ ] All CRUD functions work with async sessions
- [ ] add_message rejects messages on non-active chats
- [ ] resolve_chat and expire_chat are idempotent
- [ ] Unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Create chat | taskpacket_id, user_id | New ApprovalChat with status=active |
| 2 | Duplicate create | Same taskpacket_id twice | Same chat returned both times |
| 3 | Add message | chat_id, role=user, content | Persisted ApprovalChatMessage |
| 4 | Add to resolved | resolved chat_id | ValueError raised |
| 5 | Get messages ordered | 5 messages added | Returned in created_at order |
| 6 | Resolve chat | active chat_id | status=resolved, resolved_at set |
| 7 | Resolve idempotent | already resolved chat_id | No change, no error |

## Files Affected

| File | Action |
|------|--------|
| `src/approval/chat_models.py` | Create |
| `src/approval/chat_crud.py` | Create |
| `alembic/versions/xxxx_approval_chat_tables.py` | Create |
| `tests/approval/test_chat_crud.py` | Create |

## Technical Notes

- Follow the pattern in `src/admin/rbac.py` for SQLAlchemy model definition (uses `Mapped`, `mapped_column`, `Base` from `src/db/base.py`).
- The unique partial index on PostgreSQL: `CREATE UNIQUE INDEX uq_active_chat_per_task ON approval_chat (taskpacket_id) WHERE status = 'active'`.
- For tests, use the same async session fixtures as existing unit tests. If none exist, create a SQLite-based test session (SQLAlchemy async supports SQLite for testing).
- Message content is unbounded text. No size limit in the DB — the 50-message cap is enforced at the API layer, not the storage layer.
