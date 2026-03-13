# Cloudflare Tunnel + GoDaddy Domain + Local Docker Setup

Research and implementation guide for exposing a local Docker container to the
public internet via Cloudflare Tunnel using a GoDaddy-registered domain.

---

## Architecture Overview

```
Internet                          Cloudflare Edge                Your Home Network
                                                                 (no open ports)
Browser ──HTTPS──► Cloudflare ◄──── persistent outbound ────── cloudflared container
                   (TLS term,       connection (QUIC/H2)              │
                    WAF, DDoS)                                        │
                                                                 docker network
                                                                      │
                                                                  your app container
                                                                  (port 8080, etc.)
```

**Key point:** Your home router needs zero port forwarding. The `cloudflared` daemon
initiates an outbound connection to Cloudflare's edge, and Cloudflare routes
incoming requests back through that connection.

---

## Prerequisites

| Item | Details |
|------|---------|
| Domain | Registered on GoDaddy (any TLD) |
| Cloudflare account | Free tier — sign up at https://dash.cloudflare.com |
| Docker + Docker Compose | Installed on your home machine |
| Home internet | Standard residential connection (no static IP needed) |

---

## Part 1: Domain Configuration (GoDaddy → Cloudflare DNS)

Cloudflare Tunnel requires Cloudflare to manage your DNS. You have two options:

### Option A: Change nameservers (recommended)

This makes Cloudflare the authoritative DNS for your domain while keeping
GoDaddy as the registrar.

1. **Add domain to Cloudflare**
   - Log in to Cloudflare dashboard
   - Click "Add a site" → enter your domain → select **Free** plan
   - Cloudflare will scan existing DNS records and import them

2. **Copy Cloudflare nameservers**
   - Cloudflare gives you two nameservers, e.g.:
     ```
     aria.ns.cloudflare.com
     noah.ns.cloudflare.com
     ```

3. **Update nameservers on GoDaddy**
   - GoDaddy → My Products → DNS → your domain
   - Click "Change" next to Nameservers
   - Select "I'll use my own nameservers"
   - Enter the two Cloudflare nameservers
   - Save

4. **Wait for propagation**
   - Usually 15 minutes to 24 hours
   - Cloudflare will email you when active
   - Verify: `dig NS yourdomain.com` should show Cloudflare nameservers

### Option B: CNAME setup (Business plan only)

Not available on free tier — requires Cloudflare Business ($200/mo). Skip this.

### DNS verification checklist

```bash
# Confirm nameservers point to Cloudflare
dig NS yourdomain.com +short

# Confirm domain resolves (after tunnel setup)
dig A app.yourdomain.com +short
```

---

## Part 2: Cloudflare Tunnel Setup

### Step 1: Install cloudflared locally (one-time auth)

You need `cloudflared` on your host temporarily to authenticate and create
the tunnel. After that, everything runs in Docker.

```bash
# Windows (winget)
winget install Cloudflare.cloudflared

# macOS
brew install cloudflared

# Linux (Debian/Ubuntu)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

### Step 2: Authenticate

```bash
cloudflared tunnel login
```

This opens a browser — select your domain. A certificate (`cert.pem`) is saved to:
- **Windows:** `%USERPROFILE%\.cloudflared\cert.pem`
- **Linux/macOS:** `~/.cloudflared/cert.pem`

### Step 3: Create the tunnel

```bash
cloudflared tunnel create home-docker
```

This creates:
- A tunnel UUID (e.g., `a1b2c3d4-...`)
- A credentials file at `~/.cloudflared/<TUNNEL_UUID>.json`

Save the UUID — you'll need it.

### Step 4: Create the config file

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /home/nonroot/.cloudflared/<TUNNEL_UUID>.json

ingress:
  # Route app.yourdomain.com to your Docker container
  - hostname: app.yourdomain.com
    service: http://myapp:8080

  # Route a second subdomain (optional)
  - hostname: api.yourdomain.com
    service: http://myapi:3000

  # Catch-all (required — returns 404 for unmatched requests)
  - service: http_status:404
```

### Step 5: Create DNS records

```bash
cloudflared tunnel route dns home-docker app.yourdomain.com
cloudflared tunnel route dns home-docker api.yourdomain.com   # if using multiple
```

This creates CNAME records in Cloudflare DNS pointing to
`<TUNNEL_UUID>.cfargotunnel.com`.

---

## Part 3: Docker Compose Configuration

### Directory structure

```
~/tunnel/
├── docker-compose.yml
├── cloudflared/
│   ├── config.yml          ← copied from Step 4
│   ├── cert.pem            ← from authentication
│   └── <TUNNEL_UUID>.json  ← tunnel credentials
└── myapp/
    └── (your application files)
```

### docker-compose.yml

```yaml
version: "3.9"

services:
  # ── Your application ──────────────────────────────────
  myapp:
    image: your-app-image:latest       # or build: ./myapp
    container_name: myapp
    restart: unless-stopped
    networks:
      - tunnel-net
    # No "ports:" needed — not exposed to host or internet
    environment:
      - APP_ENV=production

  # ── Cloudflare Tunnel ─────────────────────────────────
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflared/config.yml:/etc/cloudflared/config.yml:ro
      - ./cloudflared/cert.pem:/home/nonroot/.cloudflared/cert.pem:ro
      - ./cloudflared/<TUNNEL_UUID>.json:/home/nonroot/.cloudflared/<TUNNEL_UUID>.json:ro
    networks:
      - tunnel-net
    depends_on:
      - myapp

networks:
  tunnel-net:
    driver: bridge
```

### config.yml (inside cloudflared/ directory)

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /home/nonroot/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: app.yourdomain.com
    service: http://myapp:8080
    originRequest:
      noTLSVerify: true          # only if your app uses self-signed certs
      connectTimeout: 10s
      keepAliveTimeout: 90s

  - service: http_status:404
```

### Start everything

```bash
cd ~/tunnel
docker compose up -d

# Check tunnel status
docker logs cloudflared

# You should see:
# Connection ... registered connectorID=... location=...
# (4 connections to different Cloudflare data centers)
```

---

## Part 4: Security Hardening

### 4.1 Cloudflare Access (zero-trust auth, free for up to 50 users)

Add an authentication layer so only authorized users can reach your app:

1. Cloudflare dashboard → Zero Trust → Access → Applications
2. "Add an application" → Self-hosted
3. Configure:
   - **Application domain:** `app.yourdomain.com`
   - **Session duration:** 24 hours
   - **Policy:** Allow — Emails ending in `@youremail.com`
     (or use one-time PIN, GitHub SSO, Google SSO, etc.)

Now visitors must authenticate before Cloudflare forwards any traffic to your
tunnel. Your app never sees unauthenticated requests.

### 4.2 Cloudflare WAF rules (free tier)

- Dashboard → Security → WAF
- Enable managed rules (free tier includes basic protection)
- Add custom rules:
  - Block by country (if your users are in one region)
  - Rate limiting (e.g., 100 requests/minute per IP)

### 4.3 Docker network isolation

```yaml
# In docker-compose.yml, use an internal network for backend services
networks:
  tunnel-net:
    driver: bridge
  internal:
    driver: bridge
    internal: true   # no external access

services:
  myapp:
    networks:
      - tunnel-net
      - internal

  database:
    networks:
      - internal     # only reachable by myapp, not by cloudflared
```

### 4.4 Cloudflared service token (machine-to-machine)

For API endpoints that other services call:

```bash
# Create a service token in Cloudflare Zero Trust dashboard
# Then pass headers in API calls:
curl -H "CF-Access-Client-Id: <CLIENT_ID>" \
     -H "CF-Access-Client-Secret: <CLIENT_SECRET>" \
     https://api.yourdomain.com/health
```

### 4.5 Local firewall

Even though no ports are forwarded, defense in depth:

```bash
# Linux (ufw)
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw enable

# Windows — ensure no inbound rules for your app port
```

---

## Part 5: Multiple Services / Subdomains

One tunnel can serve many subdomains. Update `config.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /home/nonroot/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: app.yourdomain.com
    service: http://myapp:8080

  - hostname: api.yourdomain.com
    service: http://myapi:3000

  - hostname: grafana.yourdomain.com
    service: http://grafana:3000

  - hostname: pgadmin.yourdomain.com
    service: http://pgadmin:80

  - service: http_status:404
```

Register each DNS route:

```bash
cloudflared tunnel route dns home-docker app.yourdomain.com
cloudflared tunnel route dns home-docker api.yourdomain.com
cloudflared tunnel route dns home-docker grafana.yourdomain.com
cloudflared tunnel route dns home-docker pgadmin.yourdomain.com
```

---

## Part 6: Monitoring and Maintenance

### Health checks

```bash
# Tunnel status from CLI
cloudflared tunnel info home-docker

# From Cloudflare dashboard
# Zero Trust → Networks → Tunnels → home-docker → status

# Local container health
docker inspect --format='{{.State.Health.Status}}' cloudflared
```

### Add health check to docker-compose

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  healthcheck:
    test: ["CMD", "cloudflared", "tunnel", "--config", "/etc/cloudflared/config.yml", "info"]
    interval: 60s
    timeout: 10s
    retries: 3
```

### Auto-restart on host boot

Docker's `restart: unless-stopped` handles container restarts. Ensure Docker
itself starts on boot:

```bash
# Linux
sudo systemctl enable docker

# Windows
# Docker Desktop → Settings → General → Start Docker Desktop when you sign in
```

### Updating cloudflared

```bash
docker compose pull cloudflared
docker compose up -d cloudflared
```

---

## Part 7: Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ERR Unable to reach the origin service` | App container not running or wrong port | `docker ps`, check service name matches config.yml hostname |
| `502 Bad Gateway` | App is starting up slowly | Add `connectTimeout: 30s` to originRequest |
| Tunnel shows "Inactive" in dashboard | cloudflared container crashed | `docker logs cloudflared`, check credentials file path |
| DNS not resolving | Nameservers not propagated | `dig NS yourdomain.com`, wait or re-check GoDaddy settings |
| `ERR certificate` errors | cert.pem not mounted correctly | Verify volume mount path in docker-compose |
| Tunnel connects but app returns errors | App bound to 127.0.0.1 not 0.0.0.0 | Set app to listen on `0.0.0.0` inside the container |

### Debug logging

```bash
# Run tunnel with debug output
docker compose exec cloudflared cloudflared tunnel --loglevel debug run
```

---

## Part 8: Cost Summary

| Component | Cost |
|-----------|------|
| GoDaddy domain | ~$10-15/year (varies by TLD) |
| Cloudflare free plan | $0 |
| Cloudflare Tunnel | $0 |
| Cloudflare Access (up to 50 users) | $0 |
| Home electricity for Docker host | (already running) |
| **Total** | **~$10-15/year** |

---

## Quick-Start Checklist

```
[ ] 1. Register/own domain on GoDaddy
[ ] 2. Create free Cloudflare account
[ ] 3. Add domain to Cloudflare, get nameservers
[ ] 4. Update GoDaddy nameservers → Cloudflare
[ ] 5. Wait for DNS propagation (check email)
[ ] 6. Install cloudflared, run `tunnel login`
[ ] 7. Create tunnel: `cloudflared tunnel create home-docker`
[ ] 8. Write config.yml with ingress rules
[ ] 9. Route DNS: `cloudflared tunnel route dns home-docker app.yourdomain.com`
[ ] 10. Set up docker-compose.yml with cloudflared + app
[ ] 11. `docker compose up -d`
[ ] 12. Test: visit https://app.yourdomain.com
[ ] 13. (Optional) Enable Cloudflare Access for auth
[ ] 14. (Optional) Configure WAF rules
```
