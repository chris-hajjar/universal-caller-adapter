# Agentic Platform POC

A lightweight multi-tenant agentic platform where a single identity layer (Okta) ties together memory, permissions, and async job execution across any AI client — Claude, GPT, Slack — without the user doing anything special.

**One gateway. One memory layer. One permission model. Client-agnostic.**

## Architecture

```
[Claude Desktop / Slack Bot]
             ↓
       Okta (Auth + Scoped Tokens)
             ↓
       Gateway API (FastAPI)
        ├── Permission enforcement (reads manifest → gates MCP access)
        ├── Memory middleware (fires async job after every exchange)
        └── MCP Router (routes to allowed servers only)
             ↓                        ↓                      ↓
     MariaDB MCP Server       Memory MCP Server         BackgroundTasks
     (OSS, dumb executor)     (OSS, search + store)          ↓
                                     ↓                  Embed + Write
                                Supabase pgvector        (OpenAI API)
                             (user-namespaced)
```

## Test Users

| | Chris (Owner) | User A | User B |
|---|---|---|---|
| **MariaDB** | All tables, R+W | invoices, orders, products — read only | invoices only — read only |
| **Memory MCP** | Yes | Yes | Yes |
| **Slack MCP** | Yes | Yes | No |
| **Reports MCP** | Yes | No | No |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for `npx mcp-remote`)
- Accounts set up per `SETUP_CHECKLIST.md`

### Step 1: Clone and install

```bash
cd agentic-platform-poc
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Step 2: Configure environment

```bash
cp .env.example .env
# Edit .env with your actual credentials (see SETUP_CHECKLIST.md)
```

### Step 3: Seed the databases

**MariaDB** (Railway):
```bash
# Make sure MARIADB_* vars are set in .env
source .env  # or use python-dotenv
python scripts/seed_mariadb.py
```

**Supabase** (pgvector):
1. Open the Supabase SQL Editor
2. Paste and run the contents of `scripts/seed_supabase.sql`

### Step 4: Start the Gateway

```bash
# Load env vars
export $(grep -v '^#' .env | xargs)

# Start the gateway in dev mode
uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

The gateway runs at `http://localhost:8000`. Verify with:
```bash
curl http://localhost:8000/health
```

### Step 5: Start MCP servers

Start the OSS MCP servers that the gateway routes to. Each runs as a separate process:

```bash
# MariaDB MCP (example — use whichever OSS server you choose)
# Runs on port 8001
npx mysql-mcp-server --host $MARIADB_HOST --port $MARIADB_PORT \
  --user $MARIADB_USER --password $MARIADB_PASSWORD --database $MARIADB_DATABASE \
  --listen 8001

# Memory MCP (Supabase)
# Runs on port 8002
npx supabase-mcp-server --url $SUPABASE_URL --key $SUPABASE_SERVICE_KEY \
  --listen 8002
```

### Step 6: Run the integration tests

```bash
python scripts/test_gateway.py
```

This tests all three users against the gateway and verifies:
- Chris (owner) can access everything
- User A is blocked from reports and users tables
- User B is blocked from orders, products, and Slack
- Write operations are blocked for read-only users

### Step 7: Set up Claude Desktop

Copy the config for the user you want to test as:

```bash
# Option A: Use the swap script
python scripts/swap_claude_config.py chris    # or user_a, user_b

# Option B: Manually copy a config
cp claude_configs/user_b_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Restart Claude Desktop. The MCP servers in Claude now route through the gateway.

### Step 8: Start the Slack Bot

```bash
export $(grep -v '^#' .env | xargs)
python -m slack_bot.app
```

The bot runs in Socket Mode. Mention it in a channel or DM it:
- `query invoices` → routes through gateway as the Slack user's identity
- `search memory for shipping delays` → semantic search on user's memories

### Step 9: Start the Admin UI

```bash
export $(grep -v '^#' .env | xargs)
streamlit run admin_ui/app.py
```

Opens at `http://localhost:8501`. From here you can:
1. See all users and their current permissions
2. Toggle MCP server access per user
3. Expand MariaDB to check/uncheck individual tables
4. Set read-only vs read-write scope
5. See the live JSON manifest that will be written to Okta
6. Save — takes effect on the gateway's next request (no restart)

---

## Project Structure

```
agentic-platform-poc/
├── gateway/                  # FastAPI gateway (the brain)
│   ├── main.py              # Routes, endpoints, BackgroundTasks
│   ├── auth.py              # Okta JWT validation + dev mode
│   ├── permissions.py       # Permission engine + manifest loading
│   ├── mcp_router.py        # Routes requests to MCP servers
│   ├── memory.py            # Async embed + store to pgvector
│   └── okta_client.py       # Okta Management API wrapper
├── admin_ui/
│   └── app.py               # Streamlit admin dashboard
├── slack_bot/
│   └── app.py               # Bolt for Python Slack bot
├── scripts/
│   ├── seed_mariadb.py      # Create tables + fake data
│   ├── seed_supabase.sql    # pgvector schema + RPC function
│   ├── swap_claude_config.py # Switch Claude Desktop user
│   └── test_gateway.py      # Integration test suite
├── manifests/                # Dev mode permission manifests
│   ├── chris_at_company.com.json
│   ├── user_a_at_company.com.json
│   └── user_b_at_company.com.json
├── claude_configs/           # Pre-built Claude Desktop configs
│   ├── chris_config.json
│   ├── user_a_config.json
│   └── user_b_config.json
├── mcp_servers/              # OSS MCP server notes
├── .env.example              # All required env vars
├── requirements.txt          # Python dependencies
├── SETUP_CHECKLIST.md        # External account setup guide
└── README.md                 # This file
```

## Demo Script

1. Open Streamlit — show the MCP grid across all 3 users
2. Show User B has only invoices checked, Slack MCP off
3. Switch to user_b config in Claude Desktop
4. Query orders table → **blocked**. Query invoices → **works**
5. Uncheck invoices for User B live in Streamlit → query again → **now blocked**
6. Switch to user_a → query products → **works**
7. Open Supabase → show memories table populating as you chat
8. Chat in Slack as User B → switch to Claude Desktop → **context carries over**

## Two Validation Moments

**Moment 1 — Permission Enforcement**: Three users, same MariaDB MCP server, three different table-level outcomes. Gateway enforced it. MCP server unchanged.

**Moment 2 — Cross-Client Memory**: Agent remembers a Slack conversation when you open Claude Desktop. User did nothing. Memory synced invisibly.
