"""
Agent that interacts with the Health Claims MCP server.
This agent demonstrates calling MCP tools and handling responses.
"""

from typing import Any
import json


class HealthClaimsAgent:
    """Agent for interacting with health claims MCP server."""

    def __init__(self, mcp_client: Any):
        """Initialize agent with MCP client.
        
        Args:
            mcp_client: MCP client instance for tool calls
        """
        self.mcp_client = mcp_client

    async def get_member_claims(self, member_id: str, status: str = None) -> dict:
        """Get claims for a member.
        
        Args:
            member_id: Member ID to retrieve claims for
            status: Optional status filter (paid, pending, denied)
            
        Returns:
            Dictionary with member claims or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "list_member_claims",
                {"member_id": member_id, "status": status},
            )
            return result
        except Exception as e:
            return {"error": str(e), "tool": "list_member_claims"}

    async def get_claim_details(self, claim_id: str) -> dict:
        """Get detailed information about a claim.
        
        Args:
            claim_id: Claim ID to retrieve
            
        Returns:
            Dictionary with claim details or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "get_claim_detail",
                {"claim_id": claim_id},
            )
            return result
        except Exception as e:
            return {"error": str(e), "tool": "get_claim_detail"}

    async def get_member_benefits(self, member_id: str) -> dict:
        """Get member's benefit information.
        
        Args:
            member_id: Member ID to retrieve benefits for
            
        Returns:
            Dictionary with benefit information or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "get_member_benefits",
                {"member_id": member_id},
            )
            return result
        except Exception as e:
            return {"error": str(e), "tool": "get_member_benefits"}

    async def estimate_responsibility(
        self,
        member_id: str,
        procedure_code: str,
        billed_amount: float,
        network: str = "in-network",
    ) -> dict:
        """Estimate member responsibility for a procedure.
        
        Args:
            member_id: Member ID
            procedure_code: Medical procedure code
            billed_amount: Amount billed for the procedure
            network: Network type (in-network or out-of-network)
            
        Returns:
            Dictionary with cost estimate or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "estimate_member_responsibility",
                {
                    "member_id": member_id,
                    "procedure_code": procedure_code,
                    "billed_amount": billed_amount,
                    "network": network,
                },
            )
            return result
        except Exception as e:
            return {"error": str(e), "tool": "estimate_member_responsibility"}

    async def search_providers(
        self, specialty: str, zip_code: str = None, network: str = None
    ) -> dict:
        """Search for providers.
        
        Args:
            specialty: Medical specialty to search for
            zip_code: Optional ZIP code filter
            network: Optional network filter (in-network or out-of-network)
            
        Returns:
            Dictionary with provider search results or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "search_providers",
                {"specialty": specialty, "zip_code": zip_code, "network": network},
            )
            return {"providers": result}
        except Exception as e:
            return {"error": str(e), "tool": "search_providers"}

    async def create_prior_authorization(
        self,
        member_id: str,
        provider_id: str,
        procedure_codes: list,
        service_date: str,
        diagnosis_codes: list = None,
    ) -> dict:
        """Create a prior authorization request.
        
        Args:
            member_id: Member ID
            provider_id: Provider ID
            procedure_codes: List of procedure codes
            service_date: Proposed service date
            diagnosis_codes: Optional list of diagnosis codes
            
        Returns:
            Dictionary with authorization details or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "create_prior_authorization",
                {
                    "member_id": member_id,
                    "provider_id": provider_id,
                    "procedure_codes": procedure_codes,
                    "service_date": service_date,
                    "diagnosis_codes": diagnosis_codes,
                },
            )
            return result
        except Exception as e:
            return {"error": str(e), "tool": "create_prior_authorization"}

    async def get_prior_auth_status(self, auth_id: str) -> dict:
        """Get status of a prior authorization.
        
        Args:
            auth_id: Authorization ID
            
        Returns:
            Dictionary with authorization status or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "get_prior_authorization_status",
                {"auth_id": auth_id},
            )
            return result
        except Exception as e:
            return {"error": str(e), "tool": "get_prior_authorization_status"}

    async def submit_inquiry(
        self, claim_id: str, inquiry_type: str, note: str
    ) -> dict:
        """Submit a claim inquiry.
        
        Args:
            claim_id: Claim ID to inquire about
            inquiry_type: Type of inquiry
            note: Inquiry note/message
            
        Returns:
            Dictionary with inquiry ticket details or error
        """
        try:
            result = await self.mcp_client.call_tool(
                "submit_claim_inquiry",
                {"claim_id": claim_id, "inquiry_type": inquiry_type, "note": note},
            )
            return result
        except Exception as e:
            return {"error": str(e), "tool": "submit_claim_inquiry"}
