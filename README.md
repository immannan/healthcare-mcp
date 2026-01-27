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
export FASTMCP_STREAMABLE_HTTP_PATH=/claims-mcp
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

Run the Inspector in the foreground (graceful stop with Ctrl+C):

```bash
npx @modelcontextprotocol/inspector
```

If your org blocks new npm versions, install in a temp folder with an override:

```bash
mkdir -p /tmp/mcp-inspector
cat <<'JSON' > /tmp/mcp-inspector/package.json
{
  "name": "mcp-inspector-wrapper",
  "private": true,
  "version": "0.0.0",
  "dependencies": {
    "@modelcontextprotocol/inspector": "0.17.0"
  },
  "overrides": {
    "diff": "4.0.2"
  }
}
JSON
(cd /tmp/mcp-inspector && npm install)
(cd /tmp/mcp-inspector && npx @modelcontextprotocol/inspector)
```

Stop a background Inspector process:

```bash
pkill -f "@modelcontextprotocol/inspector"
```

## Notes

- The server uses FastMCP (`mcp.server.fastmcp.FastMCP`) with `@mcp.tool()`
  decorators as described in the MCP build-server docs.
- The mock logic is deterministic and in-memory; no external calls or PHI.
