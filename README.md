# Universal Caller Adapter - POC

A proof-of-concept demonstrating how multiple authentication entry points (Platform, OAuth, Slack) can be normalized into a single canonical caller model and enforced through one centralized authorization layer.

## Overview

This POC validates that:
- Different authentication mechanisms can coexist
- They can be normalized into a single `Principal`
- Authorization can be enforced once, centrally, before tool execution
- Tools do not need to know about authentication

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Entry Points                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Cookie  │  │  OAuth   │  │  Slack   │  │Anonymous │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │   Auth Middleware         │
        │  (Tries adapters in order)│
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │      Principal            │
        │  ┌──────────────────────┐ │
        │  │ principal_id         │ │
        │  │ tenant_id            │ │
        │  │ auth_method          │ │
        │  │ auth_strength        │ │
        │  │ entitlements         │ │
        │  └──────────────────────┘ │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │    Authorizer             │
        │  (Centralized policies)   │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │    Tools                  │
        │  (Auth-agnostic)          │
        └───────────────────────────┘
```

## Project Structure

```
universal-caller-adapter/
├── src/
│   ├── models/
│   │   └── principal.py          # Canonical Principal model
│   ├── adapters/
│   │   ├── base.py               # AuthAdapter interface
│   │   ├── cookie.py             # Platform cookie auth
│   │   ├── oauth.py              # OAuth/OIDC JWT auth
│   │   └── slack.py              # Slack signature auth
│   ├── auth/
│   │   └── authorizer.py         # Centralized authorization
│   ├── middleware/
│   │   └── auth.py               # Auth middleware
│   └── tools/
│       ├── rag_search.py         # Sample tool: RAG search
│       └── diagnostics.py        # Sample tool: diagnostics
├── main.py                        # FastAPI application
├── run_demo.py                    # Consolidated demo runner (starts server automatically)
├── simple_demo.py                 # Educational demo with explanations
├── demo.py                        # Comprehensive demo script
├── requirements.txt
└── README.md
```

## Key Components

### 1. Principal (Canonical Caller Model)

The single representation of "who is calling":

```python
@dataclass
class Principal:
    principal_id: str
    tenant_id: Optional[str]
    auth_method: AuthMethod  # cookie | oauth | slack | anonymous
    auth_strength: AuthStrength  # strong | weak | anonymous
    entitlements: Set[str]
```

### 2. Authentication Adapters

Each adapter normalizes a different entry point to a Principal:

- **CookieAdapter**: Platform session cookies → Principal (STRONG)
- **OAuthAdapter**: JWT tokens → Principal (STRONG)
- **SlackAdapter**: Slack signatures → Principal (WEAK)
- **Fallback**: No auth → Anonymous Principal

### 3. Centralized Authorization

Single place where authorization decisions are made:

```python
class Authorizer:
    def authorize(self, principal: Principal, tool_name: str):
        # Check auth strength
        # Check entitlements
        # Raise AuthorizationError if failed
```

Tool policies define requirements:

```python
ToolPolicy(
    tool_name="diagnostics",
    required_entitlements={"diag:read"},
    min_auth_strength=AuthStrength.STRONG  # Blocks Slack
)
```

### 4. Auth-Agnostic Tools

Tools receive a Principal and assume authorization already happened:

```python
async def diagnostics(principal: Principal) -> Dict[str, Any]:
    # No auth logic - just business logic
    return {"system_info": "..."}
```

## Running the POC

### 1. Install Dependencies

```bash
cd universal-caller-adapter
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Demo (Easy Mode)

The easiest way to run the demos is using the consolidated demo runner, which automatically starts the server:

```bash
python run_demo.py
```

This will:
- Automatically start the server in the background
- Present you with a menu to choose which demo to run:
  1. **Simple Educational Demo** - Interactive, step-by-step walkthrough with explanations
  2. **Comprehensive Demo** - Automated demonstration of all scenarios
  3. **Both Demos** - Run both in sequence
  4. **Interactive Playground** - Experiment with different auth methods and tool calls
- Clean up the server when done

You can also run specific demos directly:

```bash
python run_demo.py --simple      # Run educational demo only
python run_demo.py --full        # Run comprehensive demo only
python run_demo.py --both        # Run both demos
python run_demo.py --playground  # Run interactive playground mode
```

**Interactive Playground Mode:**

The playground mode lets you experiment with the Universal Caller Adapter by:
- Selecting different authentication methods (Cookie, OAuth, Slack, Anonymous)
- Choosing which tool to call (whoami, rag-search, diagnostics)
- Seeing the exact request details (headers, cookies, body)
- Viewing real-time server responses
- Understanding why requests succeed or fail based on auth strength and entitlements

This is perfect for exploring authorization behaviors and understanding how different auth methods interact with tool policies.

### 3. Manual Server Management (Alternative)

If you prefer to manage the server manually:

**Start the server:**
```bash
python main.py
```

**Run demos** (in separate terminals):
```bash
python simple_demo.py    # Educational demo
python demo.py           # Comprehensive demo
```

The demo scripts will:
1. Show each auth method resolving to a Principal
2. Call tools via different entry points
3. Demonstrate Slack being blocked from sensitive tools
4. Show consistent authorization behavior

### 4. Manual Testing

You can also test manually with curl:

**Cookie Auth:**
```bash
curl -X POST http://localhost:8000/tools/rag-search \
  -H "Content-Type: application/json" \
  -b "session_id=sess_alice_123" \
  -d '{"query": "test"}'
```

**OAuth Auth:**
```bash
# First, generate a token (using Python):
python -c "
import jwt
from datetime import datetime, timedelta
token = jwt.encode({
    'sub': 'user_test',
    'role': 'admin',
    'tenant_id': 'acme',
    'exp': datetime.utcnow() + timedelta(hours=1)
}, 'demo-secret-key', algorithm='HS256')
print(token)
"

# Then use it:
curl -X POST http://localhost:8000/tools/rag-search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "test"}'
```

**Slack Auth:**
```bash
curl -X POST http://localhost:8000/tools/rag-search \
  -H "Content-Type: application/json" \
  -H "x-slack-signature: v0=abc123" \
  -H "x-slack-request-timestamp: $(date +%s)" \
  -H "x-slack-user-id: U01ABC123" \
  -d '{"query": "test"}'
```

## Demo Scenarios

The demo validates:

### ✅ Scenario 1: All entry points normalize to Principal
- Cookie, OAuth, Slack, Anonymous all resolve to same structure
- `/whoami` endpoint shows the resolved Principal

### ✅ Scenario 2: Consistent authorization
- Same tool called via different auth methods
- Authorization logic is identical regardless of entry point

### ✅ Scenario 3: Auth strength enforcement
- `rag_search`: Allows WEAK auth (Slack ✓)
- `diagnostics`: Requires STRONG auth (Slack ✗)

### ✅ Scenario 4: Entitlement enforcement
- Users without `diag:read` blocked from diagnostics
- Users without `rag:read` blocked from RAG search

### ✅ Scenario 5: Tools are auth-agnostic
- Tools receive Principal
- No auth/authz logic inside tools
- Clean separation of concerns

## Success Criteria

- [x] All entry points resolve to a Principal
- [x] Authorization behavior is consistent across entry points
- [x] Tools remain auth-agnostic
- [x] Architectural pattern is clear in <1-minute demo

## API Endpoints

### `GET /`
API information and available endpoints.

### `GET /whoami`
Show the resolved Principal for the current request.

### `POST /tools/rag-search`
Search RAG knowledge base.
- **Requires**: `rag:read` entitlement
- **Min auth**: WEAK (Slack allowed)

### `POST /tools/diagnostics`
System diagnostics.
- **Requires**: `diag:read` entitlement
- **Min auth**: STRONG (Slack blocked)

## Extending the POC

### Adding a New Auth Method

1. Create a new adapter in `src/adapters/`:

```python
class NewAdapter(AuthAdapter):
    async def can_handle(self, request: Request) -> bool:
        # Detect if this is your auth method
        pass

    async def authenticate(self, request: Request) -> Optional[Principal]:
        # Extract credentials, validate, return Principal
        pass
```

2. Register it in `main.py`:

```python
new_adapter = NewAdapter()
app.add_middleware(
    AuthMiddleware,
    adapters=[cookie_adapter, oauth_adapter, slack_adapter, new_adapter]
)
```

### Adding a New Tool

1. Create tool in `src/tools/`:

```python
async def my_tool(principal: Principal, ...) -> Dict[str, Any]:
    # Business logic only - no auth
    return {...}
```

2. Define policy in `main.py`:

```python
authorizer.register_policy(ToolPolicy(
    tool_name="my_tool",
    required_entitlements={"my:permission"},
    min_auth_strength=AuthStrength.STRONG
))
```

3. Create endpoint:

```python
@app.post("/tools/my-tool")
async def invoke_my_tool(request: Request):
    principal = get_principal(request)
    authorizer.authorize(principal, "my_tool")
    result = await my_tool(principal)
    return ToolResponse(success=True, data=result)
```

## Open Challenges for Wide-Scale Adoption

While this POC demonstrates a unified authentication architecture, several design challenges require deeper consideration for production deployment at scale:

1. **Entitlements & Policy Model**: String-based entitlements (`{"rag:read"}`) lack hierarchy, resource-level scoping, and conditional logic. Real systems need policy-as-code with tenant-scoped permissions, temporal constraints, and the ability to express "read docs in tenant A, write docs in tenant B" without code changes.

2. **Auth Strength Model**: The three-tier strength model (ANONYMOUS/WEAK/STRONG) oversimplifies authentication quality. Production systems need to distinguish password-only from MFA-backed sessions, support step-up authentication for sensitive operations, and handle certificate-based auth which is stronger than password-based OAuth but currently both would be "STRONG".

3. **Multi-Tenancy Isolation**: While `tenant_id` exists in the Principal model, it's not validated during authorization checks. Wide-scale deployments need architectural patterns for enforcing tenant boundaries at the authorization layer to prevent cross-tenant access even when entitlements match.

4. **Token Lifecycle & Distributed State**: Missing refresh, revocation, and session timeout capabilities create architectural questions about distributed state management. How should token blacklists work across multiple instances? How to handle cache invalidation when policies change? These require distributed systems design decisions beyond simple implementation.

## Non-Goals (Out of Scope for POC)

- Production-grade IAM
- Full SSO or enterprise identity integration
- Long-term token lifecycle management
- UI or end-user workflows
- Comprehensive error handling
- Logging and monitoring
- Rate limiting
- RBAC/ABAC extensions

## License

This project is open source and available for all users and implementations. Feel free to use, modify, and adapt this pattern for your own projects. Contributions and feedback are welcome!
