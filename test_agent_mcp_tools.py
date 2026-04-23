"""
Comprehensive unit tests for the HealthClaimsAgent calling MCP server tools.
Covers success scenarios, failure scenarios, and negative/edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from agent import HealthClaimsAgent


class TestListMemberClaimsSuccess:
    """Test successful scenarios for list_member_claims tool."""

    @pytest.mark.asyncio
    async def test_list_claims_all(self):
        """Test retrieving all claims for a member."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member": {"member_id": "M-1001", "name": "Jordan Lee"},
            "claim_count": 2,
            "claims": [
                {
                    "claim_id": "C-10001",
                    "service_date": "2024-08-10",
                    "status": "paid",
                    "provider_name": "Northside Primary Care",
                    "billed_amount": 250.0,
                    "member_responsibility": 60.0,
                }
            ],
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-1001")

        assert "claims" in result
        assert result["claim_count"] == 2
        assert result["member"]["member_id"] == "M-1001"
        mock_client.call_tool.assert_called_once_with(
            "list_member_claims", {"member_id": "M-1001", "status": None}
        )

    @pytest.mark.asyncio
    async def test_list_claims_with_status_filter(self):
        """Test retrieving claims filtered by status."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member": {"member_id": "M-1001", "name": "Jordan Lee"},
            "claim_count": 1,
            "claims": [
                {
                    "claim_id": "C-10001",
                    "status": "paid",
                }
            ],
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-1001", status="paid")

        assert result["claim_count"] == 1
        assert result["claims"][0]["status"] == "paid"
        mock_client.call_tool.assert_called_once_with(
            "list_member_claims", {"member_id": "M-1001", "status": "paid"}
        )

    @pytest.mark.asyncio
    async def test_list_claims_pending_status(self):
        """Test retrieving pending claims."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member": {"member_id": "M-1001", "name": "Jordan Lee"},
            "claim_count": 1,
            "claims": [
                {
                    "claim_id": "C-10002",
                    "status": "pending",
                    "status_reason": "awaiting medical records",
                }
            ],
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-1001", status="pending")

        assert result["claims"][0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_claims_denied_status(self):
        """Test retrieving denied claims."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member": {"member_id": "M-1002", "name": "Casey Patel"},
            "claim_count": 1,
            "claims": [
                {
                    "claim_id": "C-10003",
                    "status": "denied",
                    "status_reason": "prior authorization required",
                }
            ],
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-1002", status="denied")

        assert result["claims"][0]["status"] == "denied"


class TestListMemberClaimsFailure:
    """Test failure scenarios for list_member_claims tool."""

    @pytest.mark.asyncio
    async def test_list_claims_member_not_found(self):
        """Test retrieving claims for non-existent member."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "member_not_found",
            "member_id": "M-9999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-9999")

        assert "error" in result
        assert result["error"] == "member_not_found"

    @pytest.mark.asyncio
    async def test_list_claims_tool_exception(self):
        """Test exception handling when tool fails."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Connection error")

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-1001")

        assert "error" in result
        assert "Connection error" in result["error"]

    @pytest.mark.asyncio
    async def test_list_claims_invalid_status(self):
        """Test retrieving claims with invalid status filter."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member": {"member_id": "M-1001", "name": "Jordan Lee"},
            "claim_count": 0,
            "claims": [],
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-1001", status="invalid_status")

        assert result["claim_count"] == 0


class TestListMemberClaimsNegative:
    """Test negative/edge cases for list_member_claims tool."""

    @pytest.mark.asyncio
    async def test_list_claims_empty_result(self):
        """Test when member has no claims."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member": {"member_id": "M-1001", "name": "Jordan Lee"},
            "claim_count": 0,
            "claims": [],
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-1001")

        assert result["claim_count"] == 0
        assert result["claims"] == []

    @pytest.mark.asyncio
    async def test_list_claims_empty_member_id(self):
        """Test with empty member ID."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"error": "member_not_found", "member_id": ""}

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_claims_special_characters_member_id(self):
        """Test member ID with special characters."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"error": "member_not_found", "member_id": "M-@#$%"}

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_claims("M-@#$%")

        assert "error" in result


class TestGetClaimDetailSuccess:
    """Test successful scenarios for get_claim_detail tool."""

    @pytest.mark.asyncio
    async def test_get_claim_detail_paid(self):
        """Test retrieving details for a paid claim."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "claim_id": "C-10001",
            "member_id": "M-1001",
            "provider_id": "PR-2001",
            "service_date": "2024-08-10",
            "claim_type": "professional",
            "status": "paid",
            "status_reason": "adjudicated",
            "billed_amount": 250.0,
            "allowed_amount": 180.0,
            "paid_amount": 120.0,
            "member_responsibility": 60.0,
            "member": {"member_id": "M-1001", "name": "Jordan Lee"},
            "provider": {"provider_id": "PR-2001", "name": "Northside Primary Care"},
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_claim_details("C-10001")

        assert result["claim_id"] == "C-10001"
        assert result["status"] == "paid"
        assert result["paid_amount"] == 120.0
        assert result["member"]["name"] == "Jordan Lee"

    @pytest.mark.asyncio
    async def test_get_claim_detail_pending(self):
        """Test retrieving details for a pending claim."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "claim_id": "C-10002",
            "status": "pending",
            "status_reason": "awaiting medical records",
            "paid_amount": 0.0,
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_claim_details("C-10002")

        assert result["status"] == "pending"
        assert result["paid_amount"] == 0.0

    @pytest.mark.asyncio
    async def test_get_claim_detail_denied(self):
        """Test retrieving details for a denied claim."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "claim_id": "C-10003",
            "status": "denied",
            "status_reason": "prior authorization required",
            "paid_amount": 0.0,
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_claim_details("C-10003")

        assert result["status"] == "denied"


class TestGetClaimDetailFailure:
    """Test failure scenarios for get_claim_detail tool."""

    @pytest.mark.asyncio
    async def test_get_claim_detail_not_found(self):
        """Test retrieving details for non-existent claim."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "claim_not_found",
            "claim_id": "C-99999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_claim_details("C-99999")

        assert "error" in result
        assert result["error"] == "claim_not_found"

    @pytest.mark.asyncio
    async def test_get_claim_detail_tool_exception(self):
        """Test exception handling when tool fails."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Database error")

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_claim_details("C-10001")

        assert "error" in result
        assert "Database error" in result["error"]


class TestGetClaimDetailNegative:
    """Test negative/edge cases for get_claim_detail tool."""

    @pytest.mark.asyncio
    async def test_get_claim_detail_empty_id(self):
        """Test with empty claim ID."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"error": "claim_not_found", "claim_id": ""}

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_claim_details("")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_claim_detail_malformed_id(self):
        """Test with malformed claim ID format."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"error": "claim_not_found", "claim_id": "INVALID"}

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_claim_details("INVALID")

        assert "error" in result


class TestGetMemberBenefitsSuccess:
    """Test successful scenarios for get_member_benefits tool."""

    @pytest.mark.asyncio
    async def test_get_member_benefits_ppo_plan(self):
        """Test retrieving benefits for member with PPO plan."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "plan": {
                "plan_id": "P-100",
                "plan_name": "Optum Choice PPO",
                "deductible_total": 1500.0,
                "deductible_remaining": 420.0,
                "oop_max_total": 5000.0,
                "oop_max_remaining": 2100.0,
                "coinsurance_in_network": 0.2,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_benefits("M-1001")

        assert result["member_id"] == "M-1001"
        assert result["plan"]["plan_name"] == "Optum Choice PPO"
        assert result["plan"]["deductible_remaining"] == 420.0

    @pytest.mark.asyncio
    async def test_get_member_benefits_hmo_plan(self):
        """Test retrieving benefits for member with HMO plan."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1002",
            "plan": {
                "plan_id": "P-200",
                "plan_name": "Optum Select HMO",
                "deductible_total": 500.0,
                "deductible_remaining": 120.0,
                "oop_max_total": 3000.0,
                "oop_max_remaining": 980.0,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_benefits("M-1002")

        assert result["plan"]["plan_name"] == "Optum Select HMO"
        assert result["plan"]["deductible_total"] == 500.0


class TestGetMemberBenefitsFailure:
    """Test failure scenarios for get_member_benefits tool."""

    @pytest.mark.asyncio
    async def test_get_member_benefits_member_not_found(self):
        """Test retrieving benefits for non-existent member."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "member_not_found",
            "member_id": "M-9999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_benefits("M-9999")

        assert "error" in result
        assert result["error"] == "member_not_found"

    @pytest.mark.asyncio
    async def test_get_member_benefits_plan_not_found(self):
        """Test when member's plan is not found."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "plan_not_found",
            "plan_id": "P-999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_benefits("M-1001")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_member_benefits_tool_exception(self):
        """Test exception handling when tool fails."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Service unavailable")

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_benefits("M-1001")

        assert "error" in result


class TestGetMemberBenefitsNegative:
    """Test negative/edge cases for get_member_benefits tool."""

    @pytest.mark.asyncio
    async def test_get_member_benefits_zero_deductible(self):
        """Test member with zero deductible remaining."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "plan": {
                "plan_id": "P-100",
                "deductible_remaining": 0.0,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_benefits("M-1001")

        assert result["plan"]["deductible_remaining"] == 0.0

    @pytest.mark.asyncio
    async def test_get_member_benefits_max_oop_reached(self):
        """Test member with OOP maximum reached."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "plan": {
                "plan_id": "P-100",
                "oop_max_total": 5000.0,
                "oop_max_remaining": 0.0,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_member_benefits("M-1001")

        assert result["plan"]["oop_max_remaining"] == 0.0


class TestEstimateMemberResponsibilitySuccess:
    """Test successful scenarios for estimate_member_responsibility tool."""

    @pytest.mark.asyncio
    async def test_estimate_in_network_procedure(self):
        """Test estimating member responsibility for in-network procedure."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "procedure_code": "99213",
            "network": "in-network",
            "billed_amount": 250.0,
            "allowed_amount_estimate": 187.5,
            "estimate": {
                "applied_to_deductible": 187.5,
                "coinsurance": 0.0,
                "copay": 30.0,
                "member_responsibility_estimate": 217.5,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility(
            "M-1001", "99213", 250.0, "in-network"
        )

        assert result["network"] == "in-network"
        assert result["estimate"]["copay"] == 30.0

    @pytest.mark.asyncio
    async def test_estimate_out_of_network_procedure(self):
        """Test estimating member responsibility for out-of-network procedure."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "procedure_code": "72100",
            "network": "out-of-network",
            "billed_amount": 980.0,
            "allowed_amount_estimate": 588.0,
            "estimate": {
                "applied_to_deductible": 420.0,
                "coinsurance": 67.2,
                "copay": 0.0,
                "member_responsibility_estimate": 487.2,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility(
            "M-1001", "72100", 980.0, "out-of-network"
        )

        assert result["network"] == "out-of-network"
        assert result["estimate"]["coinsurance"] > 0

    @pytest.mark.asyncio
    async def test_estimate_default_network(self):
        """Test estimate with default network (in-network)."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "network": "in-network",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility("M-1001", "99213", 250.0)

        assert result["network"] == "in-network"


class TestEstimateMemberResponsibilityFailure:
    """Test failure scenarios for estimate_member_responsibility tool."""

    @pytest.mark.asyncio
    async def test_estimate_member_not_found(self):
        """Test estimating for non-existent member."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "member_not_found",
            "member_id": "M-9999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility(
            "M-9999", "99213", 250.0, "in-network"
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_estimate_invalid_network(self):
        """Test estimate with invalid network type."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "invalid_network",
            "network": "invalid",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility(
            "M-1001", "99213", 250.0, "invalid"
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_estimate_tool_exception(self):
        """Test exception handling when tool fails."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Calculation error")

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility(
            "M-1001", "99213", 250.0, "in-network"
        )

        assert "error" in result


class TestEstimateMemberResponsibilityNegative:
    """Test negative/edge cases for estimate_member_responsibility tool."""

    @pytest.mark.asyncio
    async def test_estimate_zero_billed_amount(self):
        """Test estimate with zero billed amount."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "billed_amount": 0.0,
            "estimate": {
                "member_responsibility_estimate": 0.0,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility("M-1001", "99213", 0.0)

        assert result["estimate"]["member_responsibility_estimate"] == 0.0

    @pytest.mark.asyncio
    async def test_estimate_large_billed_amount(self):
        """Test estimate with large billed amount."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "member_id": "M-1001",
            "billed_amount": 100000.0,
            "estimate": {
                "member_responsibility_estimate": 5000.0,
            },
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility("M-1001", "99213", 100000.0)

        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_estimate_negative_billed_amount(self):
        """Test estimate with negative billed amount."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "invalid_amount",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.estimate_responsibility("M-1001", "99213", -250.0)

        assert "error" in result


class TestSearchProvidersSuccess:
    """Test successful scenarios for search_providers tool."""

    @pytest.mark.asyncio
    async def test_search_providers_by_specialty(self):
        """Test searching providers by specialty."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = [
            {
                "provider_id": "PR-2001",
                "name": "Northside Primary Care",
                "specialty": "primary care",
                "network": "in-network",
            }
        ]

        agent = HealthClaimsAgent(mock_client)
        result = await agent.search_providers("primary care")

        assert "providers" in result
        assert len(result["providers"]) > 0
        assert result["providers"][0]["specialty"] == "primary care"

    @pytest.mark.asyncio
    async def test_search_providers_with_zip_filter(self):
        """Test searching providers with ZIP code filter."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = [
            {
                "provider_id": "PR-2001",
                "zip_code": "55401",
            }
        ]

        agent = HealthClaimsAgent(mock_client)
        result = await agent.search_providers("primary care", zip_code="55401")

        assert result["providers"][0]["zip_code"] == "55401"

    @pytest.mark.asyncio
    async def test_search_providers_with_network_filter(self):
        """Test searching providers with network filter."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = [
            {
                "provider_id": "PR-2001",
                "network": "in-network",
            },
            {
                "provider_id": "PR-2002",
                "network": "in-network",
            },
        ]

        agent = HealthClaimsAgent(mock_client)
        result = await agent.search_providers(
            "orthopedics", network="in-network"
        )

        for provider in result["providers"]:
            assert provider["network"] == "in-network"

    @pytest.mark.asyncio
    async def test_search_providers_multi_filter(self):
        """Test searching providers with multiple filters."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = [
            {
                "provider_id": "PR-2001",
                "specialty": "primary care",
                "zip_code": "55401",
                "network": "in-network",
            }
        ]

        agent = HealthClaimsAgent(mock_client)
        result = await agent.search_providers(
            "primary care", zip_code="55401", network="in-network"
        )

        assert len(result["providers"]) > 0


class TestSearchProvidersNegative:
    """Test negative/edge cases for search_providers tool."""

    @pytest.mark.asyncio
    async def test_search_providers_no_results(self):
        """Test search returning no results."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = []

        agent = HealthClaimsAgent(mock_client)
        result = await agent.search_providers("nonexistent_specialty")

        assert result["providers"] == []

    @pytest.mark.asyncio
    async def test_search_providers_empty_specialty(self):
        """Test search with empty specialty."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = []

        agent = HealthClaimsAgent(mock_client)
        result = await agent.search_providers("")

        assert "providers" in result


class TestCreatePriorAuthSuccess:
    """Test successful scenarios for create_prior_authorization tool."""

    @pytest.mark.asyncio
    async def test_create_prior_auth_success(self):
        """Test successfully creating a prior authorization."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "auth_id": "PA-9002",
            "member_id": "M-1002",
            "provider_id": "PR-2002",
            "procedure_codes": ["29881"],
            "diagnosis_codes": ["S83.511A"],
            "service_date": "2024-08-15",
            "status": "pending",
            "status_reason": "clinical review",
            "decision_date": None,
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.create_prior_authorization(
            "M-1002",
            "PR-2002",
            ["29881"],
            "2024-08-15",
            diagnosis_codes=["S83.511A"],
        )

        assert result["auth_id"] == "PA-9002"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_prior_auth_multiple_procedures(self):
        """Test creating prior auth with multiple procedure codes."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "auth_id": "PA-9003",
            "procedure_codes": ["29881", "29882", "29883"],
            "status": "pending",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.create_prior_authorization(
            "M-1002",
            "PR-2002",
            ["29881", "29882", "29883"],
            "2024-08-15",
        )

        assert len(result["procedure_codes"]) == 3


class TestCreatePriorAuthFailure:
    """Test failure scenarios for create_prior_authorization tool."""

    @pytest.mark.asyncio
    async def test_create_prior_auth_member_not_found(self):
        """Test creating prior auth for non-existent member."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "member_not_found",
            "member_id": "M-9999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.create_prior_authorization(
            "M-9999", "PR-2002", ["29881"], "2024-08-15"
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_prior_auth_provider_not_found(self):
        """Test creating prior auth for non-existent provider."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "provider_not_found",
            "provider_id": "PR-9999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.create_prior_authorization(
            "M-1002", "PR-9999", ["29881"], "2024-08-15"
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_prior_auth_tool_exception(self):
        """Test exception handling when tool fails."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Authorization service error")

        agent = HealthClaimsAgent(mock_client)
        result = await agent.create_prior_authorization(
            "M-1002", "PR-2002", ["29881"], "2024-08-15"
        )

        assert "error" in result


class TestCreatePriorAuthNegative:
    """Test negative/edge cases for create_prior_authorization tool."""

    @pytest.mark.asyncio
    async def test_create_prior_auth_empty_procedure_codes(self):
        """Test creating prior auth with empty procedure codes."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "auth_id": "PA-9004",
            "procedure_codes": [],
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.create_prior_authorization(
            "M-1002", "PR-2002", [], "2024-08-15"
        )

        assert "auth_id" in result

    @pytest.mark.asyncio
    async def test_create_prior_auth_past_service_date(self):
        """Test creating prior auth with past service date."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "auth_id": "PA-9005",
            "service_date": "2020-01-01",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.create_prior_authorization(
            "M-1002", "PR-2002", ["29881"], "2020-01-01"
        )

        assert "auth_id" in result


class TestGetPriorAuthStatusSuccess:
    """Test successful scenarios for get_prior_authorization_status tool."""

    @pytest.mark.asyncio
    async def test_get_prior_auth_status_approved(self):
        """Test retrieving status of approved prior authorization."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "auth_id": "PA-9001",
            "status": "approved",
            "status_reason": "medical necessity met",
            "decision_date": "2024-07-25",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_prior_auth_status("PA-9001")

        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_get_prior_auth_status_pending(self):
        """Test retrieving status of pending prior authorization."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "auth_id": "PA-9002",
            "status": "pending",
            "status_reason": "clinical review",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_prior_auth_status("PA-9002")

        assert result["status"] == "pending"


class TestGetPriorAuthStatusFailure:
    """Test failure scenarios for get_prior_authorization_status tool."""

    @pytest.mark.asyncio
    async def test_get_prior_auth_status_not_found(self):
        """Test retrieving status of non-existent authorization."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "auth_not_found",
            "auth_id": "PA-9999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_prior_auth_status("PA-9999")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_prior_auth_status_tool_exception(self):
        """Test exception handling when tool fails."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Database timeout")

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_prior_auth_status("PA-9001")

        assert "error" in result


class TestGetPriorAuthStatusNegative:
    """Test negative/edge cases for get_prior_authorization_status tool."""

    @pytest.mark.asyncio
    async def test_get_prior_auth_status_empty_id(self):
        """Test with empty authorization ID."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"error": "auth_not_found", "auth_id": ""}

        agent = HealthClaimsAgent(mock_client)
        result = await agent.get_prior_auth_status("")

        assert "error" in result


class TestSubmitInquirySuccess:
    """Test successful scenarios for submit_claim_inquiry tool."""

    @pytest.mark.asyncio
    async def test_submit_inquiry_status_question(self):
        """Test submitting a status inquiry."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "ticket_id": "INQ-ABC12345",
            "claim_id": "C-10001",
            "inquiry_type": "status_question",
            "note": "What is the status of my claim?",
            "submitted_at": "2024-09-15T10:30:45Z",
            "status": "open",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.submit_inquiry(
            "C-10001", "status_question", "What is the status of my claim?"
        )

        assert "ticket_id" in result
        assert result["status"] == "open"

    @pytest.mark.asyncio
    async def test_submit_inquiry_appeal(self):
        """Test submitting an appeal inquiry."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "ticket_id": "INQ-XYZ67890",
            "claim_id": "C-10003",
            "inquiry_type": "appeal",
            "note": "I would like to appeal this denial.",
            "submitted_at": "2024-09-15T10:30:45Z",
            "status": "open",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.submit_inquiry(
            "C-10003", "appeal", "I would like to appeal this denial."
        )

        assert result["inquiry_type"] == "appeal"

    @pytest.mark.asyncio
    async def test_submit_inquiry_billing_question(self):
        """Test submitting a billing inquiry."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "ticket_id": "INQ-DEF45678",
            "inquiry_type": "billing",
            "status": "open",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.submit_inquiry(
            "C-10001", "billing", "Question about member responsibility amount."
        )

        assert "ticket_id" in result


class TestSubmitInquiryFailure:
    """Test failure scenarios for submit_claim_inquiry tool."""

    @pytest.mark.asyncio
    async def test_submit_inquiry_claim_not_found(self):
        """Test submitting inquiry for non-existent claim."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "error": "claim_not_found",
            "claim_id": "C-99999",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.submit_inquiry("C-99999", "status_question", "Status?")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_submit_inquiry_tool_exception(self):
        """Test exception handling when tool fails."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Ticket system error")

        agent = HealthClaimsAgent(mock_client)
        result = await agent.submit_inquiry("C-10001", "status_question", "Status?")

        assert "error" in result


class TestSubmitInquiryNegative:
    """Test negative/edge cases for submit_claim_inquiry tool."""

    @pytest.mark.asyncio
    async def test_submit_inquiry_empty_note(self):
        """Test submitting inquiry with empty note."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "ticket_id": "INQ-EMPTY",
            "note": "",
        }

        agent = HealthClaimsAgent(mock_client)
        result = await agent.submit_inquiry("C-10001", "status_question", "")

        assert "ticket_id" in result

    @pytest.mark.asyncio
    async def test_submit_inquiry_long_note(self):
        """Test submitting inquiry with very long note."""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "ticket_id": "INQ-LONG",
            "note": "x" * 5000,
        }

        agent = HealthClaimsAgent(mock_client)
        long_note = "x" * 5000
        result = await agent.submit_inquiry("C-10001", "status_question", long_note)

        assert "ticket_id" in result


class TestAgentIntegration:
    """Integration tests demonstrating agent workflows."""

    @pytest.mark.asyncio
    async def test_workflow_check_claim_and_benefits(self):
        """Test workflow: check claim details and retrieve benefits."""
        mock_client = AsyncMock()

        # First call: get claim details
        mock_client.call_tool.side_effect = [
            {
                "claim_id": "C-10001",
                "member_id": "M-1001",
                "status": "paid",
            },
            {
                "member_id": "M-1001",
                "plan": {"plan_name": "Optum Choice PPO"},
            },
        ]

        agent = HealthClaimsAgent(mock_client)
        claim = await agent.get_claim_details("C-10001")
        benefits = await agent.get_member_benefits(claim["member_id"])

        assert claim["status"] == "paid"
        assert benefits["plan"]["plan_name"] == "Optum Choice PPO"

    @pytest.mark.asyncio
    async def test_workflow_search_and_estimate(self):
        """Test workflow: search providers and estimate costs."""
        mock_client = AsyncMock()

        # First call: search providers
        mock_client.call_tool.side_effect = [
            [{"provider_id": "PR-2001", "specialty": "primary care"}],
            {
                "member_id": "M-1001",
                "estimate": {"member_responsibility_estimate": 120.0},
            },
        ]

        agent = HealthClaimsAgent(mock_client)
        providers = await agent.search_providers("primary care")
        estimate = await agent.estimate_responsibility("M-1001", "99213", 250.0)

        assert len(providers["providers"]) > 0
        assert "member_responsibility_estimate" in estimate["estimate"]

    @pytest.mark.asyncio
    async def test_workflow_prior_auth_and_status(self):
        """Test workflow: create prior auth and check status."""
        mock_client = AsyncMock()

        # First call: create prior auth
        mock_client.call_tool.side_effect = [
            {
                "auth_id": "PA-9002",
                "status": "pending",
            },
            {
                "auth_id": "PA-9002",
                "status": "approved",
            },
        ]

        agent = HealthClaimsAgent(mock_client)
        auth = await agent.create_prior_authorization(
            "M-1002", "PR-2002", ["29881"], "2024-08-15"
        )
        status = await agent.get_prior_auth_status(auth["auth_id"])

        assert auth["status"] == "pending"
        assert status["status"] == "approved"
