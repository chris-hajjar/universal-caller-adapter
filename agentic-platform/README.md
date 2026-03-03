# Agentic Platform POC

A lightweight multi-tenant agentic platform where a single identity layer (Okta) ties together memory, permissions, and async job execution across any AI client — Claude, GPT, Slack — without the user doing anything special.

One gateway. One memory layer. One permission model. Client-agnostic.

## Architecture

```
[Claude Desktop / Slack Bot]
             |
       Okta (Auth + Scoped Tokens)
             |
       Gateway API (FastAPI)
        |-- Permission enforcement (reads manifest -> gates MCP access)
        |-- Memory middleware (fires async job after every exchange)
        +-- MCP Router (routes to allowed servers only)
             |                        |                      |
     MariaDB MCP Server       Memory MCP Server         BackgroundTasks
     (OSS, dumb executor)     (OSS, search + store)          |
                                     |                  Embed + Write
                                Supabase pgvector        (OpenAI API)
                             (user-namespaced)
```

## What You Need (Accounts)

| Service | Purpose | Signup |
|---------|---------|--------|
| **Okta Developer** | JWT auth, user attributes for permission manifests | https://developer.okta.com/signup/ |
| **Railway** | Hosted MariaDB (business data) | https://railway.app |
| **Supabase** | Hosted pgvector (conversation memory) | https://supabase.com |
| **OpenAI** | Embedding API for memory | https://platform.openai.com |
| **Slack** (optional) | Slack bot integration | https://api.slack.com/apps |

---

## Step-by-Step Setup

### Step 1 — Okta Developer Account (15 min)

1. **Sign up** at https://developer.okta.com/signup/
   - You get a free developer org (e.g., `dev-12345678.okta.com`)

2. **Create an API Services application:**
   - Okta Admin Console → Applications → Create App Integration
   - Choose **API Services** (machine-to-machine)
   - Name it `agentic-gateway`
   - Note the **Client ID**

3. **Create an Authorization Server** (or use `default`):
   - Security → API → Authorization Servers
   - Note the **Issuer URI** (e.g., `https://dev-12345678.okta.com/oauth2/default`)
   - Add a custom scope: `mcp.access`

4. **Create 3 test users:**
   - Directory → People → Add Person
   - Create:
     - `chris@company.com` (Owner)
     - `user_a@company.com` (Standard)
     - `user_b@company.com` (Limited)
   - Set passwords for each

5. **Add a custom user attribute for permission manifests:**
   - Directory → Profile Editor → Select "User (default)"
   - Click **Add Attribute**
   - Display name: `MCP Permissions`
   - Variable name: `mcp_permissions`
   - Data type: **string**
   - Save

6. **Set the permission manifests on each user:**
   - Directory → People → select user → Profile → Edit

   **Chris (Owner):** Leave `mcp_permissions` blank — owner has implicit full access

   **User A:** Set `mcp_permissions` to:
   ```json
   {"user_id":"user_a@company.com","role":"standard","mcp_servers":{"mariadb":{"enabled":true,"scope":"read_only","tables":["invoices","orders","products"]},"memory":{"enabled":true,"scope":"read_write"},"slack":{"enabled":true,"scope":"read_write"},"reports":{"enabled":false,"scope":"read_only"}}}
   ```

   **User B:** Set `mcp_permissions` to:
   ```json
   {"user_id":"user_b@company.com","role":"limited","mcp_servers":{"mariadb":{"enabled":true,"scope":"read_only","tables":["invoices"]},"memory":{"enabled":true,"scope":"read_write"},"slack":{"enabled":false,"scope":"read_only"},"reports":{"enabled":false,"scope":"read_only"}}}
   ```

7. **Get an API token** (for the admin UI to read/write user attributes):
   - Security → API → Tokens → Create Token
   - Name: `agentic-gateway-admin`
   - Copy the token value (starts with `00...`)

**What you have now:**
- `OKTA_DOMAIN` = `dev-12345678.okta.com`
- `OKTA_CLIENT_ID` = from the app you created
- `OKTA_API_TOKEN` = the SSWS token
- `OWNER_EMAIL` = `chris@company.com`

### Step 2 — Railway MariaDB (5 min)

1. **Sign up** at https://railway.app
2. **New Project → Add Service → Database → MariaDB**
3. **Click the MariaDB service → Settings → Connection**
4. Copy these values:
   - `MARIADB_HOST` (e.g., `roundhouse.proxy.rlwy.net`)
   - `MARIADB_PORT` (e.g., `38271`)
   - `MARIADB_USER` (usually `root`)
   - `MARIADB_PASSWORD`
   - `MARIADB_DATABASE` (usually `railway`)

### Step 3 — Supabase pgvector (5 min)

1. **Sign up** at https://supabase.com
2. **New Project** — pick a name and password
3. **Enable pgvector:**
   - SQL Editor → New query → Run:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
4. **Get credentials:**
   - Settings → API
   - `SUPABASE_URL` = Project URL (e.g., `https://abc123.supabase.co`)
   - `SUPABASE_SERVICE_KEY` = service_role key (the long one, NOT the anon key)

### Step 4 — OpenAI API Key (2 min)

1. Go to https://platform.openai.com/api-keys
2. Create a new key
3. Copy it → `OPENAI_API_KEY`

### Step 5 — Configure .env

```bash
cd agentic-platform
cp .env.example .env
```

Fill in every value in `.env`:

```
# Okta
OKTA_DOMAIN=dev-12345678.okta.com
OKTA_AUDIENCE=api://default
OKTA_CLIENT_ID=your_client_id
OKTA_API_TOKEN=your_ssws_token
OWNER_EMAIL=chris@company.com

# MariaDB (Railway)
MARIADB_HOST=roundhouse.proxy.rlwy.net
MARIADB_PORT=38271
MARIADB_USER=root
MARIADB_PASSWORD=your_password
MARIADB_DATABASE=railway

# Supabase
SUPABASE_URL=https://abc123.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

# OpenAI
OPENAI_API_KEY=sk-...

# Gateway
GATEWAY_URL=http://localhost:8000
GATEWAY_PORT=8000
```

### Step 6 — Install Dependencies

```bash
cd agentic-platform
pip install -r requirements.txt
```

### Step 7 — Seed the Databases

```bash
# Seed MariaDB with fake business data (invoices, orders, users, products, reports)
python -m seed.mariadb_seed

# Set up Supabase pgvector (memories table + search function)
python -m seed.supabase_seed
```

MariaDB gets 5 tables with ~10 rows each. Supabase gets a `memories` table with a vector similarity search function.

### Step 8 — Start the Gateway

```bash
uvicorn gateway.main:app --reload --port 8000
```

Test it:
```bash
# Health check (no auth)
curl http://localhost:8000/health

# Whoami as User B (dev mode uses email as token)
curl -H "Authorization: Bearer user_b@company.com" http://localhost:8000/whoami

# Try a blocked call — User B querying orders table
curl -X POST http://localhost:8000/mcp/call \
  -H "Authorization: Bearer user_b@company.com" \
  -H "Content-Type: application/json" \
  -d '{"server_name":"mariadb","tool_name":"query","arguments":{"query":"SELECT * FROM orders"}}'
# → 403: Access denied: table 'orders' is not in your allowed tables

# Try an allowed call — User B querying invoices
curl -X POST http://localhost:8000/mcp/call \
  -H "Authorization: Bearer user_b@company.com" \
  -H "Content-Type: application/json" \
  -d '{"server_name":"mariadb","tool_name":"query","arguments":{"query":"SELECT * FROM invoices"}}'
# → Routed to MariaDB MCP server
```

### Step 9 — Start the Admin UI

```bash
streamlit run admin/app.py
```

Opens at http://localhost:8501. You'll see:
1. **User list** — all 3 users with their roles and enabled MCPs
2. **Permission grid** — click a user to expand. Toggle servers, check/uncheck MariaDB tables, change read/write scope
3. **Live manifest preview** — JSON that gets written to Okta when you save

Changes save to Okta immediately. Gateway picks them up on the next request.

### Step 10 — Connect Claude Desktop

```bash
# Generate config for User B
python scripts/claude_config_swap.py user_b

# Or for the owner
python scripts/claude_config_swap.py owner
```

This writes a Claude Desktop config that points to the MCP proxy, which forwards all tool calls through the gateway with the user's auth token.

Restart Claude Desktop after swapping configs.

### Step 11 — Start the Slack Bot (optional)

First, create a Slack app:
1. https://api.slack.com/apps → Create New App → From scratch
2. Enable **Socket Mode** (Settings → Socket Mode → Enable)
3. Add **Bot Token Scopes**: `chat:write`, `app_mentions:read`, `im:history`, `im:read`, `im:write`
4. Install to workspace
5. Copy `SLACK_BOT_TOKEN` (xoxb-...) and `SLACK_APP_TOKEN` (xapp-...)

Configure user mapping in `.env`:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_USER_MAP={"U01ABC123":"user_a@company.com","U02DEF456":"user_b@company.com"}
```

Start the bot:
```bash
python -m slack_bot.app
```

---

## Test Users & Permission Matrix

|               | Chris (Owner)     | User A                                   | User B                      |
|---------------|-------------------|------------------------------------------|-----------------------------|
| **MariaDB**   | All tables, R+W   | invoices, orders, products — read only   | invoices only — read only   |
| **Memory MCP**| Enabled           | Enabled                                  | Enabled                     |
| **Slack MCP** | Enabled           | Enabled                                  | Disabled                    |
| **Reports**   | Enabled           | Disabled                                 | Disabled                    |

## Demo Script

1. Open Streamlit at http://localhost:8501 — show the MCP grid across all 3 users
2. Show User B has only `invoices` checked, Slack MCP off
3. Switch to `user_b` config in Claude Desktop
4. Query orders table → **blocked**. Query invoices → **works**
5. Uncheck invoices for User B live in Streamlit → query again → **now blocked**
6. Switch to `user_a` → query products → **works**
7. Open Supabase dashboard → show `memories` table populating as you chat
8. Chat in Slack as User B → switch to Claude Desktop → **context carries over**

## Dev Mode (No Okta)

If you leave `OKTA_DOMAIN` blank in `.env`, the gateway runs in dev mode:
- Tokens are treated as email addresses (`Bearer user_b@company.com`)
- Permission manifests are loaded from hardcoded defaults
- No JWT verification
- Admin UI saves locally (doesn't persist across restarts)

This is useful for testing the permission logic without setting up Okta.

## Running Tests

```bash
cd agentic-platform
python -m pytest tests/ -v
```

All 39 tests run in dev mode (no external services needed).

## File Structure

```
agentic-platform/
├── gateway/
│   ├── main.py            # FastAPI gateway — all endpoints
│   ├── auth.py            # Okta JWT validation + manifest loading
│   ├── permissions.py     # Permission enforcement (server, table, SQL)
│   ├── mcp_router.py      # Routes tool calls to backend MCP servers
│   ├── memory.py          # Async memory sync (OpenAI embed → Supabase)
│   └── models.py          # Pydantic models
├── admin/
│   └── app.py             # Streamlit admin UI
├── slack_bot/
│   └── app.py             # Bolt for Python Slack bot
├── scripts/
│   ├── mcp_proxy.py       # MCP stdio proxy for Claude Desktop
│   └── claude_config_swap.py  # Config swap per test user
├── seed/
│   ├── mariadb_seed.py    # Seed MariaDB (5 tables, ~10 rows each)
│   └── supabase_seed.py   # Set up pgvector (memories table + search fn)
└── tests/
    ├── test_gateway.py    # Gateway endpoint tests
    ├── test_permissions.py # Permission enforcement tests (25 tests)
    └── test_memory.py     # Memory sync tests
```
