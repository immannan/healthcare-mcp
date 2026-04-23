# Unit Tests Guide - Health Claims Agent MCP Tools

This guide explains the comprehensive unit test suite for the agent calling MCP server tools in the health claims domain.

## Overview

The test suite (`test_agent_mcp_tools.py`) provides comprehensive coverage for all MCP tools with:
- ✅ **Success scenarios** - Normal operation and expected results
- ❌ **Failure scenarios** - Error handling and edge cases
- ⚠️ **Negative scenarios** - Boundary conditions and invalid inputs

## Test Structure

### Tools Covered

1. **`list_member_claims`** - List claims for a member
2. **`get_claim_detail`** - Get full claim details
3. **`get_member_benefits`** - Retrieve member's benefit information
4. **`estimate_member_responsibility`** - Calculate member cost estimate
5. **`search_providers`** - Search for healthcare providers
6. **`create_prior_authorization`** - Create prior auth request
7. **`get_prior_authorization_status`** - Check prior auth status
8. **`submit_claim_inquiry`** - Submit a claim inquiry ticket

### Test Classes by Category

#### Success Scenarios
- `TestListMemberClaimsSuccess` - All claims, filtered by status (paid, pending, denied)
- `TestGetClaimDetailSuccess` - Paid, pending, and denied claims
- `TestGetMemberBenefitsSuccess` - PPO and HMO plan types
- `TestEstimateMemberResponsibilitySuccess` - In-network, out-of-network, default network
- `TestSearchProvidersSuccess` - Specialty search, ZIP filter, network filter, multi-filter
- `TestCreatePriorAuthSuccess` - Single and multiple procedure codes
- `TestGetPriorAuthStatusSuccess` - Approved and pending status
- `TestSubmitInquirySuccess` - Status question, appeal, billing inquiry

#### Failure Scenarios
- `TestListMemberClaimsFailure` - Member not found, tool exception, invalid status
- `TestGetClaimDetailFailure` - Claim not found, tool exception
- `TestGetMemberBenefitsFailure` - Member not found, plan not found, tool exception
- `TestEstimateMemberResponsibilityFailure` - Member not found, invalid network, calculation error
- `TestSearchProvidersFailure` - No results found
- `TestCreatePriorAuthFailure` - Member not found, provider not found, authorization error
- `TestGetPriorAuthStatusFailure` - Authorization not found, database timeout
- `TestSubmitInquiryFailure` - Claim not found, ticket system error

#### Negative/Edge Cases
- `TestListMemberClaimsNegative` - Empty results, empty ID, special characters
- `TestGetClaimDetailNegative` - Empty ID, malformed ID format
- `TestGetMemberBenefitsNegative` - Zero deductible, maximum OOP reached
- `TestEstimateMemberResponsibilityNegative` - Zero amount, large amounts, negative amounts
- `TestSearchProvidersNegative` - No results, empty specialty
- `TestCreatePriorAuthNegative` - Empty procedure codes, past service dates
- `TestGetPriorAuthStatusNegative` - Empty ID
- `TestSubmitInquiryNegative` - Empty note, very long notes

#### Integration Tests
- `TestAgentIntegration` - Multi-step workflows
  - Check claim and retrieve benefits
  - Search providers and estimate costs
  - Create prior auth and check status

## Test Coverage Summary

| Tool | Success | Failure | Negative | Total |
|------|---------|---------|----------|-------|
| list_member_claims | 4 | 3 | 3 | 10 |
| get_claim_detail | 3 | 2 | 2 | 7 |
| get_member_benefits | 2 | 3 | 2 | 7 |
| estimate_member_responsibility | 3 | 3 | 3 | 9 |
| search_providers | 4 | 0 | 2 | 6 |
| create_prior_authorization | 2 | 3 | 2 | 7 |
| get_prior_authorization_status | 2 | 2 | 1 | 5 |
| submit_claim_inquiry | 3 | 2 | 2 | 7 |
| Integration Workflows | 3 | - | - | 3 |
| **TOTAL** | **26** | **18** | **17** | **61** |

## Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest test_agent_mcp_tools.py -v
```

### Run Tests by Category

```bash
# Success scenarios only
pytest test_agent_mcp_tools.py -v -k "Success"

# Failure scenarios only
pytest test_agent_mcp_tools.py -v -k "Failure"

# Negative scenarios only
pytest test_agent_mcp_tools.py -v -k "Negative"

# Integration tests only
pytest test_agent_mcp_tools.py -v -k "Integration"
```

### Run Tests for Specific Tool

```bash
# Test only list_member_claims
pytest test_agent_mcp_tools.py -v -k "ListMemberClaims"

# Test only get_claim_detail
pytest test_agent_mcp_tools.py -v -k "GetClaimDetail"

# Test only search_providers
pytest test_agent_mcp_tools.py -v -k "SearchProviders"
```

### Run with Coverage Report

```bash
pip install pytest-cov
pytest test_agent_mcp_tools.py --cov=agent --cov-report=html
```

The coverage report will be generated in `htmlcov/index.html`

### Run with Verbose Output

```bash
pytest test_agent_mcp_tools.py -vv -s
```

### Run Specific Test

```bash
pytest test_agent_mcp_tools.py::TestEstimateMemberResponsibilitySuccess::test_estimate_in_network_procedure -v
```

## Test Scenarios Examples

### Success Scenario Example
```python
async def test_list_claims_all(self):
    """Test retrieving all claims for a member."""
    mock_client.call_tool.return_value = {
        "member": {"member_id": "M-1001", "name": "Jordan Lee"},
        "claim_count": 2,
        "claims": [...]
    }
    result = await agent.get_member_claims("M-1001")
    assert result["claim_count"] == 2
```

### Failure Scenario Example
```python
async def test_list_claims_member_not_found(self):
    """Test retrieving claims for non-existent member."""
    mock_client.call_tool.return_value = {
        "error": "member_not_found",
        "member_id": "M-9999"
    }
    result = await agent.get_member_claims("M-9999")
    assert "error" in result
```

### Negative Scenario Example
```python
async def test_estimate_zero_billed_amount(self):
    """Test estimate with zero billed amount."""
    mock_client.call_tool.return_value = {
        "estimate": {"member_responsibility_estimate": 0.0}
    }
    result = await agent.estimate_responsibility("M-1001", "99213", 0.0)
    assert result["estimate"]["member_responsibility_estimate"] == 0.0
```

## Test Methodology

### Mock-Based Testing
- All tests use `AsyncMock` to simulate MCP client responses
- No actual MCP server calls are made during testing
- Tests focus on agent behavior and error handling

### Error Handling Verification
- Each tool method catches exceptions and returns error dictionaries
- Tests verify that errors are properly propagated
- Tests check for appropriate error messages and codes

### Data Validation
- Tests verify response structure and data types
- Tests check for proper handling of edge cases (empty, zero, negative values)
- Tests validate filtering and parameter passing

## Key Test Patterns

### 1. Tool Success Tests
Verify that the agent correctly calls the tool and processes the response.

```python
result = await agent.get_member_claims("M-1001")
assert "claims" in result
```

### 2. Tool Failure Tests
Verify that the agent handles errors gracefully.

```python
mock_client.call_tool.return_value = {"error": "member_not_found"}
result = await agent.get_member_claims("M-9999")
assert "error" in result
```

### 3. Exception Handling Tests
Verify that the agent handles exceptions from the MCP client.

```python
mock_client.call_tool.side_effect = Exception("Connection error")
result = await agent.get_member_claims("M-1001")
assert "error" in result
```

### 4. Boundary Condition Tests
Verify that the agent handles edge cases.

```python
result = await agent.estimate_responsibility("M-1001", "99213", 0.0)
# Verify zero amount is handled
```

### 5. Integration Tests
Verify that the agent can chain multiple tool calls.

```python
claim = await agent.get_claim_details("C-10001")
benefits = await agent.get_member_benefits(claim["member_id"])
# Verify both calls complete successfully
```

## Expected Test Output

```
test_agent_mcp_tools.py::TestListMemberClaimsSuccess::test_list_claims_all PASSED
test_agent_mcp_tools.py::TestListMemberClaimsSuccess::test_list_claims_with_status_filter PASSED
test_agent_mcp_tools.py::TestListMemberClaimsFailure::test_list_claims_member_not_found PASSED
...
===================== 61 passed in 0.24s =====================
```

## Files Included

1. **`agent.py`** - HealthClaimsAgent implementation
   - Async agent class that calls MCP tools
   - Error handling for each tool
   - All 8 MCP tools implemented

2. **`test_agent_mcp_tools.py`** - Comprehensive test suite
   - 61 unit tests covering all scenarios
   - Organized into logical test classes
   - Integration tests for multi-step workflows

3. **`requirements.txt`** - Updated dependencies
   - pytest for test framework
   - pytest-asyncio for async test support

4. **`TEST_GUIDE.md`** - This guide

## Troubleshooting

### Tests not discovering
```bash
pytest --collect-only test_agent_mcp_tools.py
```

### Async tests not running
Ensure `pytest.ini` or `pyproject.toml` is configured:
```ini
[tool:pytest]
asyncio_mode = auto
```

### Module import errors
```bash
pip install -e .
```

## Next Steps

1. **Integrate with CI/CD**: Add tests to your GitHub Actions or GitLab CI pipeline
2. **Expand Coverage**: Add tests for specific business logic
3. **Performance Tests**: Add benchmarks for tool response times
4. **Mocking Real MCP**: Replace mock responses with actual MCP server calls for integration testing

## Related Documentation

- [MCP Python SDK](https://modelcontextprotocol.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://github.com/pytest-dev/pytest-asyncio)
