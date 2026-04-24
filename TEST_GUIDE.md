# Test Guide

The project has one test suite covering the A2A protocol implementation.

---

## A2A Protocol Tests (`test_a2a_communication.py` — 40 tests)

Tests the full A2A stack: message layer, registry, protocol engine, and all four healthcare agents. All tests use `AsyncMock` to simulate MCP client responses — no running server required.

### Coverage

| Test Class | Tests | What is covered |
|-----------|-------|-----------------|
| `TestA2AMessage` | 5 | Message creation, serialization, JSON round-trip |
| `TestA2ARequest` | 1 | Request builder |
| `TestA2AResponse` | 1 | Response builder |
| `TestA2AError` | 1 | Error builder |
| `TestAgentRegistry` | 4 | Registration, lookup, capability-based discovery |
| `TestA2AProtocol` | 4 | Handler registration, message routing, timeout |
| `TestMemberAssistAgent` | 5 | Init, register, MCP calls, A2A request handling |
| `TestClaimsAgent` | 5 | Init, register, MCP calls, A2A request handling |
| `TestProviderAdvocateAgent` | 3 | Init, register, provider search |
| `TestBenefitsAgent` | 2 | Init, cost calculation |
| `TestA2AIntegration` | 3 | Multi-agent discovery and coordination flows |
| `TestA2AErrorHandling` | 2 | Unregistered handlers, missing parameters |
| **Total** | **40** | |

---

## Running Tests

```bash
# All tests
pytest -v

# With coverage
pytest test_a2a_communication.py --cov=a2a --cov-report=html
```

See [QUICKSTART.md](QUICKSTART.md) for filtering commands.

---

## Test Patterns

### Agent initialisation and registration

```python
@pytest.mark.asyncio
async def test_agent_registers(self):
    protocol = A2AProtocol()
    agent = ClaimsAgent(protocol, AsyncMock())
    await agent.register()
    assert protocol.registry.get_agent("claims-agent") is not None
```

### Handler invoked via protocol

```python
@pytest.mark.asyncio
async def test_eligibility_handler(self):
    protocol = A2AProtocol()
    claims = ClaimsAgent(protocol, AsyncMock())
    await claims.register()
    protocol.register_handler(
        "check_member_eligibility",
        claims.handle_check_member_eligibility,
    )
    result = await claims.handle_check_member_eligibility({"member_id": "M-1001"})
    assert "member_id" in result
```

### MCP tool call (mocked)

```python
@pytest.mark.asyncio
async def test_mcp_tool_call(self):
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = {"member_id": "M-1001", "plan": {...}}
    agent = ClaimsAgent(A2AProtocol(), mock_client)
    result = await agent.call_mcp_tool("get_member_benefits", {"member_id": "M-1001"})
    assert "plan" in result
```

### Exception handling

```python
@pytest.mark.asyncio
async def test_mcp_tool_exception(self):
    mock_client = AsyncMock()
    mock_client.call_tool.side_effect = Exception("Connection error")
    agent = ClaimsAgent(A2AProtocol(), mock_client)
    result = await agent.call_mcp_tool("get_member_benefits", {"member_id": "M-1001"})
    assert "error" in result
```

---

## Adding Tests

```python
@pytest.mark.asyncio
async def test_new_case(self):
    protocol = A2AProtocol()
    agent = ProviderAdvocateAgent(protocol, AsyncMock())
    await agent.register()
    protocol.register_handler(
        "search_network_providers",
        agent.handle_search_network_providers,
    )
    result = await agent.handle_search_network_providers({"specialty": "radiology"})
    assert "result" in result
```

---

## Troubleshooting

**Tests not found**
```bash
pytest --collect-only
```

**Async tests not running** — confirm `pytest.ini` contains:
```ini
[pytest]
asyncio_mode = auto
```

**Import errors**
```bash
pip install -r requirements.txt
```
