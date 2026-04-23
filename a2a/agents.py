"""
Healthcare Domain Agents using A2A Protocol.

Multiple specialized agents that communicate via A2A protocol
and utilize MCP tools for healthcare claims operations.
"""

from typing import Any, Optional, List
from dataclasses import dataclass
import logging
import asyncio

from .a2a_protocol import A2AProtocol, AgentInfo, AgentCapability

logger = logging.getLogger(__name__)


class HealthcareAgentBase:
    """Base class for healthcare agents."""
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        description: str,
        protocol: A2AProtocol,
        mcp_client: Any = None,
    ):
        """Initialize healthcare agent."""
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.description = description
        self.protocol = protocol
        self.mcp_client = mcp_client
        self.capabilities: List[AgentCapability] = []
    
    async def register(self) -> None:
        """Register agent with the protocol."""
        agent_info = AgentInfo(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            description=self.description,
            capabilities=self.capabilities,
        )
        self.protocol.registry.register(agent_info)
    
    async def call_mcp_tool(self, tool_name: str, params: dict) -> dict:
        """Call an MCP tool."""
        if not self.mcp_client:
            logger.warning(f"No MCP client available for agent {self.agent_id}")
            return {"error": "mcp_client_not_available"}
        
        try:
            result = await self.mcp_client.call_tool(tool_name, params)
            logger.info(f"Called MCP tool {tool_name} from {self.agent_name}")
            return result
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {str(e)}")
            return {"error": str(e), "tool": tool_name}


class MemberAssistAgent(HealthcareAgentBase):
    """
    Member Assist Agent - Patient Coordinator.
    
    Role: Coordinates member inquiries, checks eligibility, and recommends providers.
    Communicates with Claims Agent and Provider Advocate Agent.
    """
    
    def __init__(self, protocol: A2AProtocol, mcp_client: Any = None):
        super().__init__(
            agent_id="member-assist-agent",
            agent_name="Member Assist Agent",
            description="Patient coordinator that checks eligibility and recommends providers",
            protocol=protocol,
            mcp_client=mcp_client,
        )
        
        self.capabilities = [
            AgentCapability(
                name="Check Member Eligibility",
                method="check_eligibility",
                description="Check if a member is eligible and get their benefits",
                parameters={"member_id": "string"},
                tags=["eligibility", "benefits"],
            ),
            AgentCapability(
                name="Find Network Providers",
                method="find_providers",
                description="Find in-network providers for a given specialty",
                parameters={"specialty": "string", "zip_code": "string (optional)"},
                tags=["provider", "network"],
            ),
        ]
    
    async def check_eligibility(self, member_id: str) -> dict:
        """Check member eligibility via Claims Agent."""
        logger.info(f"[{self.agent_name}] Checking eligibility for member {member_id}")
        
        try:
            response = await self.protocol.send_request(
                sender_id=self.agent_id,
                recipient_id="claims-agent",
                method="check_member_eligibility",
                params={"member_id": member_id},
            )
            
            logger.info(f"[{self.agent_name}] Received eligibility response for {member_id}")
            return response.get("result", response)
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error checking eligibility: {str(e)}")
            return {"error": str(e)}
    
    async def find_providers(self, specialty: str, zip_code: Optional[str] = None) -> dict:
        """Find providers via Provider Advocate Agent."""
        logger.info(f"[{self.agent_name}] Finding providers for {specialty}")
        
        try:
            response = await self.protocol.send_request(
                sender_id=self.agent_id,
                recipient_id="provider-advocate-agent",
                method="search_network_providers",
                params={"specialty": specialty, "zip_code": zip_code},
            )
            
            logger.info(f"[{self.agent_name}] Received provider list for {specialty}")
            return response.get("result", response)
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error finding providers: {str(e)}")
            return {"error": str(e)}
    
    async def handle_check_eligibility(self, params: dict) -> dict:
        """Handle eligibility check requests from other agents."""
        member_id = params.get("member_id")
        if not member_id:
            return {"error": "member_id required"}
        
        # Call MCP server to get member benefits
        result = await self.call_mcp_tool("get_member_benefits", {"member_id": member_id})
        return {"result": result}
    
    async def handle_find_providers(self, params: dict) -> dict:
        """Handle provider search requests from other agents."""
        specialty = params.get("specialty")
        zip_code = params.get("zip_code")
        
        if not specialty:
            return {"error": "specialty required"}
        
        # Call MCP server to search providers
        result = await self.call_mcp_tool(
            "search_providers",
            {"specialty": specialty, "zip_code": zip_code, "network": "in-network"},
        )
        return {"result": result}


class ClaimsAgent(HealthcareAgentBase):
    """
    Claims Agent - Claims Processor.
    
    Role: Processes claims, tracks status, and retrieves claim history.
    Communicates with Member Assist Agent and Benefits Agent.
    """
    
    def __init__(self, protocol: A2AProtocol, mcp_client: Any = None):
        super().__init__(
            agent_id="claims-agent",
            agent_name="Claims Agent",
            description="Claims processor that reviews and tracks claims",
            protocol=protocol,
            mcp_client=mcp_client,
        )
        
        self.capabilities = [
            AgentCapability(
                name="Check Member Eligibility",
                method="check_member_eligibility",
                description="Check member eligibility and get benefits",
                parameters={"member_id": "string"},
                tags=["eligibility", "claims"],
            ),
            AgentCapability(
                name="Get Claim Details",
                method="get_claim_details",
                description="Get detailed information about a specific claim",
                parameters={"claim_id": "string"},
                tags=["claims", "details"],
            ),
            AgentCapability(
                name="Estimate Costs",
                method="estimate_member_costs",
                description="Estimate member responsibility for a procedure",
                parameters={
                    "member_id": "string",
                    "procedure_code": "string",
                    "billed_amount": "float",
                },
                tags=["costs", "estimation"],
            ),
        ]
    
    async def check_member_eligibility(self, member_id: str) -> dict:
        """Check member eligibility by getting claims and benefits."""
        logger.info(f"[{self.agent_name}] Checking eligibility for member {member_id}")
        
        claims = await self.call_mcp_tool(
            "list_member_claims",
            {"member_id": member_id},
        )
        benefits = await self.call_mcp_tool(
            "get_member_benefits",
            {"member_id": member_id},
        )
        
        return {
            "member_id": member_id,
            "claims": claims,
            "benefits": benefits,
        }
    
    async def get_claim_details_remote(self, claim_id: str) -> dict:
        """Get claim details."""
        logger.info(f"[{self.agent_name}] Getting details for claim {claim_id}")
        
        result = await self.call_mcp_tool(
            "get_claim_detail",
            {"claim_id": claim_id},
        )
        return result
    
    async def estimate_costs(
        self,
        member_id: str,
        procedure_code: str,
        billed_amount: float,
        network: str = "in-network",
    ) -> dict:
        """Estimate member costs via Benefits Agent."""
        logger.info(
            f"[{self.agent_name}] Requesting cost estimate from Benefits Agent"
        )
        
        try:
            response = await self.protocol.send_request(
                sender_id=self.agent_id,
                recipient_id="benefits-agent",
                method="calculate_member_responsibility",
                params={
                    "member_id": member_id,
                    "procedure_code": procedure_code,
                    "billed_amount": billed_amount,
                    "network": network,
                },
            )
            
            logger.info(f"[{self.agent_name}] Received cost estimate")
            return response.get("result", response)
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error estimating costs: {str(e)}")
            return {"error": str(e)}
    
    async def handle_check_member_eligibility(self, params: dict) -> dict:
        """Handle eligibility check requests."""
        member_id = params.get("member_id")
        if not member_id:
            return {"error": "member_id required"}
        
        return await self.check_member_eligibility(member_id)
    
    async def handle_get_claim_details(self, params: dict) -> dict:
        """Handle claim detail requests."""
        claim_id = params.get("claim_id")
        if not claim_id:
            return {"error": "claim_id required"}
        
        return await self.get_claim_details_remote(claim_id)
    
    async def handle_estimate_member_costs(self, params: dict) -> dict:
        """Handle cost estimation requests."""
        member_id = params.get("member_id")
        procedure_code = params.get("procedure_code")
        billed_amount = params.get("billed_amount")
        network = params.get("network", "in-network")
        
        if not all([member_id, procedure_code, billed_amount]):
            return {"error": "member_id, procedure_code, and billed_amount required"}
        
        result = await self.call_mcp_tool(
            "estimate_member_responsibility",
            {
                "member_id": member_id,
                "procedure_code": procedure_code,
                "billed_amount": billed_amount,
                "network": network,
            },
        )
        return {"result": result}


class ProviderAdvocateAgent(HealthcareAgentBase):
    """
    Provider Advocate Agent - Provider Network Manager.
    
    Role: Manages provider network information and search.
    Communicates with Member Assist Agent.
    """
    
    def __init__(self, protocol: A2AProtocol, mcp_client: Any = None):
        super().__init__(
            agent_id="provider-advocate-agent",
            agent_name="Provider Advocate Agent",
            description="Provider network manager for provider lookup and search",
            protocol=protocol,
            mcp_client=mcp_client,
        )
        
        self.capabilities = [
            AgentCapability(
                name="Search Network Providers",
                method="search_network_providers",
                description="Search for in-network providers by specialty",
                parameters={
                    "specialty": "string",
                    "zip_code": "string (optional)",
                },
                tags=["provider", "network", "search"],
            ),
        ]
    
    async def search_providers(
        self,
        specialty: str,
        zip_code: Optional[str] = None,
        network: str = "in-network",
    ) -> dict:
        """Search for providers."""
        logger.info(
            f"[{self.agent_name}] Searching providers for {specialty} in {zip_code or 'any location'}"
        )
        
        result = await self.call_mcp_tool(
            "search_providers",
            {
                "specialty": specialty,
                "zip_code": zip_code,
                "network": network,
            },
        )
        return result
    
    async def handle_search_network_providers(self, params: dict) -> dict:
        """Handle provider search requests."""
        specialty = params.get("specialty")
        zip_code = params.get("zip_code")
        network = params.get("network", "in-network")
        
        if not specialty:
            return {"error": "specialty required"}
        
        result = await self.search_providers(specialty, zip_code, network)
        return {"result": result}


class BenefitsAgent(HealthcareAgentBase):
    """
    Benefits Agent - Benefits Specialist.
    
    Role: Handles benefit information and cost estimations.
    Communicates with Claims Agent.
    """
    
    def __init__(self, protocol: A2AProtocol, mcp_client: Any = None):
        super().__init__(
            agent_id="benefits-agent",
            agent_name="Benefits Agent",
            description="Benefits specialist that handles coverage and cost estimations",
            protocol=protocol,
            mcp_client=mcp_client,
        )
        
        self.capabilities = [
            AgentCapability(
                name="Calculate Member Responsibility",
                method="calculate_member_responsibility",
                description="Calculate member's financial responsibility for a procedure",
                parameters={
                    "member_id": "string",
                    "procedure_code": "string",
                    "billed_amount": "float",
                    "network": "string (optional)",
                },
                tags=["benefits", "costs", "estimation"],
            ),
        ]
    
    async def calculate_responsibility(
        self,
        member_id: str,
        procedure_code: str,
        billed_amount: float,
        network: str = "in-network",
    ) -> dict:
        """Calculate member responsibility."""
        logger.info(
            f"[{self.agent_name}] Calculating responsibility for {member_id}"
        )
        
        result = await self.call_mcp_tool(
            "estimate_member_responsibility",
            {
                "member_id": member_id,
                "procedure_code": procedure_code,
                "billed_amount": billed_amount,
                "network": network,
            },
        )
        return result
    
    async def handle_calculate_member_responsibility(self, params: dict) -> dict:
        """Handle member responsibility calculation requests."""
        member_id = params.get("member_id")
        procedure_code = params.get("procedure_code")
        billed_amount = params.get("billed_amount")
        network = params.get("network", "in-network")
        
        if not all([member_id, procedure_code, billed_amount]):
            return {"error": "member_id, procedure_code, and billed_amount required"}
        
        result = await self.calculate_responsibility(
            member_id, procedure_code, billed_amount, network
        )
        return {"result": result}
