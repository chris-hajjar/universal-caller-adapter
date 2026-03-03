# External Setup Checklist

Everything you need to set up **outside of the code** before the POC runs.

---

## 1. Okta Developer Account

- [ ] Sign up at [developer.okta.com](https://developer.okta.com/signup/)
- [ ] Create a new **Web Application** in Okta
  - Sign-in redirect URI: `http://localhost:8000/callback` (not used in POC, but required)
  - Sign-out redirect URI: `http://localhost:8000`
  - Grant types: Authorization Code, Client Credentials
- [ ] Note your **Okta Domain** (e.g. `dev-12345678.okta.com`)
- [ ] Create an **API Token** (Security → API → Tokens → Create Token)
- [ ] Add a custom **user profile attribute** called `agentic_manifest` (type: string, no character limit)
  - Directory → Profile Editor → User (default) → Add Attribute
- [ ] Create 3 test users:
  - `chris@company.com` — will be the owner
  - `user_a@company.com` — limited user
  - `user_b@company.com` — limited user
- [ ] Set the `agentic_manifest` attribute for each user:
  - Chris: `{"user_id": "chris@company.com", "role": "owner", "mcp_servers": {...}}`
  - User A & B: copy from `manifests/` directory

**Env vars to collect:**
```
OKTA_DOMAIN=dev-XXXXXXXX.okta.com
OKTA_AUDIENCE=api://default
OKTA_ISSUER=https://dev-XXXXXXXX.okta.com/oauth2/default
OKTA_API_TOKEN=00xxxxxxxxx
```

---

## 2. Railway MariaDB

- [ ] Sign up at [railway.app](https://railway.app)
- [ ] Create a new project → Add a **MariaDB** database
- [ ] Wait for provisioning (usually < 1 minute)
- [ ] Go to the database → **Connect** tab → copy connection details

**Env vars to collect:**
```
MARIADB_HOST=containers-us-west-XXX.railway.app
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=<from Railway>
MARIADB_DATABASE=railway
```

**After connecting:** Run `python scripts/seed_mariadb.py` to create tables and seed data.

---

## 3. Supabase (pgvector)

- [ ] Sign up at [supabase.com](https://supabase.com)
- [ ] Create a new project (choose a region close to you)
- [ ] Wait for database provisioning
- [ ] Go to **SQL Editor** → paste and run `scripts/seed_supabase.sql`
  - This creates the `memories` table, vector index, and similarity search function
- [ ] Go to **Settings → API** → copy the Project URL and service_role key

**Env vars to collect:**
```
SUPABASE_URL=https://xxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs...
```

---

## 4. OpenAI API Key

- [ ] Sign up / log in at [platform.openai.com](https://platform.openai.com)
- [ ] Create an API key (Settings → API Keys)
- [ ] Ensure you have credits / billing set up (embedding calls cost ~$0.001 per call)

**Env vars to collect:**
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

## 5. Slack App (for Slack Bot)

- [ ] Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From Scratch
- [ ] Name: `Agentic Platform Bot` (or whatever you prefer)
- [ ] Pick your workspace
- [ ] Enable **Socket Mode** (Settings → Socket Mode → Enable)
  - Generate an **App-Level Token** with `connections:write` scope
- [ ] Add **Bot Token Scopes** (OAuth & Permissions → Scopes):
  - `app_mentions:read`
  - `chat:write`
  - `im:history`
  - `im:read`
  - `im:write`
  - `users:read`
  - `users:read.email`
- [ ] Enable **Events** (Event Subscriptions → Enable):
  - Subscribe to bot events: `app_mention`, `message.im`
- [ ] Install the app to your workspace
- [ ] Copy the **Bot User OAuth Token** (`xoxb-...`)
- [ ] Copy the **App-Level Token** (`xapp-...`)

**Env vars to collect:**
```
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-x-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 6. Claude Desktop

- [ ] Install Claude Desktop ([claude.ai/download](https://claude.ai/download))
- [ ] Ensure Node.js 18+ is installed (for `npx mcp-remote`)
- [ ] No API key needed — Claude Desktop handles auth natively

**Config location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/claude/claude_desktop_config.json`

Pre-built configs are in `claude_configs/`. Swap with:
```bash
python scripts/swap_claude_config.py user_b
```

---

## 7. Python Environment

- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed (for MCP server tooling)
- [ ] `pip install -r requirements.txt`

---

## Summary — All Env Vars

Once you have everything, your `.env` should contain:

```env
GATEWAY_DEV_MODE=true

OKTA_DOMAIN=dev-XXXXXXXX.okta.com
OKTA_AUDIENCE=api://default
OKTA_ISSUER=https://dev-XXXXXXXX.okta.com/oauth2/default
OKTA_API_TOKEN=00xxxxxxxxx

MARIADB_HOST=containers-us-west-XXX.railway.app
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=<from Railway>
MARIADB_DATABASE=railway

SUPABASE_URL=https://xxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs...

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

MCP_MARIADB_URL=http://localhost:8001
MCP_MEMORY_URL=http://localhost:8002
MCP_SLACK_URL=http://localhost:8003
MCP_REPORTS_URL=http://localhost:8004

SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

GATEWAY_URL=http://localhost:8000
OWNER_EMAIL=chris@company.com
```

---

## Estimated Setup Time

| Service | Time |
|---------|------|
| Okta Developer | 15–20 min (account + app + custom attribute + 3 users) |
| Railway MariaDB | 5 min |
| Supabase pgvector | 5–10 min (project + SQL setup) |
| OpenAI API key | 2 min |
| Slack App | 10–15 min (scopes + socket mode + install) |
| Claude Desktop | 5 min |
| **Total** | **~45–60 min** |
