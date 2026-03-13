# Story 25.5 — Agent Network Isolation

> **As a** platform engineer,
> **I want** the agent container to run on a restricted Docker network that blocks access to internal services but allows GitHub API egress,
> **so that** a compromised or malicious agent cannot reach PostgreSQL, Temporal, NATS, or the admin API.

**Purpose:** Without network isolation, container isolation is theater. A container with network access to internal services can exfiltrate secrets, corrupt data, or disrupt infrastructure regardless of filesystem isolation. This story creates the network boundary that makes container isolation meaningful.

**Intent:** Define a Docker network `agent-net` in both dev and prod Compose files. Configure it so agent containers can resolve DNS and reach `github.com`/`api.github.com` over HTTPS, but cannot connect to any internal service (PostgreSQL 5432, Temporal 7233, NATS 4222, FastAPI 8000). Verify with integration tests.

**Points:** 5 | **Size:** M
**Epic:** 25 — Container Isolation for Primary Agent
**Sprint:** 2 (Integration and Isolation)
**Depends on:** Story 25.2 (ContainerManager uses the network name)

---

## Description

Docker's network model isolates containers by network membership. Containers on different networks cannot communicate unless explicitly connected to both. The platform services (PostgreSQL, Temporal, NATS, app) are on the `default` network. Agent containers are on `agent-net`. Since these are separate networks with no shared membership, agent containers cannot reach internal services.

Egress to the internet (specifically GitHub) is allowed by default on user-defined bridge networks — Docker routes outbound traffic through the host's network stack. The key constraint is that inbound connections from `agent-net` to `default` network services are blocked by Docker's inter-network isolation.

For production hardening, the `agent-net` network can optionally use `internal: true` with an explicit egress proxy, but that is a future enhancement. The Phase 1 approach relies on Docker's built-in network isolation between user-defined bridge networks.

## Tasks

- [ ] Add `agent-net` network to `docker-compose.dev.yml`:
  ```yaml
  networks:
    default:
      driver: bridge
    agent-net:
      driver: bridge
      labels:
        - "org.thestudio.purpose=agent-isolation"
  ```
- [ ] Ensure platform services (postgres, temporal, nats, app) are on `default` network only (they already are by default, but make it explicit)
- [ ] Add `agent-net` network to `infra/docker-compose.prod.yml` with same configuration
- [ ] Document the network architecture in a comment block in both Compose files
- [ ] Update `ContainerManager.launch()` to use `network="agent-net"` parameter (should already be parameterized from Story 25.2)
- [ ] Write integration tests in `tests/integration/test_agent_network_isolation.py` (requires Docker):
  - Launch container on `agent-net`, attempt `curl postgres:5432` — must fail (connection refused or timeout)
  - Launch container on `agent-net`, attempt `curl temporal:7233` — must fail
  - Launch container on `agent-net`, attempt `curl nats:4222` — must fail
  - Launch container on `agent-net`, attempt `curl -s https://api.github.com/zen` — must succeed (GitHub reachable)
  - Launch container on `agent-net`, attempt DNS resolution of `github.com` — must succeed
- [ ] Document Docker Desktop limitations: on macOS/Windows, Docker Desktop networking differs from Linux. Internal service names may not resolve from `agent-net` at all (which is the desired behavior), but the test approach may need adjustment.

## Acceptance Criteria

- [ ] `agent-net` network is defined in `docker-compose.dev.yml`
- [ ] `agent-net` network is defined in `infra/docker-compose.prod.yml`
- [ ] Agent container on `agent-net` cannot connect to PostgreSQL
- [ ] Agent container on `agent-net` cannot connect to Temporal
- [ ] Agent container on `agent-net` cannot connect to NATS
- [ ] Agent container on `agent-net` cannot connect to FastAPI admin
- [ ] Agent container on `agent-net` can reach `github.com` over HTTPS
- [ ] DNS resolution works inside agent container

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | PostgreSQL blocked | `curl -s --connect-timeout 3 postgres:5432` from agent-net | Connection fails (timeout or refused) |
| 2 | Temporal blocked | `curl -s --connect-timeout 3 temporal:7233` from agent-net | Connection fails |
| 3 | NATS blocked | `curl -s --connect-timeout 3 nats:4222` from agent-net | Connection fails |
| 4 | App blocked | `curl -s --connect-timeout 3 app:8000` from agent-net | Connection fails |
| 5 | GitHub reachable | `curl -s https://api.github.com/zen` from agent-net | HTTP 200, response body is a string |
| 6 | DNS works | `nslookup github.com` from agent-net | Resolves to IP address |

## Files Affected

| File | Action |
|------|--------|
| `docker-compose.dev.yml` | Modify (add agent-net network) |
| `infra/docker-compose.prod.yml` | Modify (add agent-net network) |
| `tests/integration/test_agent_network_isolation.py` | Create |

## Technical Notes

- Docker user-defined bridge networks provide automatic DNS resolution for container names within the same network, but NOT across networks. This means `agent-net` containers cannot resolve `postgres`, `temporal`, etc. by name — they are on a different network.
- Even if an agent container somehow knows the IP address of an internal service, Docker's iptables rules prevent cross-network traffic between user-defined bridges (unless `com.docker.network.bridge.enable_icc=true` is set, which it is not by default).
- On Docker Desktop (macOS/Windows), networking is virtualized through a Linux VM. The isolation behavior is the same, but tools like `iptables` are not directly accessible for debugging.
- Future hardening options: (1) `internal: true` on `agent-net` blocks ALL egress, then use an explicit HTTP proxy container for GitHub access. (2) Outbound firewall rules on the host to restrict `agent-net` to specific IP ranges (GitHub's published IP ranges).
- The `agent-net` network is created by `docker compose up` when defined in the Compose file. For standalone container launches (outside Compose), the `ContainerManager` should create the network if it does not exist: `docker network create agent-net`.
