"""
A2A Protocol - Agent-to-Agent Communication Protocol.

Implements a protocol for agents to discover each other, communicate,
and delegate tasks asynchronously using JSON-RPC 2.0 format.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

from .message import A2AMessage, A2ARequest, A2AResponse, A2AError, MessageType

logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Description of an agent's capability/skill."""
    
    name: str
    method: str
    description: str
    parameters: Dict[str, Any]
    tags: List[str] = None


@dataclass
class AgentInfo:
    """Agent registration information."""
    
    agent_id: str
    agent_name: str
    description: str
    capabilities: List[AgentCapability]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class AgentRegistry:
    """Registry for discovering and managing agent information."""
    
    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
    
    def register(self, agent_info: AgentInfo) -> None:
        """Register an agent in the registry."""
        self._agents[agent_info.agent_id] = agent_info
        logger.info(f"Registered agent: {agent_info.agent_name} ({agent_info.agent_id})")
    
    def unregister(self, agent_id: str) -> None:
        """Unregister an agent from the registry."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information by ID."""
        return self._agents.get(agent_id)
    
    def find_agents_by_capability(self, method: str, tags: List[str] = None) -> List[AgentInfo]:
        """Find agents that support a specific capability."""
        results = []
        for agent in self._agents.values():
            for cap in agent.capabilities:
                if cap.method == method:
                    if tags is None or any(tag in cap.tags for tag in tags):
                        results.append(agent)
                        break
        return results
    
    def list_all_agents(self) -> List[AgentInfo]:
        """List all registered agents."""
        return list(self._agents.values())


class A2AProtocol:
    """
    Agent-to-Agent Protocol implementation.
    
    Manages agent registration, message routing, and communication.
    """
    
    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self._handlers: Dict[str, Callable] = {}
        self._request_queue: asyncio.Queue = asyncio.Queue()
        self._response_handlers: Dict[str, asyncio.Event] = {}
        self._response_data: Dict[str, Any] = {}
    
    def register_handler(self, method: str, handler: Callable) -> None:
        """Register a message handler for a specific method."""
        self._handlers[method] = handler
        logger.info(f"Registered handler for method: {method}")
    
    async def send_request(
        self,
        sender_id: str,
        recipient_id: str,
        method: str,
        params: dict,
        timeout: float = 30.0,
    ) -> dict:
        """
        Send a request to another agent and wait for response.
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the receiving agent
            method: Method name to call
            params: Method parameters
            timeout: Maximum wait time for response in seconds
            
        Returns:
            Response data from the recipient agent
        """
        request = A2ARequest(
            sender=sender_id,
            recipient=recipient_id,
            method=method,
            params=params,
        )
        message = request.to_message()
        
        logger.info(
            f"Sending A2A request from {sender_id} to {recipient_id}: {method}"
        )
        
        # Register response handler
        response_event = asyncio.Event()
        self._response_handlers[message.id] = response_event
        
        try:
            # Put message in queue for processing
            await self._request_queue.put(message)
            
            # Wait for response
            await asyncio.wait_for(response_event.wait(), timeout=timeout)
            
            result = self._response_data.pop(message.id)
            logger.info(f"Received response for request {message.id}")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Request {message.id} timed out after {timeout}s")
            raise TimeoutError(f"No response within {timeout} seconds")
        finally:
            self._response_handlers.pop(message.id, None)
    
    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Process an incoming A2A message.
        
        Args:
            message: The incoming A2A message
            
        Returns:
            Response message if applicable
        """
        logger.info(
            f"Processing message from {message.sender} to {message.recipient}: "
            f"{message.method} (type: {message.message_type})"
        )
        
        if message.message_type == MessageType.REQUEST:
            return await self._handle_request(message)
        elif message.message_type == MessageType.RESPONSE:
            await self._handle_response(message)
        elif message.message_type == MessageType.ERROR:
            await self._handle_error(message)
        
        return None
    
    async def _handle_request(self, message: A2AMessage) -> A2AMessage:
        """Handle incoming request message."""
        method_handler = self._handlers.get(message.method)
        
        if not method_handler:
            logger.warning(f"No handler for method: {message.method}")
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32601,
                message=f"Method not found: {message.method}",
            ).to_message()
        
        try:
            # Call the handler
            result = await method_handler(message.params) if asyncio.iscoroutinefunction(method_handler) else method_handler(message.params)
            
            response = A2AResponse(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                result=result or {},
            )
            logger.info(f"Successfully handled request {message.id}")
            return response.to_message()
        except Exception as e:
            logger.error(f"Error handling request {message.id}: {str(e)}")
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32603,
                message=f"Internal error: {str(e)}",
            ).to_message()
    
    async def _handle_response(self, message: A2AMessage) -> None:
        """Handle incoming response message."""
        if message.id in self._response_handlers:
            self._response_data[message.id] = message.result or message.error or {}
            self._response_handlers[message.id].set()
    
    async def _handle_error(self, message: A2AMessage) -> None:
        """Handle incoming error message."""
        if message.id in self._response_handlers:
            error_info = message.error or {"code": -1, "message": "Unknown error"}
            self._response_data[message.id] = error_info
            self._response_handlers[message.id].set()
    
    def discover_agents(self, capability: Optional[str] = None) -> List[AgentInfo]:
        """Discover available agents, optionally filtered by capability."""
        if capability:
            return self.registry.find_agents_by_capability(capability)
        return self.registry.list_all_agents()
