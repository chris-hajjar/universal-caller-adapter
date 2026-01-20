# Credential Vault & Downstream API Authorization
## Product Scoping Document

**Document Version:** 1.0
**Date:** 2026-01-20
**Status:** Draft
**Author:** Technical Architecture Team
**Stakeholders:** Product Management, Engineering, Security, Compliance

---

## Executive Summary

### The Problem
Our system currently authenticates users and authorizes tool calls, but tools cannot make authenticated API calls to external services (GitHub, Slack, etc.) on behalf of users. This severely limits functionality for integration use cases.

**Current State:**
- ✅ We verify WHO the user is
- ✅ We verify WHAT tools they can access
- ❌ We CANNOT call external APIs as the user
- ❌ Tools must use service accounts (wrong user context) or fail

**Impact:**
- Cannot build integrations (read user's GitHub repos, post to user's Slack, etc.)
- Cannot provide personalized experiences based on user's external data
- Limits platform value and competitive positioning

### Proposed Solution
Implement a **Credential Vault** system that:
1. Allows users to explicitly connect external services via OAuth
2. Securely stores delegated credentials (tokens) per user
3. Enables tools to access external APIs with proper user authorization
4. Maintains enterprise-grade security and compliance

### Success Metrics
- **Primary:** 80%+ of active users connect at least one external service
- **Secondary:** Tools successfully call external APIs with <5% error rate
- **Tertiary:** Zero security incidents related to credential storage

---

## Problem Statement

### Current Architecture Limitation

Our authorization flow today:

```
1. User request with credentials → Authentication
2. Create Principal (identity + permissions)
3. DISCARD original credentials ❌
4. Authorize tool call
5. Execute tool
6. Tool has identity but NO credentials for downstream APIs
```

**Concrete Example:**

```
User: "Show me my GitHub repositories"

System: ✓ Verified you're Alice
        ✓ You have permission to use github_repos tool
        ✓ Executing tool...

Tool:   ❌ I need Alice's GitHub token to call GitHub API
        ❌ But I don't have it
        ❌ Cannot complete request
```

### Why This Matters

**Use Cases Blocked:**
1. **Read user's external data:** GitHub repos, Slack messages, Google Drive files
2. **Write on user's behalf:** Post to Slack, create GitHub issues, send emails
3. **Sync/integrate:** Two-way sync between systems with user's permissions
4. **Personalization:** Tools that adapt based on user's external context

**Business Impact:**
- Cannot compete with Zapier, n8n, Make.com for integration use cases
- Cannot provide AI agents that act across multiple systems
- Limited to internal-only tools

---

## Solution Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ User Authenticates (Cookie/OAuth/Slack)                     │
│ → Creates Principal                                         │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ NEW: User Connects External Services                        │
│ → OAuth flow per service (GitHub, Slack, etc.)             │
│ → Store encrypted tokens in Credential Vault               │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Tool Execution                                               │
│ → Retrieve user's token for required service               │
│ → Call external API with user's credentials                │
│ → Return results                                            │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Identity Service:** Maps multiple auth methods to canonical user ID
2. **Connection Manager:** OAuth flows to connect external services
3. **Credential Vault:** Encrypted storage for tokens (AWS Secrets Manager)
4. **Token Lifecycle Manager:** Auto-refresh, expiration handling, revocation
5. **Integration Layer:** Tools retrieve and use stored credentials

### Key Principles

- **Explicit Consent:** Users must explicitly authorize each service connection
- **Principle of Least Privilege:** Tokens scoped to minimum required permissions
- **Secure by Default:** Encrypted storage, audit logging, STRONG auth required
- **User Control:** Users can view and disconnect services anytime

---

## Functional Requirements

### FR-1: Service Connection (OAuth Flow)

**User Story:** As a user, I want to connect my external accounts so tools can access them on my behalf.

**Acceptance Criteria:**
- [ ] User can view list of available services to connect
- [ ] Clicking "Connect [Service]" initiates OAuth flow
- [ ] User redirected to service's authorization page
- [ ] User sees clear scope description (what permissions are requested)
- [ ] After authorization, user redirected back with success message
- [ ] Connection persists across sessions
- [ ] Only users with STRONG authentication can connect services

**UI/UX:**
```
┌─────────────────────────────────────┐
│ Connect External Services            │
├─────────────────────────────────────┤
│                                      │
│ Available Services:                  │
│                                      │
│ ┌──────────────────────────────┐    │
│ │ 🐙 GitHub                    │    │
│ │                              │    │
│ │ Access your repositories,    │    │
│ │ issues, and pull requests    │    │
│ │                              │    │
│ │ [Connect GitHub]             │    │
│ └──────────────────────────────┘    │
│                                      │
│ ┌──────────────────────────────┐    │
│ │ 💬 Slack                     │    │
│ │                              │    │
│ │ Post messages and read       │    │
│ │ channels on your behalf      │    │
│ │                              │    │
│ │ [Connect Slack]              │    │
│ └──────────────────────────────┘    │
│                                      │
└─────────────────────────────────────┘
```

**Error Cases:**
- User denies authorization → Show friendly message, allow retry
- OAuth fails (network, invalid config) → Show error, log incident
- User already connected → Show "Already connected" status

---

### FR-2: View Connected Services

**User Story:** As a user, I want to see what services I've connected and manage them.

**Acceptance Criteria:**
- [ ] User can view list of all connected services
- [ ] Each service shows: Name, connected date, permissions granted
- [ ] User can disconnect any service
- [ ] After disconnect, tools requiring that service show "Not connected" error
- [ ] Disconnecting revokes token at provider (best effort)

**UI/UX:**
```
┌─────────────────────────────────────┐
│ Settings → Connected Services        │
├─────────────────────────────────────┤
│                                      │
│ Your connected accounts:             │
│                                      │
│ ┌──────────────────────────────┐    │
│ │ 🐙 GitHub                    │    │
│ │ Connected: Jan 15, 2026      │    │
│ │ Permissions:                 │    │
│ │ • Read repositories          │    │
│ │ • Read user profile          │    │
│ │                              │    │
│ │ [Disconnect]  [Reconnect]    │    │
│ └──────────────────────────────┘    │
│                                      │
│ ┌──────────────────────────────┐    │
│ │ 💬 Slack                     │    │
│ │ Not connected                │    │
│ │                              │    │
│ │ [Connect]                    │    │
│ └──────────────────────────────┘    │
│                                      │
└─────────────────────────────────────┘
```

---

### FR-3: Tool Execution with Credentials

**User Story:** As a user, I want tools to automatically use my connected services without re-authenticating.

**Acceptance Criteria:**
- [ ] Tool checks if required service is connected
- [ ] If not connected, show clear error with link to connect
- [ ] If connected, tool retrieves token and calls external API
- [ ] If token expired, automatically refresh (transparent to user)
- [ ] If refresh fails, prompt user to reconnect
- [ ] Tool returns results as if API call was native

**Error Handling:**

| Error | User Experience |
|-------|-----------------|
| Service not connected | "Please connect GitHub first [Connect]" |
| Token expired, refresh succeeds | Transparent, user sees results |
| Token expired, refresh fails | "Please reconnect GitHub [Reconnect]" |
| API rate limit | "GitHub rate limit reached, try again in 15 minutes" |
| API unauthorized | "GitHub access revoked, please reconnect [Reconnect]" |
| Network error | "Cannot reach GitHub, please try again" |

**Example Flow:**
```
User: "Show my GitHub repos"

System:
  1. Check: Does Alice have GitHub connected?
     → Yes ✓

  2. Retrieve: Get Alice's GitHub token from vault
     → Found: token_xyz (expires in 30 min) ✓

  3. Call: GET github.com/user/repos
     → Success ✓

  4. Return: "Found 12 repositories: ..."
```

---

### FR-4: Identity Linking (Multi-Auth Support)

**User Story:** As a user who authenticates via multiple methods (web login, SSO, Slack), I want my connected services to work across all methods.

**Background:** Users may authenticate via:
- Cookie (username/password login)
- OAuth (company SSO)
- Slack (slash commands)

These create different `principal_id` values for the same person. We need to link them to one identity.

**Acceptance Criteria:**
- [ ] System maintains canonical user ID across auth methods
- [ ] Users can link their Slack account to their web/SSO account
- [ ] Once linked, Slack commands can access services connected via web
- [ ] Linking requires STRONG authentication (not Slack WEAK auth)
- [ ] Users can view and unlink auth methods

**Slack Linking Flow:**

```
1. User in Slack: /link-account
   → Bot: "Visit your-system.com/link and enter code: ABC-123"

2. User opens browser → Goes to your-system.com/link
   → Prompted to log in (needs STRONG auth)
   → Logs in with company SSO

3. User enters code: ABC-123
   → System links: slack:U12345 ↔ alice@acme.com
   → Success: "Slack account linked!"

4. User in Slack: /github-repos
   → System resolves: slack:U12345 → alice@acme.com
   → Retrieves: alice@acme.com's GitHub token
   → Works! ✓
```

**UI/UX (Settings):**
```
┌─────────────────────────────────────┐
│ Settings → Linked Accounts           │
├─────────────────────────────────────┤
│                                      │
│ Your authentication methods:         │
│                                      │
│ ✓ Email: alice@acme.com (Primary)   │
│ ✓ Slack: @alice (acme.slack.com)    │
│ ✓ Cookie Session: user_12345        │
│                                      │
│ [Link Another Account]               │
│                                      │
└─────────────────────────────────────┘
```

---

### FR-5: Token Lifecycle Management

**User Story:** As a user, I want my connected services to work reliably without manual token maintenance.

**Acceptance Criteria:**
- [ ] Tokens automatically refresh before expiration (5 min buffer)
- [ ] Refresh happens in background (user doesn't wait)
- [ ] Failed refresh prompts user to reconnect
- [ ] Token revocation (user disconnects) is immediate
- [ ] Expired tokens cleaned up automatically (30 days after expiry)

**Token States:**

```
VALID → Token active, not expired
  ├─→ AUTO_REFRESH (5 min before expiry)
  │     ├─→ SUCCESS: New token stored
  │     └─→ FAILURE: Mark EXPIRED, notify user
  │
  ├─→ REVOKED (user disconnected)
  │     └─→ Delete immediately
  │
  └─→ EXPIRED (past expiry, refresh failed)
        └─→ Delete after 30 days
```

**Refresh Strategy:**

| Service | Refresh Method | Frequency |
|---------|----------------|-----------|
| GitHub | OAuth refresh_token | Before expiry (8 hour tokens) |
| Slack | Re-authorization | 90 days or on failure |
| Google | OAuth refresh_token | Before expiry (1 hour tokens) |

---

### FR-6: Security & Compliance

**User Story:** As a security/compliance officer, I want strong guarantees about credential security.

**Acceptance Criteria:**

**Encryption:**
- [ ] All tokens encrypted at rest (AES-256)
- [ ] Encryption keys managed via AWS KMS or equivalent
- [ ] Keys rotated every 90 days
- [ ] Tokens encrypted in transit (TLS 1.3)

**Access Control:**
- [ ] Only STRONG authentication can connect/disconnect services
- [ ] WEAK authentication (Slack) can use services only after linking
- [ ] Tool execution contexts can only access tokens they need
- [ ] No token sharing across tenants (multi-tenant isolation)

**Audit Logging:**
- [ ] Log all credential operations: connect, disconnect, access, refresh
- [ ] Log format: timestamp, user_id, action, service, result, IP, user_agent
- [ ] Logs retained for 1 year minimum
- [ ] Logs exportable for compliance audits

**Compliance:**
- [ ] SOC 2 Type II ready (access controls, encryption, logging)
- [ ] GDPR ready (right to erasure, data portability, consent)
- [ ] OAuth 2.0 best practices (PKCE, state parameter, etc.)

**Sample Audit Log:**
```json
{
  "timestamp": "2026-01-20T10:30:00Z",
  "event": "credential_accessed",
  "user_id": "alice@acme.com",
  "service": "github",
  "tool": "read_github_repos",
  "result": "success",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0..."
}
```

---

### FR-7: Error Handling & User Feedback

**User Story:** As a user, I want clear feedback when something goes wrong with my connections.

**Acceptance Criteria:**
- [ ] All errors have user-friendly messages (no technical jargon)
- [ ] Errors include actionable next steps ("Click here to reconnect")
- [ ] System differentiates between user errors and system errors
- [ ] Transient errors (network) suggest retry
- [ ] Permanent errors (revoked access) suggest reconnect

**Error Types & Messages:**

| Error Type | User Message | Action |
|------------|--------------|--------|
| Not connected | "Please connect your GitHub account to use this tool" | [Connect GitHub] |
| Token expired | "Your GitHub connection expired. Please reconnect." | [Reconnect] |
| Refresh failed | "Cannot refresh GitHub access. Please reconnect." | [Reconnect] |
| API unauthorized | "GitHub revoked access. Please reconnect." | [Reconnect] |
| Rate limited | "GitHub rate limit reached. Try again in 15 minutes." | [Show timer] |
| Network error | "Cannot reach GitHub. Please check your connection." | [Retry] |
| Invalid scope | "This tool needs additional GitHub permissions." | [Reconnect with new scope] |

---

### FR-8: Service Configuration (Admin)

**User Story:** As an admin, I want to configure which external services are available.

**Acceptance Criteria:**
- [ ] Admin can enable/disable services globally
- [ ] Admin can configure OAuth credentials per service
- [ ] Admin can set required scopes per service
- [ ] Admin can view service connection statistics
- [ ] Changes take effect immediately (no restart required)

**Admin UI:**
```
┌─────────────────────────────────────┐
│ Admin → External Services            │
├─────────────────────────────────────┤
│                                      │
│ ┌──────────────────────────────┐    │
│ │ GitHub                       │    │
│ │ Status: ✓ Enabled            │    │
│ │ Connected Users: 1,247       │    │
│ │                              │    │
│ │ OAuth Configuration:         │    │
│ │ Client ID: gh_abc123         │    │
│ │ Client Secret: ••••••••      │    │
│ │ Scopes: repo, read:user      │    │
│ │                              │    │
│ │ [Edit] [Disable] [Stats]     │    │
│ └──────────────────────────────┘    │
│                                      │
│ [+ Add New Service]                  │
│                                      │
└─────────────────────────────────────┘
```

---

## Non-Functional Requirements

### NFR-1: Performance
- Token retrieval: < 100ms (with caching)
- OAuth flow: < 2s total (excluding external service time)
- Token refresh: < 500ms (background job)
- Cache tokens locally for 5 minutes to reduce vault calls

### NFR-2: Reliability
- 99.9% uptime for credential vault
- Failed token refresh retries 3x with exponential backoff
- Circuit breaker for external APIs (fail fast after 5 errors)
- Graceful degradation (tools continue working with cached tokens)

### NFR-3: Scalability
- Support 100k+ users with connected services
- Support 1k+ token refreshes per minute
- Horizontally scalable (stateless application servers)
- Use managed services for vault (AWS Secrets Manager)

### NFR-4: Security
- All credentials encrypted at rest and in transit
- No credentials in logs, ever
- Token rotation on security incidents
- Regular security audits (quarterly)

### NFR-5: Observability
- Metrics: Connection rate, refresh success rate, API call success rate
- Alerting: Failed refreshes >5%, vault errors, API errors >10%
- Dashboards: Real-time connection status, token health
- Distributed tracing for multi-service calls

---

## User Flows

### Flow 1: First-Time User Connecting GitHub

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: User tries to use GitHub tool                       │
└─────────────────────────────────────────────────────────────┘

User: "Show me my GitHub repos"

System: ┌─────────────────────────────────────┐
        │ GitHub Not Connected                │
        │                                     │
        │ To use this tool, connect GitHub.  │
        │                                     │
        │ [Connect GitHub]                   │
        └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Step 2: OAuth flow                                          │
└─────────────────────────────────────────────────────────────┘

User clicks [Connect GitHub]
  ↓
Redirect to: github.com/login/oauth/authorize
  ↓
GitHub shows: "YourApp wants to access your repos. [Authorize]"
  ↓
User clicks [Authorize]
  ↓
Redirect back: your-system.com/callback/github?code=xyz

┌─────────────────────────────────────────────────────────────┐
│ Step 3: Token exchange & storage (invisible to user)       │
└─────────────────────────────────────────────────────────────┘

System exchanges code for token
  ↓
System stores: alice:github → encrypted_token
  ↓
System shows: "✅ GitHub connected successfully!"

┌─────────────────────────────────────────────────────────────┐
│ Step 4: User retries                                        │
└─────────────────────────────────────────────────────────────┘

User: "Show me my GitHub repos"

System: [Retrieves token, calls GitHub API]

        "Found 12 repositories:
         1. alice/my-project
         2. alice/website
         ..."
```

### Flow 2: Slack User Linking Account

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Slack user tries to use GitHub tool                │
└─────────────────────────────────────────────────────────────┘

User in Slack: /github-repos

SlackBot: ⚠️ Your Slack account is not linked.

          To use this command:
          1. Visit: your-system.com/link
          2. Enter code: ABC-123

          This lets you connect services like GitHub.

┌─────────────────────────────────────────────────────────────┐
│ Step 2: User links account via web                         │
└─────────────────────────────────────────────────────────────┘

User opens: your-system.com/link
  ↓
Prompted to log in (needs STRONG auth)
  ↓
User logs in with company SSO (alice@acme.com)
  ↓
Enter code: ABC-123
  ↓
System links: slack:U12345 ↔ alice@acme.com
  ↓
Success page: "✅ Slack account linked!"

┌─────────────────────────────────────────────────────────────┐
│ Step 3: User connects GitHub (via web)                     │
└─────────────────────────────────────────────────────────────┘

User clicks "Connect GitHub" (standard OAuth flow)
  ↓
System stores: alice@acme.com:github → token

┌─────────────────────────────────────────────────────────────┐
│ Step 4: User returns to Slack                              │
└─────────────────────────────────────────────────────────────┘

User in Slack: /github-repos

System:
  1. Resolve: slack:U12345 → alice@acme.com
  2. Retrieve: alice@acme.com:github → token
  3. Call GitHub API
  4. Return results

SlackBot: Found 12 repositories:
          • alice/my-project
          • alice/website
          ...
```

### Flow 3: Token Expiration & Refresh

```
┌─────────────────────────────────────────────────────────────┐
│ Scenario A: Successful Auto-Refresh (Transparent)          │
└─────────────────────────────────────────────────────────────┘

Time: 9:55 AM - Token expires at 10:00 AM

Background Job:
  → Checks tokens expiring in next 5 minutes
  → Finds: alice@acme.com:github (expires 10:00 AM)
  → Uses refresh_token to get new access_token
  → Success! Stores new token
  → Updates expiry to 6:00 PM

Time: 10:15 AM - User uses tool

User: "Show my GitHub repos"

System:
  → Retrieves token (fresh, expires 6:00 PM)
  → Works perfectly
  → User never knew token was refreshed ✓

┌─────────────────────────────────────────────────────────────┐
│ Scenario B: Failed Refresh (User Action Required)          │
└─────────────────────────────────────────────────────────────┘

Time: 9:55 AM - Token expires at 10:00 AM

Background Job:
  → Tries to refresh: alice@acme.com:github
  → GitHub returns: "refresh_token revoked"
  → Marks token as EXPIRED
  → Logs incident

Time: 10:15 AM - User uses tool

User: "Show my GitHub repos"

System: ┌─────────────────────────────────────┐
        │ GitHub Connection Expired           │
        │                                     │
        │ Your GitHub access has expired.    │
        │ Please reconnect.                  │
        │                                     │
        │ [Reconnect GitHub]                 │
        └─────────────────────────────────────┘

User clicks [Reconnect GitHub]
  → Standard OAuth flow
  → New token stored
  → Tool works again ✓
```

---

## Technical Architecture

### System Components

```
┌───────────────────────────────────────────────────────────────┐
│                     Application Layer                          │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │   Auth     │  │  Identity  │  │Connection  │             │
│  │Middleware  │→ │  Service   │→ │  Manager   │             │
│  └────────────┘  └────────────┘  └────────────┘             │
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ Credential │  │   Token    │  │   Tools    │             │
│  │   Vault    │← │  Refresh   │← │  Layer     │             │
│  │  Service   │  │   Worker   │  │            │             │
│  └────────────┘  └────────────┘  └────────────┘             │
│                                                                │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                      │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  Redis          │  │  AWS Secrets    │                   │
│  │  (Identity Map) │  │  Manager        │                   │
│  │                 │  │  (Token Vault)  │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                                │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  PostgreSQL     │  │  CloudWatch     │                   │
│  │  (Audit Logs)   │  │  (Metrics)      │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### Data Models

**Identity Mapping:**
```python
{
  "cookie:user_123": "alice",
  "oauth:alice@acme.com": "alice",
  "slack:U12345": "alice"
}
```

**Credential Storage (AWS Secrets Manager):**
```json
{
  "SecretId": "user/alice/github",
  "SecretString": {
    "access_token": "gho_encrypted...",
    "refresh_token": "ghr_encrypted...",
    "expires_at": "2026-01-20T18:00:00Z",
    "scopes": ["repo", "read:user"],
    "created_at": "2026-01-20T10:00:00Z"
  }
}
```

**Service Configuration:**
```python
{
  "github": {
    "enabled": true,
    "oauth_client_id": "gh_abc123",
    "oauth_client_secret": "gh_secret_xyz",
    "scopes": ["repo", "read:user"],
    "token_endpoint": "https://github.com/login/oauth/access_token",
    "refresh_endpoint": "https://github.com/login/oauth/access_token"
  }
}
```

### Security Controls

| Control | Implementation |
|---------|----------------|
| **Encryption at Rest** | AWS KMS with customer-managed keys |
| **Encryption in Transit** | TLS 1.3, certificate pinning |
| **Access Control** | IAM roles, principle of least privilege |
| **Audit Logging** | CloudWatch Logs, 1-year retention |
| **Token Rotation** | Automatic refresh, manual revocation |
| **Secret Scanning** | Pre-commit hooks, CI/CD checks |
| **Vulnerability Scanning** | Weekly Dependabot, quarterly pen test |

---

## Success Metrics

### Primary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Adoption Rate** | 80% of active users connect ≥1 service | Weekly active users with connections / WAU |
| **Tool Success Rate** | 95% of tool calls succeed | Successful API calls / Total API calls |
| **Token Refresh Success** | 98% refresh without user intervention | Auto-refreshes succeeded / Total refreshes |

### Secondary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Connection Growth** | 10% MoM | New connections this month / last month |
| **Services per User** | 2.5 avg | Total connections / Total users |
| **Slack Linking Rate** | 60% of Slack users link | Linked Slack users / Total Slack users |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Security Incidents** | 0 | Credential leaks, unauthorized access |
| **P0 Incidents** | <1 per quarter | Vault outages, data loss |
| **Mean Time to Refresh** | <500ms | Avg refresh duration |
| **Vault Availability** | 99.9% | Uptime excluding maintenance |

---

## Out of Scope (V1)

The following are explicitly OUT OF SCOPE for the initial implementation:

1. **Custom OAuth Providers:** Only GitHub, Slack, Google initially
2. **API Key-Based Services:** Only OAuth 2.0 services (no API keys)
3. **On-Premise Integration:** Only cloud-based services
4. **Service-to-Service Auth:** Only user-to-service delegation
5. **Legacy OAuth 1.0:** Only OAuth 2.0 support
6. **Fine-Grained Permissions:** Scopes defined per service, not per user
7. **Connection Sharing:** No team/group shared connections
8. **Approval Workflows:** No admin approval for connections
9. **Connection Templates:** No pre-configured connection bundles
10. **Offline Access:** Tokens work only when user account active

---

## Open Questions

### For Product Management

1. **Prioritization:** Which services to support first? (GitHub, Slack, Google Drive, Salesforce, etc.)
2. **Pricing:** Is this a paid feature or available to all users?
3. **Limits:** Max services per user? Rate limits per service?
4. **Branding:** How to position this vs competitors (Zapier, n8n)?
5. **Support:** What level of support for connection issues?

### For Security

1. **Key Rotation:** How often to rotate encryption keys? Impact on existing tokens?
2. **Compliance:** Any specific compliance requirements beyond SOC 2/GDPR?
3. **Incident Response:** Playbook for credential compromise?
4. **Token Storage:** AWS Secrets Manager vs HashiCorp Vault vs Azure Key Vault?
5. **Audit Requirements:** What audit reports are needed? Frequency?

### For Engineering

1. **Migration:** How to handle existing service accounts currently in use?
2. **Backwards Compatibility:** Any existing integrations that need migration?
3. **Testing:** How to test OAuth flows in dev/staging environments?
4. **Monitoring:** What alerts are critical? Who gets paged?
5. **Rollout:** Phased rollout strategy? Beta users first?

### For UX/Design

1. **Onboarding:** Should we prompt users to connect services on first login?
2. **Discovery:** How do users learn which services are available?
3. **Trust Signals:** How to build user trust around credential storage?
4. **Mobile:** Mobile app support for OAuth flows?
5. **Accessibility:** WCAG 2.1 AA compliance for connection flows?

---

## Implementation Phases

### Phase 1: MVP (Weeks 1-3)
**Goal:** Cookie/OAuth users can connect GitHub

**Deliverables:**
- [ ] Connection Manager (OAuth flow for GitHub)
- [ ] Credential Vault Service (AWS Secrets Manager integration)
- [ ] Token retrieval in tools
- [ ] Basic error handling
- [ ] Settings page (view/disconnect)

**Success Criteria:**
- Cookie/OAuth users can connect GitHub
- Tools can read GitHub repos
- Users can disconnect GitHub
- Zero security incidents

### Phase 2: Enhanced Security & Reliability (Weeks 4-5)
**Goal:** Production-ready security and token lifecycle

**Deliverables:**
- [ ] Token auto-refresh (background job)
- [ ] Comprehensive audit logging
- [ ] Enhanced error handling
- [ ] Monitoring & alerting
- [ ] Security audit & penetration test

**Success Criteria:**
- 98% token refresh success rate
- All access logged
- Alerts firing correctly
- Security audit passed

### Phase 3: Multi-Auth Support (Weeks 6-7)
**Goal:** Slack users can use connected services

**Deliverables:**
- [ ] Identity Service (canonical ID mapping)
- [ ] Slack linking flow (/link-account)
- [ ] Cross-auth-method access
- [ ] Link management UI

**Success Criteria:**
- Slack users can link accounts
- Slack commands work with web-connected services
- 60% of Slack users link accounts

### Phase 4: Scale & Polish (Weeks 8-10)
**Goal:** Support multiple services, scale to all users

**Deliverables:**
- [ ] Additional services (Slack, Google, etc.)
- [ ] Service configuration admin UI
- [ ] Performance optimization (caching)
- [ ] Documentation & runbooks
- [ ] User onboarding flows

**Success Criteria:**
- 3+ services supported
- 80% user adoption
- <100ms token retrieval
- Full documentation

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Credential Leak** | Low | Critical | Encryption, audit logs, secret scanning, pen tests |
| **Token Revocation by Provider** | Medium | Medium | Auto-refresh, user notification, reconnect flow |
| **Vault Outage** | Low | High | Multi-AZ deployment, local caching, degraded mode |
| **OAuth Config Error** | Medium | Medium | Config validation, staging environment testing |
| **User Confusion** | High | Low | Clear UX, onboarding, help docs, support training |
| **Compliance Violation** | Low | Critical | Legal review, security audit, compliance framework |
| **Scale Issues** | Medium | Medium | Load testing, horizontal scaling, managed services |
| **Key Rotation Impact** | Low | Medium | Phased rotation, backward compatibility, monitoring |

---

## Dependencies

### External Dependencies
- AWS Secrets Manager (or equivalent vault service)
- Redis (or equivalent for identity mapping)
- OAuth provider availability (GitHub, Slack, etc.)

### Internal Dependencies
- Existing auth system (Cookie/OAuth/Slack adapters)
- Existing authorization system (Authorizer, ToolPolicy)
- Tool framework (tools need updates to use credentials)

### Team Dependencies
- Security team: Review architecture, approve launch
- Compliance team: Verify GDPR/SOC 2 readiness
- Infrastructure team: Provision AWS resources
- Support team: Training on connection troubleshooting

---

## Appendix A: Competitive Analysis

| Platform | Credential Model | Strengths | Weaknesses |
|----------|------------------|-----------|------------|
| **Zapier** | Per-user OAuth, encrypted vault | Mature, 5000+ integrations | Expensive, closed source |
| **n8n** | Per-user OAuth, self-hosted vault | Open source, self-hosted option | Less polished UX |
| **Make** | Per-user OAuth, encrypted vault | Visual workflow builder | Complex for simple tasks |
| **Workato** | Enterprise OAuth, team credentials | Enterprise features, governance | Very expensive, enterprise only |

**Our Differentiation:**
- Embedded in AI agent platform (vs standalone automation)
- Tool-level abstraction (vs workflow building)
- Multi-auth support (Cookie/OAuth/Slack)

---

## Appendix B: Glossary

- **Canonical ID:** The primary user identifier that all auth methods map to
- **Credential Vault:** Secure storage system for OAuth tokens and credentials
- **Downstream API:** External service (GitHub, Slack) that tools call on user's behalf
- **Identity Linking:** Associating multiple auth methods to one user identity
- **OAuth 2.0:** Industry standard protocol for delegated authorization
- **Principal:** Authenticated user identity with permissions (existing system concept)
- **Refresh Token:** Long-lived token used to obtain new access tokens
- **Scope:** Specific permissions requested during OAuth flow (e.g., "read:repo")
- **Service Connection:** User's authorization for system to access external service
- **Token Exchange:** Process of swapping one token for another (OAuth RFC 8693)
- **STRONG Auth:** Cookie or OAuth authentication (vs WEAK Slack auth)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-20 | Technical Architecture | Initial draft |

---

## Approval Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Manager | | | |
| Engineering Lead | | | |
| Security Lead | | | |
| Compliance Officer | | | |

---

**Next Steps:**
1. Review this document with stakeholders
2. Answer open questions
3. Get approval sign-offs
4. Create engineering tasks and timeline
5. Kick off Phase 1 implementation
