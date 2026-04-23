# Quick Start - Running the Tests

## 1. Setup (One-time)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Run Tests

### All tests
```bash
pytest test_agent_mcp_tools.py -v
```

### By scenario type
```bash
pytest test_agent_mcp_tools.py -v -k "Success"     # 26 tests
pytest test_agent_mcp_tools.py -v -k "Failure"     # 18 tests
pytest test_agent_mcp_tools.py -v -k "Negative"    # 17 tests
pytest test_agent_mcp_tools.py -v -k "Integration" # 3 tests
```

### By tool
```bash
pytest test_agent_mcp_tools.py -v -k "ListMemberClaims"
pytest test_agent_mcp_tools.py -v -k "GetClaimDetail"
pytest test_agent_mcp_tools.py -v -k "GetMemberBenefits"
pytest test_agent_mcp_tools.py -v -k "EstimateMemberResponsibility"
pytest test_agent_mcp_tools.py -v -k "SearchProviders"
pytest test_agent_mcp_tools.py -v -k "CreatePriorAuth"
pytest test_agent_mcp_tools.py -v -k "GetPriorAuthStatus"
pytest test_agent_mcp_tools.py -v -k "SubmitInquiry"
```

### Single test
```bash
pytest test_agent_mcp_tools.py::TestEstimateMemberResponsibilitySuccess::test_estimate_in_network_procedure -v
```

### With coverage
```bash
pip install pytest-cov
pytest test_agent_mcp_tools.py --cov=agent --cov-report=html
# Open htmlcov/index.html in browser
```

## 3. Expected Output

```
test_agent_mcp_tools.py::TestListMemberClaimsSuccess::test_list_claims_all PASSED
test_agent_mcp_tools.py::TestListMemberClaimsSuccess::test_list_claims_with_status_filter PASSED
test_agent_mcp_tools.py::TestListMemberClaimsSuccess::test_list_claims_pending_status PASSED
...
===================== 61 passed in 0.24s =====================
```

## 4. Test Structure

Each test file has:
- **Setup**: Create mock client
- **Action**: Call agent method
- **Assert**: Verify results

Example:
```python
@pytest.mark.asyncio
async def test_get_member_benefits_ppo_plan(self):
    """Test retrieving benefits for member with PPO plan."""
    # Setup
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = {
        "member_id": "M-1001",
        "plan": {"plan_name": "Optum Choice PPO"}
    }
    
    # Action
    agent = HealthClaimsAgent(mock_client)
    result = await agent.get_member_benefits("M-1001")
    
    # Assert
    assert result["plan"]["plan_name"] == "Optum Choice PPO"
```

## 5. Adding New Tests

### Add a success test
```python
@pytest.mark.asyncio
async def test_new_success_case(self):
    """Test description."""
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = {
        # Expected response
    }
    agent = HealthClaimsAgent(mock_client)
    result = await agent.tool_method(params)
    assert result["field"] == expected_value
```

### Add a failure test
```python
@pytest.mark.asyncio
async def test_new_failure_case(self):
    """Test error handling."""
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = {
        "error": "error_code",
        "details": "error message"
    }
    agent = HealthClaimsAgent(mock_client)
    result = await agent.tool_method(params)
    assert "error" in result
```

### Add an exception test
```python
@pytest.mark.asyncio
async def test_new_exception_case(self):
    """Test exception handling."""
    mock_client = AsyncMock()
    mock_client.call_tool.side_effect = Exception("Error message")
    agent = HealthClaimsAgent(mock_client)
    result = await agent.tool_method(params)
    assert "error" in result
```

## 6. Debugging Tests

### Verbose output
```bash
pytest test_agent_mcp_tools.py -vv -s
```

### Run with print statements
Add `print()` statements, then run with `-s`:
```bash
pytest test_agent_mcp_tools.py::TestClassName::test_method -s
```

### Run stop on first failure
```bash
pytest test_agent_mcp_tools.py -x
```

### Run last failed
```bash
pytest test_agent_mcp_tools.py --lf
```

## 7. CI/CD Integration

### GitHub Actions example
```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest test_agent_mcp_tools.py -v
```

## 8. Test Statistics

- **Total Tests**: 61
- **Success Tests**: 26 (43%)
- **Failure Tests**: 18 (30%)
- **Negative Tests**: 17 (28%)
- **Tools Covered**: 8/8 (100%)
- **Execution Time**: ~0.24 seconds
- **Pass Rate**: 100%

## 9. Reference

| Command | Purpose |
|---------|---------|
| `pytest` | Run all tests |
| `pytest -v` | Verbose output |
| `pytest -s` | Show print statements |
| `pytest -k "keyword"` | Filter by name |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Run last failed |
| `pytest --tb=short` | Short traceback |
| `pytest -m "marker"` | Run by marker |

## 10. Files

- `agent.py` - HealthClaimsAgent implementation
- `test_agent_mcp_tools.py` - Test suite (61 tests)
- `requirements.txt` - Dependencies
- `pytest.ini` - Pytest configuration
- `TEST_GUIDE.md` - Detailed documentation
- `TEST_SUMMARY.md` - Complete overview
- `QUICKSTART.md` - This file
