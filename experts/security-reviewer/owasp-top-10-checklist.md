# OWASP Top 10 Review Checklist

## A01:2021 — Broken Access Control
- [ ] Authorization checks on all endpoints
- [ ] Deny by default for protected resources
- [ ] CORS configuration properly restrictive

## A02:2021 — Cryptographic Failures
- [ ] No hardcoded secrets or credentials
- [ ] Proper encryption for data at rest and in transit
- [ ] Strong hashing algorithms (bcrypt/argon2 for passwords)

## A03:2021 — Injection
- [ ] Parameterized queries (no string concatenation in SQL)
- [ ] Input validation and sanitization
- [ ] Output encoding for context (HTML, URL, JS)

## A04:2021 — Insecure Design
- [ ] Threat modeling for new features
- [ ] Rate limiting on authentication endpoints
- [ ] Business logic validation

## A05:2021 — Security Misconfiguration
- [ ] No default credentials
- [ ] Error handling does not leak stack traces
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options)

## A06:2021 — Vulnerable and Outdated Components
- [ ] Dependencies scanned for known CVEs
- [ ] No end-of-life libraries in use

## A07:2021 — Identification and Authentication Failures
- [ ] Multi-factor authentication where applicable
- [ ] Session management follows best practices
- [ ] Password policies enforced

## A08:2021 — Software and Data Integrity Failures
- [ ] CI/CD pipeline integrity verified
- [ ] Deserialization of untrusted data avoided
- [ ] Code signing where applicable

## A09:2021 — Security Logging and Monitoring Failures
- [ ] Authentication events logged
- [ ] Failed access attempts logged
- [ ] Audit trail for sensitive operations

## A10:2021 — Server-Side Request Forgery (SSRF)
- [ ] URL validation for server-side requests
- [ ] Allowlist for permitted external hosts
- [ ] No unrestricted internal network access
