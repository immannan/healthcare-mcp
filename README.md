# Healthcare MCP + A2A Server (Mock)

A sample project demonstrating the **Model Context Protocol (MCP)** and **Agent-to-Agent (A2A) communication** for the health insurance claims domain.

- **`mcp_server/`** — FastMCP server exposing 8 healthcare tools
- **`a2a/`** — Custom A2A protocol with 4 specialized agents that coordinate over JSON-RPC 2.0
- **`run_a2a.py`** — Standalone HTTP server that runs all agents together

All data is synthetic — no real PHI, no external calls.

> **Official A2A SDK**: The [`a2a-sdk`](https://pypi.org/project/a2a-sdk/) (v1.0.1+) is now the official Python library for the A2A protocol. This project contains a custom implementation built for training purposes.

---

## Project Structure

```
healthcare-mcp/
├── mcp_server/                  # MCP server
│   ├── __init__.py
│   └── server.py                # FastMCP with 8 healthcare tools
├── a2a/                         # A2A protocol implementation
│   ├── __init__.py
│   ├── message.py               # JSON-RPC 2.0 message types
│   ├── a2a_protocol.py          # Protocol engine, registry, routing
│   └── agents.py                # 4 healthcare domain agents
├── run_a2a.py                   # Standalone A2A HTTP server
├── test_a2a_communication.py    # A2A protocol tests (40 tests)
├── diagrams/
│   ├── mcp.mmd                  # MCP Gateway architecture
│   └── a2a.mmd                  # A2A messaging pattern
├── requirements.txt
└── pytest.ini
```

---

## Setup

**Prerequisites:** Python 3.10+

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running the MCP Server

The MCP server exposes healthcare tools to any MCP-compatible client.

### stdio (default — for MCP clients)

```bash
python mcp_server/server.py
```

### Streamable HTTP

```bash
export MCP_TRANSPORT=streamable-http
export FASTMCP_HOST=127.0.0.1
export FASTMCP_PORT=8000
python mcp_server/server.py
```

Endpoint: `http://127.0.0.1:8000/mcp`

### SSE

```bash
export MCP_TRANSPORT=sse
python mcp_server/server.py
```

### MCP Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio`, `streamable-http`, or `sse` |
| `FASTMCP_HOST` | `127.0.0.1` | Bind host for HTTP transports |
| `FASTMCP_PORT` | `8000` | Bind port for HTTP transports |
| `FASTMCP_STREAMABLE_HTTP_PATH` | `/mcp` | URL path for streamable-http endpoint |
| `MCP_MOUNT_PATH` | _(none)_ | Optional mount path prefix |

---

## Running the A2A Server

The A2A server starts all four healthcare agents and exposes them over HTTP. It uses a local MCP client that calls the MCP tool functions in-process — no separate MCP server required.

```bash
python run_a2a.py
```

The server starts on `http://127.0.0.1:8001` by default.

### A2A Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `A2A_HOST` | `127.0.0.1` | Bind host |
| `A2A_PORT` | `8001` | Bind port |

### A2A Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/.well-known/agent.json` | Agent card — capabilities and metadata for discovery |
| `GET` | `/agents` | List all registered agents |
| `POST` | `/` | Receive an A2A JSON-RPC 2.0 message |

### Example: Discover agents

```bash
curl http://127.0.0.1:8001/.well-known/agent.json | python -m json.tool
```

### Example: Send an A2A message

```bash
curl -s -X POST http://127.0.0.1:8001/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "check_member_eligibility",
    "params": {"member_id": "M-1001"},
    "id": "req-001",
    "sender": "external-client",
    "recipient": "claims-agent",
    "type": "request"
  }' | python -m json.tool
```

---

## MCP Tools

### Claims

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_member_claims` | `member_id`, `status?` | List claims, optionally filtered by `paid`/`pending`/`denied` |
| `get_claim_detail` | `claim_id` | Full claim with member, provider, and adjudication amounts |
| `submit_claim_inquiry` | `claim_id`, `inquiry_type`, `note` | Submit an inquiry ticket |

### Benefits

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_member_benefits` | `member_id` | Deductible and OOP balances for the member's plan |
| `estimate_member_responsibility` | `member_id`, `procedure_code`, `billed_amount`, `network?` | Cost-sharing estimate |

### Providers & Authorizations

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_providers` | `specialty`, `zip_code?`, `network?` | Search providers by specialty |
| `create_prior_authorization` | `member_id`, `provider_id`, `procedure_codes`, `service_date`, `diagnosis_codes?` | Submit prior auth request |
| `get_prior_authorization_status` | `auth_id` | Fetch current status of a prior auth |

---

## A2A Agent System

### Agents

| Agent | ID | Role |
|-------|----|------|
| `MemberAssistAgent` | `member-assist-agent` | Patient coordinator — checks eligibility, finds providers |
| `ClaimsAgent` | `claims-agent` | Claims processor — eligibility, claim history, cost estimates |
| `ProviderAdvocateAgent` | `provider-advocate-agent` | Network manager — provider search |
| `BenefitsAgent` | `benefits-agent` | Benefits specialist — cost calculations |

### Communication Flow

```
MemberAssistAgent
    ├─ A2A → ClaimsAgent: "check_member_eligibility"
    │         ├─ MCP: list_member_claims, get_member_benefits
    │         └─ MCP: get_claim_detail
    │
    └─ A2A → ProviderAdvocateAgent: "search_network_providers"
              └─ MCP: search_providers

ClaimsAgent
    └─ A2A → BenefitsAgent: "calculate_member_responsibility"
              └─ MCP: estimate_member_responsibility
```

### Using agents in code

```python
import asyncio
from a2a import A2AProtocol, MemberAssistAgent, ClaimsAgent, ProviderAdvocateAgent, BenefitsAgent

async def main():
    protocol = A2AProtocol()

    member_assist     = MemberAssistAgent(protocol, mcp_client)
    claims            = ClaimsAgent(protocol, mcp_client)
    provider_advocate = ProviderAdvocateAgent(protocol, mcp_client)
    benefits          = BenefitsAgent(protocol, mcp_client)

    for agent in [member_assist, claims, provider_advocate, benefits]:
        await agent.register()

    protocol.register_handler("check_member_eligibility",        claims.handle_check_member_eligibility)
    protocol.register_handler("search_network_providers",        provider_advocate.handle_search_network_providers)
    protocol.register_handler("calculate_member_responsibility", benefits.handle_calculate_member_responsibility)

    eligibility = await member_assist.check_eligibility("M-1001")
    providers   = await member_assist.find_providers("primary care", "55401")

asyncio.run(main())
```

---

## Tests

```bash
pytest -v                          # all 40 tests
pytest test_a2a_communication.py   # A2A protocol tests only
```

See [TEST_GUIDE.md](TEST_GUIDE.md) for test documentation and [QUICKSTART.md](QUICKSTART.md) for filtering commands.

---

## Mock Data Reference

### Members

| ID | Name | Plan |
|----|------|------|
| `M-1001` | Jordan Lee | `P-100` Optum Choice PPO |
| `M-1002` | Casey Patel | `P-200` Optum Select HMO |

### Plans

| ID | Name | Deductible | Remaining | OOP Max | Remaining | In-network Coinsurance |
|----|------|-----------|-----------|---------|-----------|------------------------|
| `P-100` | Optum Choice PPO | $1,500 | $420 | $5,000 | $2,100 | 20% |
| `P-200` | Optum Select HMO | $500 | $120 | $3,000 | $980 | 10% |

### Providers

| ID | Name | Specialty | Network | ZIP |
|----|------|-----------|---------|-----|
| `PR-2001` | Northside Primary Care | primary care | in-network | 55401 |
| `PR-2002` | Lakeview Ortho Clinic | orthopedics | in-network | 55111 |
| `PR-2003` | Metro Imaging Center | radiology | out-of-network | 55415 |

### Claims

| ID | Member | Provider | Status | Billed |
|----|--------|----------|--------|--------|
| `C-10001` | M-1001 | PR-2001 | paid | $250.00 |
| `C-10002` | M-1001 | PR-2003 | pending | $980.00 |
| `C-10003` | M-1002 | PR-2002 | denied (prior auth required) | $1,350.00 |

### Prior Authorizations

| ID | Member | Status |
|----|--------|--------|
| `PA-9001` | M-1002 | approved |

---

## Architecture Diagrams

| File | Description |
|------|-------------|
| [diagrams/mcp.mmd](diagrams/mcp.mmd) | MCP Gateway routing to domain servers |
| [diagrams/a2a.mmd](diagrams/a2a.mmd) | A2A messaging between agents |

Render with [Mermaid Live Editor](https://mermaid.live) or any Mermaid-compatible viewer.

---

## MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a browser-based tool for calling MCP tools interactively.

```bash
npm install
npm start
```

---

## Notes

- All data is in-memory and resets on restart.
- `estimate_member_responsibility` uses mock multipliers (75% in-network, 60% out-of-network). Not a guarantee of payment.
- No PHI, no external API calls, no persistent storage.
- The official A2A Python SDK is [`a2a-sdk>=1.0.1`](https://pypi.org/project/a2a-sdk/). The `a2a/` module in this project is a custom educational implementation of the same protocol patterns.
