"""
Standalone A2A server — runs all four healthcare agents over HTTP.

The server uses a LocalMCPClient that calls the MCP tool functions directly
in-process (no separate MCP server required). Swap it for a real MCP HTTP
client to connect to a remote MCP server instead.

Run:
    python run_a2a.py

Environment variables:
    A2A_HOST  (default: 127.0.0.1)
    A2A_PORT  (default: 8001)

Endpoints:
    GET  /.well-known/agent.json        Agent card for the primary agent
    GET  /agents                        List all agent cards (A2A spec)
    GET  /agents/{agent_id}/card        Card for a specific agent
    GET  /tasks                         List all tasks
    GET  /tasks/{task_id}               Get a specific task by ID
    POST /                              JSON-RPC 2.0 message receiver
                                          tasks/send   — create/continue a task
                                          tasks/get    — poll task status
                                          tasks/cancel — cancel a task
                                          <skill>      — direct method call (legacy)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from a2a import (
    A2AProtocol,
    BenefitsAgent,
    ClaimsAgent,
    MemberAssistAgent,
    ProviderAdvocateAgent,
)
from a2a.message import A2AMessage
import mcp_server.server as _mcp

# ---------------------------------------------------------------------------
# Local MCP client — calls MCP tool functions in-process (no network hop)
# ---------------------------------------------------------------------------

_TOOL_MAP: dict[str, Any] = {
    "list_member_claims":             _mcp.list_member_claims,
    "get_claim_detail":               _mcp.get_claim_detail,
    "get_member_benefits":            _mcp.get_member_benefits,
    "estimate_member_responsibility": _mcp.estimate_member_responsibility,
    "search_providers":               _mcp.search_providers,
    "create_prior_authorization":     _mcp.create_prior_authorization,
    "get_prior_authorization_status": _mcp.get_prior_authorization_status,
    "submit_claim_inquiry":           _mcp.submit_claim_inquiry,
}


class LocalMCPClient:
    """Calls MCP tool functions directly — no HTTP round-trip required."""

    async def call_tool(self, tool_name: str, params: dict) -> Any:
        fn = _TOOL_MAP.get(tool_name)
        if fn is None:
            raise ValueError(f"Unknown MCP tool: {tool_name!r}")
        # Strip None values so optional parameters fall back to their defaults
        return fn(**{k: v for k, v in params.items() if v is not None})


# ---------------------------------------------------------------------------
# App lifecycle — build protocol and register all agents
# ---------------------------------------------------------------------------

_protocol: A2AProtocol | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _protocol

    mcp_client = LocalMCPClient()
    _protocol = A2AProtocol()

    member_assist    = MemberAssistAgent(_protocol, mcp_client)
    claims           = ClaimsAgent(_protocol, mcp_client)
    provider_advocate = ProviderAdvocateAgent(_protocol, mcp_client)
    benefits         = BenefitsAgent(_protocol, mcp_client)

    for agent in [member_assist, claims, provider_advocate, benefits]:
        await agent.register()

    _protocol.register_handler(
        "check_member_eligibility",
        claims.handle_check_member_eligibility,
    )
    _protocol.register_handler(
        "search_network_providers",
        provider_advocate.handle_search_network_providers,
    )
    _protocol.register_handler(
        "calculate_member_responsibility",
        benefits.handle_calculate_member_responsibility,
    )
    _protocol.register_handler(
        "check_eligibility",
        member_assist.handle_check_eligibility,
    )
    _protocol.register_handler(
        "find_providers",
        member_assist.handle_find_providers,
    )

    print(f"Healthcare A2A server ready — {len(_protocol.registry.list_all_agents())} agents registered")
    yield
    _protocol = None


# ---------------------------------------------------------------------------
# HTTP application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Healthcare A2A Server",
    description="Multi-agent healthcare claims system (mock data)",
    version="1.0.0",
    lifespan=lifespan,
)


def _base_url() -> str:
    return f"http://{os.getenv('A2A_HOST', '127.0.0.1')}:{os.getenv('A2A_PORT', '8001')}"


@app.get("/.well-known/agent.json", response_class=JSONResponse)
async def agent_card():
    """A2A spec discovery card for the primary entry-point agent (MemberAssistAgent)."""
    info = _protocol.registry.get_agent("member-assist-agent")
    if info is None:
        raise HTTPException(status_code=503, detail="Agents not yet registered")
    return info.to_agent_card(_base_url()).to_dict()


@app.get("/agents", response_class=JSONResponse)
async def list_agents():
    """List all registered agents with their A2A-spec skill descriptors."""
    base = _base_url()
    return {
        "agents": [
            info.to_agent_card(base).to_dict()
            for info in _protocol.registry.list_all_agents()
        ]
    }


@app.get("/agents/{agent_id}/card", response_class=JSONResponse)
async def agent_card_by_id(agent_id: str):
    """A2A spec discovery card for a specific agent."""
    info = _protocol.registry.get_agent(agent_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return info.to_agent_card(_base_url()).to_dict()


@app.get("/tasks", response_class=JSONResponse)
async def list_tasks():
    """List all tasks currently tracked by the server."""
    if _protocol is None:
        raise HTTPException(status_code=503, detail="Server not ready")
    return {"tasks": [t.to_dict() for t in _protocol.tasks.list_all()]}


@app.get("/tasks/{task_id}", response_class=JSONResponse)
async def get_task(task_id: str):
    """Get a specific task by ID."""
    if _protocol is None:
        raise HTTPException(status_code=503, detail="Server not ready")
    task = _protocol.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task.to_dict()


@app.post("/", response_class=JSONResponse)
async def handle_message(request: Request):
    """Receive and route an A2A JSON-RPC 2.0 message."""
    body = await request.json()
    message = A2AMessage.from_dict(body)
    response = await _protocol.handle_message(message)
    if response:
        return response.to_dict()
    return {"status": "accepted", "id": message.id}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "8001"))
    uvicorn.run(app, host=host, port=port, log_level="info")
