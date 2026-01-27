# Health Claims FastMCP (Mock)

Sample MCP server for the health insurance claims domain. This server uses
FastMCP and exposes multiple mock tools for claims, benefits, providers, and
prior authorizations. All data is synthetic and for demo use only.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (stdio)

```bash
python server.py
```

## Run (streamable HTTP)

FastMCP supports `streamable-http` and `sse` transports. Use env vars to switch
transport and control host/port.

```bash
export MCP_TRANSPORT=streamable-http
export FASTMCP_HOST=127.0.0.1
export FASTMCP_PORT=8000
python server.py
```

The Streamable HTTP endpoint defaults to:

```
http://127.0.0.1:8000/mcp
```

You can override it via `FASTMCP_STREAMABLE_HTTP_PATH`.

```bash
export FASTMCP_STREAMABLE_HTTP_PATH=/mcp
```

## Tools

- `list_member_claims`
- `get_claim_detail`
- `get_member_benefits`
- `estimate_member_responsibility`
- `search_providers`
- `create_prior_authorization`
- `get_prior_authorization_status`
- `submit_claim_inquiry`

## MCP Inspector (start/stop)

Install and run via npm scripts:

```bash
npm install
npm start
```

## Notes

- The server uses FastMCP (`mcp.server.fastmcp.FastMCP`) with `@mcp.tool()`
  decorators as described in the MCP build-server docs.
- The mock logic is deterministic and in-memory; no external calls or PHI.
