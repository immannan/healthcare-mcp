"""
Unit tests for A2A Agent-to-Agent Communication Protocol.

Tests agent registration, message handling, protocol communication,
and interactions between healthcare domain agents.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from a2a import (
    A2AMessage,
    A2ARequest,
    A2AResponse,
    A2AError,
    MessageType,
    A2AProtocol,
    AgentRegistry,
    AgentInfo,
    AgentCapability,
    MemberAssistAgent,
    ClaimsAgent,
    ProviderAdvocateAgent,
    BenefitsAgent,
    Task,
    TaskState,
    TaskStatus,
    TaskMessage,
    TaskManager,
    TextPart,
    DataPart,
    FilePart,
    Artifact,
)
from a2a.task import _part_from_dict


# ============================================================================
# Message Tests
# ============================================================================


class TestA2AMessage:
    """Test A2A message creation and serialization."""

    def test_message_creation(self):
        """Test creating an A2A message."""
        msg = A2AMessage(
            method="test_method",
            params={"key": "value"},
            sender="agent-1",
            recipient="agent-2",
        )
        
        assert msg.method == "test_method"
        assert msg.params == {"key": "value"}
        assert msg.sender == "agent-1"
        assert msg.recipient == "agent-2"
        assert msg.jsonrpc == "2.0"
        assert msg.message_type == MessageType.REQUEST

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = A2AMessage(
            method="check_status",
            params={"id": "123"},
            sender="agent-1",
            recipient="agent-2",
            result={"status": "active"},
        )
        
        msg_dict = msg.to_dict()
        
        assert msg_dict["method"] == "check_status"
        assert msg_dict["params"] == {"id": "123"}
        assert msg_dict["sender"] == "agent-1"
        assert msg_dict["recipient"] == "agent-2"
        assert msg_dict["result"] == {"status": "active"}

    def test_message_to_json(self):
        """Test converting message to JSON."""
        msg = A2AMessage(
            method="get_data",
            params={"filter": "active"},
            sender="agent-1",
            recipient="agent-2",
        )
        
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["method"] == "get_data"
        assert parsed["sender"] == "agent-1"
        assert parsed["recipient"] == "agent-2"

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"key": "val"},
            "sender": "A",
            "recipient": "B",
            "type": "request",
        }
        
        msg = A2AMessage.from_dict(data)
        
        assert msg.method == "test"
        assert msg.sender == "A"
        assert msg.recipient == "B"
        assert msg.message_type == MessageType.REQUEST

    def test_message_from_json(self):
        """Test creating message from JSON string."""
        json_str = '{"jsonrpc": "2.0", "method": "test", "sender": "A", "recipient": "B"}'
        
        msg = A2AMessage.from_json(json_str)
        
        assert msg.method == "test"
        assert msg.sender == "A"


class TestA2ARequest:
    """Test A2A request helper class."""

    def test_request_creation(self):
        """Test creating an A2A request."""
        req = A2ARequest(
            sender="agent-1",
            recipient="agent-2",
            method="call_method",
            params={"arg": "value"},
        )
        
        assert req.sender == "agent-1"
        assert req.recipient == "agent-2"
        assert req.method == "call_method"

    def test_request_to_message(self):
        """Test converting request to message."""
        req = A2ARequest(
            sender="agent-1",
            recipient="agent-2",
            method="process",
            params={"data": "test"},
        )
        
        msg = req.to_message()
        
        assert msg.message_type == MessageType.REQUEST
        assert msg.method == "process"
        assert msg.sender == "agent-1"


class TestA2AResponse:
    """Test A2A response helper class."""

    def test_response_creation(self):
        """Test creating an A2A response."""
        resp = A2AResponse(
            sender="agent-2",
            recipient="agent-1",
            request_id="req-123",
            result={"status": "success"},
        )
        
        assert resp.sender == "agent-2"
        assert resp.request_id == "req-123"
        assert resp.result == {"status": "success"}

    def test_response_to_message(self):
        """Test converting response to message."""
        resp = A2AResponse(
            sender="agent-2",
            recipient="agent-1",
            request_id="req-123",
            result={"data": "result"},
        )
        
        msg = resp.to_message()
        
        assert msg.message_type == MessageType.RESPONSE
        assert msg.id == "req-123"
        assert msg.result == {"data": "result"}


class TestA2AError:
    """Test A2A error helper class."""

    def test_error_creation(self):
        """Test creating an A2A error."""
        err = A2AError(
            sender="agent-2",
            recipient="agent-1",
            request_id="req-123",
            code=-32601,
            message="Method not found",
        )
        
        assert err.sender == "agent-2"
        assert err.code == -32601
        assert err.message == "Method not found"

    def test_error_to_message(self):
        """Test converting error to message."""
        err = A2AError(
            sender="agent-2",
            recipient="agent-1",
            request_id="req-123",
            code=-32603,
            message="Internal error",
            data={"details": "Something went wrong"},
        )
        
        msg = err.to_message()
        
        assert msg.message_type == MessageType.ERROR
        assert msg.error["code"] == -32603
        assert msg.error["message"] == "Internal error"
        assert msg.error["data"]["details"] == "Something went wrong"


# ============================================================================
# Protocol and Registry Tests
# ============================================================================


class TestAgentRegistry:
    """Test agent registry functionality."""

    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        
        agent_info = AgentInfo(
            agent_id="agent-1",
            agent_name="Test Agent",
            description="A test agent",
            capabilities=[],
        )
        
        registry.register(agent_info)
        
        retrieved = registry.get_agent("agent-1")
        assert retrieved is not None
        assert retrieved.agent_name == "Test Agent"

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()
        
        agent_info = AgentInfo(
            agent_id="agent-1",
            agent_name="Test Agent",
            description="A test agent",
            capabilities=[],
        )
        
        registry.register(agent_info)
        registry.unregister("agent-1")
        
        retrieved = registry.get_agent("agent-1")
        assert retrieved is None

    def test_find_agents_by_capability(self):
        """Test finding agents by capability."""
        registry = AgentRegistry()
        
        cap1 = AgentCapability(
            id="check-status",
            name="Check Status",
            method="check_status",
            description="Check status",
            tags=["status"],
        )
        
        agent_info1 = AgentInfo(
            agent_id="agent-1",
            agent_name="Status Agent",
            description="Agent for status",
            capabilities=[cap1],
        )
        
        agent_info2 = AgentInfo(
            agent_id="agent-2",
            agent_name="Data Agent",
            description="Agent for data",
            capabilities=[],
        )
        
        registry.register(agent_info1)
        registry.register(agent_info2)
        
        results = registry.find_agents_by_capability("check_status")
        assert len(results) == 1
        assert results[0].agent_id == "agent-1"

    def test_list_all_agents(self):
        """Test listing all agents."""
        registry = AgentRegistry()
        
        for i in range(3):
            agent_info = AgentInfo(
                agent_id=f"agent-{i}",
                agent_name=f"Agent {i}",
                description="Test agent",
                capabilities=[],
            )
            registry.register(agent_info)
        
        agents = registry.list_all_agents()
        assert len(agents) == 3


class TestA2AProtocol:
    """Test A2A protocol functionality."""

    def test_protocol_creation(self):
        """Test creating a protocol instance."""
        protocol = A2AProtocol()
        
        assert protocol.registry is not None
        assert isinstance(protocol.registry, AgentRegistry)

    def test_register_handler(self):
        """Test registering a message handler."""
        protocol = A2AProtocol()
        
        async def test_handler(params):
            return {"result": "success"}
        
        protocol.register_handler("test_method", test_handler)
        
        assert "test_method" in protocol._handlers

    @pytest.mark.asyncio
    async def test_send_request_timeout(self):
        """Test request timeout."""
        protocol = A2AProtocol()
        
        with pytest.raises(TimeoutError):
            await protocol.send_request(
                sender_id="agent-1",
                recipient_id="agent-2",
                method="slow_method",
                params={},
                timeout=0.1,
            )

    @pytest.mark.asyncio
    async def test_handle_request_success(self):
        """Test handling a successful request."""
        protocol = A2AProtocol()
        
        async def handler(params):
            return {"status": "ok", "data": params}
        
        protocol.register_handler("process", handler)
        
        message = A2AMessage(
            method="process",
            params={"input": "test"},
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.REQUEST,
        )
        
        response = await protocol.handle_message(message)
        
        assert response is not None
        assert response.message_type == MessageType.RESPONSE
        assert response.result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_handle_request_unknown_method(self):
        """Test handling request with unknown method."""
        protocol = A2AProtocol()
        
        message = A2AMessage(
            method="unknown_method",
            params={},
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.REQUEST,
        )
        
        response = await protocol.handle_message(message)
        
        assert response is not None
        assert response.message_type == MessageType.ERROR
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_discover_agents(self):
        """Test agent discovery."""
        protocol = A2AProtocol()
        
        capability = AgentCapability(
            id="test-capability",
            name="Test",
            method="test",
            description="Test capability",
        )
        
        agent_info = AgentInfo(
            agent_id="agent-1",
            agent_name="Test Agent",
            description="Test agent",
            capabilities=[capability],
        )
        
        protocol.registry.register(agent_info)
        
        agents = protocol.discover_agents("test")
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-1"


# ============================================================================
# Healthcare Agent Tests
# ============================================================================


class TestMemberAssistAgent:
    """Test Member Assist Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        agent = MemberAssistAgent(protocol, mcp_client)
        
        assert agent.agent_id == "member-assist-agent"
        assert agent.agent_name == "Member Assist Agent"
        assert len(agent.capabilities) > 0

    @pytest.mark.asyncio
    async def test_agent_registration(self):
        """Test agent registration."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        agent = MemberAssistAgent(protocol, mcp_client)
        await agent.register()
        
        registered = protocol.registry.get_agent(agent.agent_id)
        assert registered is not None
        assert registered.agent_name == "Member Assist Agent"

    @pytest.mark.asyncio
    async def test_mcp_tool_call(self):
        """Test calling MCP tool."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        mcp_client.call_tool.return_value = {"member_id": "M-1001", "name": "John"}
        
        agent = MemberAssistAgent(protocol, mcp_client)
        result = await agent.call_mcp_tool("get_member", {"member_id": "M-1001"})
        
        assert result["member_id"] == "M-1001"
        mcp_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_check_eligibility(self):
        """Test handling eligibility check."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        mcp_client.call_tool.return_value = {
            "member_id": "M-1001",
            "plan": {"plan_id": "P-100"},
        }
        
        agent = MemberAssistAgent(protocol, mcp_client)
        result = await agent.handle_check_eligibility({"member_id": "M-1001"})
        
        assert "result" in result
        assert result["result"]["member_id"] == "M-1001"

    @pytest.mark.asyncio
    async def test_handle_check_eligibility_missing_member_id(self):
        """Test handling eligibility check without member_id."""
        protocol = A2AProtocol()
        agent = MemberAssistAgent(protocol)
        
        result = await agent.handle_check_eligibility({})
        
        assert "error" in result


class TestClaimsAgent:
    """Test Claims Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        agent = ClaimsAgent(protocol, mcp_client)
        
        assert agent.agent_id == "claims-agent"
        assert agent.agent_name == "Claims Agent"
        assert len(agent.capabilities) > 0

    @pytest.mark.asyncio
    async def test_agent_registration(self):
        """Test agent registration."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        agent = ClaimsAgent(protocol, mcp_client)
        await agent.register()
        
        registered = protocol.registry.get_agent(agent.agent_id)
        assert registered is not None

    @pytest.mark.asyncio
    async def test_check_member_eligibility(self):
        """Test checking member eligibility."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        mcp_client.call_tool.side_effect = [
            {"claims": [{"claim_id": "C-1"}]},
            {"plan": {"plan_id": "P-100"}},
        ]
        
        agent = ClaimsAgent(protocol, mcp_client)
        result = await agent.check_member_eligibility("M-1001")
        
        assert "claims" in result
        assert "benefits" in result
        assert result["member_id"] == "M-1001"

    @pytest.mark.asyncio
    async def test_handle_estimate_member_costs(self):
        """Test handling cost estimation."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        mcp_client.call_tool.return_value = {
            "estimate": {"member_responsibility": 150.0},
        }
        
        agent = ClaimsAgent(protocol, mcp_client)
        result = await agent.handle_estimate_member_costs({
            "member_id": "M-1001",
            "procedure_code": "99213",
            "billed_amount": 300.0,
        })
        
        assert "result" in result


class TestProviderAdvocateAgent:
    """Test Provider Advocate Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        agent = ProviderAdvocateAgent(protocol, mcp_client)
        
        assert agent.agent_id == "provider-advocate-agent"
        assert agent.agent_name == "Provider Advocate Agent"

    @pytest.mark.asyncio
    async def test_search_providers(self):
        """Test searching providers."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        mcp_client.call_tool.return_value = [
            {"provider_id": "PR-001", "name": "Provider 1"},
        ]
        
        agent = ProviderAdvocateAgent(protocol, mcp_client)
        result = await agent.search_providers("primary care")
        
        assert len(result) > 0
        mcp_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_search_network_providers(self):
        """Test handling provider search request."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        mcp_client.call_tool.return_value = [
            {"provider_id": "PR-001", "specialty": "primary care"},
        ]
        
        agent = ProviderAdvocateAgent(protocol, mcp_client)
        result = await agent.handle_search_network_providers({
            "specialty": "primary care",
        })
        
        assert "result" in result


class TestBenefitsAgent:
    """Test Benefits Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        agent = BenefitsAgent(protocol, mcp_client)
        
        assert agent.agent_id == "benefits-agent"
        assert agent.agent_name == "Benefits Agent"

    @pytest.mark.asyncio
    async def test_calculate_responsibility(self):
        """Test calculating member responsibility."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        mcp_client.call_tool.return_value = {
            "estimate": {
                "member_responsibility_estimate": 150.0,
            },
        }
        
        agent = BenefitsAgent(protocol, mcp_client)
        result = await agent.calculate_responsibility(
            "M-1001",
            "99213",
            300.0,
        )
        
        assert "estimate" in result
        mcp_client.call_tool.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================


class TestA2AIntegration:
    """Integration tests for A2A agent communication."""

    @pytest.mark.asyncio
    async def test_agent_discovery_workflow(self):
        """Test agent discovery workflow."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        # Create and register agents
        member_assist = MemberAssistAgent(protocol, mcp_client)
        claims = ClaimsAgent(protocol, mcp_client)
        provider_advocate = ProviderAdvocateAgent(protocol, mcp_client)
        benefits = BenefitsAgent(protocol, mcp_client)
        
        await member_assist.register()
        await claims.register()
        await provider_advocate.register()
        await benefits.register()
        
        # Discover agents
        all_agents = protocol.discover_agents()
        assert len(all_agents) == 4
        
        # Discover by capability
        eligibility_agents = protocol.discover_agents("check_member_eligibility")
        assert len(eligibility_agents) >= 1

    @pytest.mark.asyncio
    async def test_agent_to_agent_communication(self):
        """Test communication between agents."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        # Setup agents
        member_assist = MemberAssistAgent(protocol, mcp_client)
        claims = ClaimsAgent(protocol, mcp_client)
        
        # Register request handler for Claims Agent
        async def eligibility_handler(params):
            return {
                "member_id": params["member_id"],
                "eligible": True,
            }
        
        protocol.register_handler("check_member_eligibility", eligibility_handler)
        
        await member_assist.register()
        await claims.register()
        
        # Test A2A request/response
        message = A2ARequest(
            sender=member_assist.agent_id,
            recipient=claims.agent_id,
            method="check_member_eligibility",
            params={"member_id": "M-1001"},
        ).to_message()
        
        response = await protocol.handle_message(message)
        
        assert response is not None
        assert response.message_type == MessageType.RESPONSE
        assert response.result["eligible"] is True

    @pytest.mark.asyncio
    async def test_multiple_agent_coordination(self):
        """Test multiple agents coordinating together."""
        protocol = A2AProtocol()
        mcp_client = AsyncMock()
        
        # Setup MCP responses
        mcp_client.call_tool.side_effect = [
            # For get_member_benefits
            {"plan": {"plan_id": "P-100", "deductible_total": 1500}},
            # For estimate_member_responsibility
            {"estimate": {"member_responsibility_estimate": 150.0}},
        ]
        
        # Create agents
        member_assist = MemberAssistAgent(protocol, mcp_client)
        claims = ClaimsAgent(protocol, mcp_client)
        benefits = BenefitsAgent(protocol, mcp_client)
        
        # Register handlers
        protocol.register_handler(
            "check_member_eligibility",
            claims.handle_check_member_eligibility,
        )
        protocol.register_handler(
            "calculate_member_responsibility",
            benefits.handle_calculate_member_responsibility,
        )
        
        # Register agents
        await member_assist.register()
        await claims.register()
        await benefits.register()
        
        # Verify all agents are registered
        agents = protocol.discover_agents()
        assert len(agents) == 3


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestA2AErrorHandling:
    """Test error handling in A2A protocol."""

    @pytest.mark.asyncio
    async def test_handler_exception_handling(self):
        """Test handling of exceptions in handlers."""
        protocol = A2AProtocol()
        
        async def failing_handler(params):
            raise ValueError("Handler failed")
        
        protocol.register_handler("failing_method", failing_handler)
        
        message = A2AMessage(
            method="failing_method",
            params={},
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.REQUEST,
        )
        
        response = await protocol.handle_message(message)
        
        assert response.message_type == MessageType.ERROR
        assert "Handler failed" in response.error["message"]

    @pytest.mark.asyncio
    async def test_missing_required_params(self):
        """Test handling of missing required parameters."""
        protocol = A2AProtocol()
        agent = BenefitsAgent(protocol)
        
        result = await agent.handle_calculate_member_responsibility({
            "member_id": "M-1001",
            # Missing procedure_code and billed_amount
        })
        
        assert "error" in result


# ============================================================================
# Task Layer Tests
# ============================================================================

class TestTaskState:
    def test_enum_values(self):
        assert TaskState.SUBMITTED.value == "submitted"
        assert TaskState.WORKING.value == "working"
        assert TaskState.INPUT_REQUIRED.value == "input-required"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.CANCELLED.value == "cancelled"

    def test_is_terminal_true(self):
        assert TaskState.COMPLETED.is_terminal
        assert TaskState.FAILED.is_terminal
        assert TaskState.CANCELLED.is_terminal

    def test_is_terminal_false(self):
        assert not TaskState.SUBMITTED.is_terminal
        assert not TaskState.WORKING.is_terminal
        assert not TaskState.INPUT_REQUIRED.is_terminal


class TestTaskParts:
    def test_text_part_to_dict(self):
        part = TextPart(text="hello")
        d = part.to_dict()
        assert d == {"type": "text", "text": "hello"}

    def test_data_part_to_dict(self):
        part = DataPart(data={"member_id": "M-1001"})
        d = part.to_dict()
        assert d == {"type": "data", "data": {"member_id": "M-1001"}}

    def test_file_part_to_dict_with_uri(self):
        part = FilePart(mime_type="application/pdf", uri="s3://bucket/file.pdf")
        d = part.to_dict()
        assert d["type"] == "file"
        assert d["mimeType"] == "application/pdf"
        assert d["uri"] == "s3://bucket/file.pdf"

    def test_file_part_to_dict_without_uri(self):
        part = FilePart()
        d = part.to_dict()
        assert "uri" not in d

    def test_part_from_dict_text(self):
        part = _part_from_dict({"type": "text", "text": "hello"})
        assert isinstance(part, TextPart)
        assert part.text == "hello"

    def test_part_from_dict_data(self):
        part = _part_from_dict({"type": "data", "data": {"x": 1}})
        assert isinstance(part, DataPart)
        assert part.data == {"x": 1}

    def test_part_from_dict_file(self):
        part = _part_from_dict({"type": "file", "mimeType": "image/png", "uri": "http://example.com/img.png"})
        assert isinstance(part, FilePart)
        assert part.uri == "http://example.com/img.png"

    def test_part_from_dict_defaults_to_text(self):
        part = _part_from_dict({"text": "fallback"})
        assert isinstance(part, TextPart)


class TestTaskMessage:
    def test_creation(self):
        msg = TaskMessage(role="user", parts=[TextPart(text="hi")])
        assert msg.role == "user"
        assert len(msg.parts) == 1

    def test_to_dict(self):
        msg = TaskMessage(role="agent", parts=[DataPart(data={"k": "v"})])
        d = msg.to_dict()
        assert d["role"] == "agent"
        assert d["parts"][0]["type"] == "data"

    def test_classmethods(self):
        u = TaskMessage.user_text("check M-1001")
        assert u.role == "user"
        assert isinstance(u.parts[0], TextPart)

        a = TaskMessage.agent_text("done")
        assert a.role == "agent"
        assert isinstance(a.parts[0], TextPart)

        ad = TaskMessage.agent_data({"result": 42})
        assert ad.role == "agent"
        assert isinstance(ad.parts[0], DataPart)
        assert ad.parts[0].data["result"] == 42

    def test_from_dict_round_trip(self):
        original = TaskMessage(role="user", parts=[TextPart(text="test"), DataPart(data={"n": 1})])
        restored = TaskMessage.from_dict(original.to_dict())
        assert restored.role == "user"
        assert len(restored.parts) == 2
        assert isinstance(restored.parts[0], TextPart)
        assert isinstance(restored.parts[1], DataPart)


class TestArtifact:
    def test_creation(self):
        art = Artifact(name="eligibility_result", parts=[DataPart(data={"eligible": True})])
        assert art.name == "eligibility_result"
        assert art.index == 0

    def test_to_dict(self):
        art = Artifact(name="result", description="check output", parts=[TextPart(text="ok")])
        d = art.to_dict()
        assert d["name"] == "result"
        assert d["description"] == "check output"
        assert d["parts"][0]["type"] == "text"


class TestTask:
    def test_creation_defaults(self):
        task = Task()
        assert task.id is not None
        assert task.status.state == TaskState.SUBMITTED
        assert task.messages == []
        assert task.artifacts == []

    def test_to_dict_structure(self):
        task = Task(id="task-001")
        d = task.to_dict()
        assert d["id"] == "task-001"
        assert d["status"]["state"] == "submitted"
        assert d["messages"] == []
        assert d["artifacts"] == []
        assert "sessionId" not in d

    def test_session_id_included_when_set(self):
        task = Task(id="task-002", session_id="sess-99")
        d = task.to_dict()
        assert d["sessionId"] == "sess-99"


class TestTaskManager:
    def test_create_stores_task(self):
        mgr = TaskManager()
        task = mgr.create()
        assert task.status.state == TaskState.SUBMITTED
        assert mgr.get(task.id) is task

    def test_get_nonexistent_returns_none(self):
        mgr = TaskManager()
        assert mgr.get("does-not-exist") is None

    def test_update_state(self):
        mgr = TaskManager()
        task = mgr.create()
        mgr.update_state(task.id, TaskState.WORKING)
        assert task.status.state == TaskState.WORKING

    def test_cancel_active_task(self):
        mgr = TaskManager()
        task = mgr.create()
        mgr.cancel(task.id)
        assert task.status.state == TaskState.CANCELLED

    def test_cancel_terminal_task_is_noop(self):
        mgr = TaskManager()
        task = mgr.create()
        mgr.update_state(task.id, TaskState.COMPLETED)
        mgr.cancel(task.id)
        assert task.status.state == TaskState.COMPLETED

    def test_add_message_and_artifact(self):
        mgr = TaskManager()
        task = mgr.create()
        mgr.add_message(task.id, TaskMessage.user_text("hello"))
        mgr.add_artifact(task.id, Artifact(name="out", parts=[TextPart(text="done")]))
        assert len(task.messages) == 1
        assert len(task.artifacts) == 1

    def test_list_all(self):
        mgr = TaskManager()
        mgr.create()
        mgr.create()
        assert len(mgr.list_all()) == 2


class TestA2AProtocolTasks:
    @pytest.mark.asyncio
    async def test_tasks_send_success(self):
        protocol = A2AProtocol()

        async def handler(params):
            return {"member_id": params.get("member_id"), "eligible": True}

        protocol.register_handler("check_member_eligibility", handler)

        message = A2AMessage(
            method="tasks/send",
            params={
                "id": "task-send-001",
                "skill": "check_member_eligibility",
                "message": {
                    "role": "user",
                    "parts": [{"type": "data", "data": {"member_id": "M-1001"}}],
                },
            },
            sender="test-client",
            recipient="claims-agent",
            message_type=MessageType.REQUEST,
        )
        response = await protocol.handle_message(message)

        assert response is not None
        assert response.message_type == MessageType.RESPONSE
        task_dict = response.result
        assert task_dict["id"] == "task-send-001"
        assert task_dict["status"]["state"] == "completed"
        assert len(task_dict["artifacts"]) == 1
        assert task_dict["artifacts"][0]["parts"][0]["data"]["eligible"] is True

    @pytest.mark.asyncio
    async def test_tasks_send_unknown_skill(self):
        protocol = A2AProtocol()

        message = A2AMessage(
            method="tasks/send",
            params={"id": "task-fail-001", "skill": "nonexistent_skill"},
            sender="client",
            recipient="agent",
            message_type=MessageType.REQUEST,
        )
        response = await protocol.handle_message(message)

        assert response.message_type == MessageType.ERROR
        # Task should be stored and marked failed
        task = protocol.tasks.get("task-fail-001")
        assert task is not None
        assert task.status.state == TaskState.FAILED

    @pytest.mark.asyncio
    async def test_tasks_get_found(self):
        protocol = A2AProtocol()
        protocol.register_handler("ping", lambda p: {"pong": True})

        # Create task via tasks/send
        send_msg = A2AMessage(
            method="tasks/send",
            params={"id": "task-get-001", "skill": "ping"},
            sender="client", recipient="agent",
            message_type=MessageType.REQUEST,
        )
        await protocol.handle_message(send_msg)

        # Retrieve via tasks/get
        get_msg = A2AMessage(
            method="tasks/get",
            params={"id": "task-get-001"},
            sender="client", recipient="agent",
            message_type=MessageType.REQUEST,
        )
        response = await protocol.handle_message(get_msg)

        assert response.message_type == MessageType.RESPONSE
        assert response.result["id"] == "task-get-001"
        assert response.result["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_tasks_get_not_found(self):
        protocol = A2AProtocol()
        message = A2AMessage(
            method="tasks/get",
            params={"id": "does-not-exist"},
            sender="client", recipient="agent",
            message_type=MessageType.REQUEST,
        )
        response = await protocol.handle_message(message)
        assert response.message_type == MessageType.ERROR
        assert response.error["code"] == -32001

    @pytest.mark.asyncio
    async def test_tasks_cancel(self):
        protocol = A2AProtocol()
        # Create a task directly in the manager (simulates a long-running task)
        task = protocol.tasks.create(task_id="task-cancel-001")

        cancel_msg = A2AMessage(
            method="tasks/cancel",
            params={"id": "task-cancel-001"},
            sender="client", recipient="agent",
            message_type=MessageType.REQUEST,
        )
        response = await protocol.handle_message(cancel_msg)

        assert response.message_type == MessageType.RESPONSE
        assert response.result["status"]["state"] == "cancelled"
        assert task.status.state == TaskState.CANCELLED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
