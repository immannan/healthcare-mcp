# Quick Start

## 1. Setup (one-time)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. Run the MCP Server

```bash
python mcp_server/server.py
```

Runs on stdio by default. For HTTP:

```bash
export MCP_TRANSPORT=streamable-http && python mcp_server/server.py
# → http://127.0.0.1:8000/mcp
```

---

## 3. Run the A2A Server

```bash
python run_a2a.py
# → http://127.0.0.1:8001
```

Check it's up:

```bash
curl http://127.0.0.1:8001/.well-known/agent.json | python -m json.tool
curl http://127.0.0.1:8001/agents
```

Send a message to the Claims Agent:

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

## 4. Run Tests

```bash
pytest -v                          # all 40 A2A tests
pytest test_a2a_communication.py   # same, explicit
```

### Filter by component

```bash
pytest test_a2a_communication.py -v -k "Message"
pytest test_a2a_communication.py -v -k "Registry"
pytest test_a2a_communication.py -v -k "Protocol"
pytest test_a2a_communication.py -v -k "Integration"
```

### Filter by agent

```bash
pytest test_a2a_communication.py -v -k "MemberAssist"
pytest test_a2a_communication.py -v -k "Claims"
pytest test_a2a_communication.py -v -k "ProviderAdvocate"
pytest test_a2a_communication.py -v -k "Benefits"
```

### With coverage

```bash
pytest test_a2a_communication.py --cov=a2a --cov-report=html
# Open htmlcov/index.html
```

---

## 5. Useful pytest Flags

| Flag | Purpose |
|------|---------|
| `-v` | Verbose output |
| `-vv -s` | Verbose + show print statements |
| `-x` | Stop on first failure |
| `--lf` | Re-run last failed tests |
| `--tb=short` | Short tracebacks |
| `-k "keyword"` | Filter by name |

---

## 6. Single Test

```bash
pytest test_a2a_communication.py::TestMemberAssistAgent -v
pytest test_a2a_communication.py::TestA2AIntegration -v
```

---

## 7. CI/CD (GitHub Actions example)

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest -v
```
