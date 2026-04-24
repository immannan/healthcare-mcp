"""
A2A Protocol - Agent-to-Agent Communication Protocol.

Implements a protocol for agents to discover each other, communicate,
and delegate tasks asynchronously using JSON-RPC 2.0 format.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import asyncio
import inspect
import logging
from datetime import datetime, timezone

from .message import A2AMessage, A2ARequest, A2AResponse, A2AError, MessageType
from .task import Artifact, DataPart, Task, TaskManager, TaskMessage, TaskState

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """
    A2A Skill — the public-facing descriptor of one capability an agent advertises.

    This is what gets published in the Agent Card so other agents (or clients)
    can discover what an agent can do WITHOUT knowing its internal routing.

    Spec fields:
        id           : unique identifier, used to reference the skill
        name         : human-readable label
        description  : what the skill does
        tags         : topics for filtering during discovery
        examples     : sample natural-language inputs (helps LLMs know when to use it)
        input_modes  : accepted content types (default: text)
        output_modes : returned content types (default: text)
    """

    id: str
    name: str
    description: str
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    input_modes: Optional[List[str]] = None
    output_modes: Optional[List[str]] = None

    def to_dict(self) -> dict:
        """Serialize to A2A spec Skill JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags or [],
            "examples": self.examples or [],
            "inputModes": self.input_modes or ["text"],
            "outputModes": self.output_modes or ["text"],
        }


@dataclass
class AgentCapability:
    """
    Internal capability record — binds a Skill to its JSON-RPC handler method.

    Extends Skill with a 'method' field that the A2A Protocol uses to route
    incoming messages to the right handler. The 'method' is internal and is
    NOT published in the Agent Card.

    Think of it as: Skill (public) + method (private routing key).
    """

    id: str
    name: str
    method: str          # Internal JSON-RPC method name — used for routing only
    description: str
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    input_modes: Optional[List[str]] = None
    output_modes: Optional[List[str]] = None

    def to_skill(self) -> Skill:
        """Return the public Skill view of this capability (strips routing method)."""
        return Skill(
            id=self.id,
            name=self.name,
            description=self.description,
            tags=self.tags,
            examples=self.examples,
            input_modes=self.input_modes,
            output_modes=self.output_modes,
        )


@dataclass
class AgentCard:
    """
    A2A Agent Card — the discovery document published at /.well-known/agent.json.

    Any A2A client fetches this URL to learn what an agent can do before sending
    a message. It contains the agent's identity, endpoint URL, protocol
    capability flags (streaming, push notifications), and its list of Skills.

    Spec reference: https://google.github.io/A2A/#/documentation?id=agent-card
    """

    name: str
    description: str
    url: str                        # Where to POST A2A messages to this agent
    version: str
    skills: List[Skill]
    streaming: bool = False         # True if agent supports SSE streaming responses
    push_notifications: bool = False  # True if agent can push async notifications

    def to_dict(self) -> dict:
        """Serialize to A2A spec Agent Card JSON."""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": {
                "streaming": self.streaming,
                "pushNotifications": self.push_notifications,
            },
            "defaultInputModes": ["text"],
            "defaultOutputModes": ["text"],
            "skills": [skill.to_dict() for skill in self.skills],
        }


@dataclass
class AgentInfo:
    """Internal agent registration record — stored in the AgentRegistry."""

    agent_id: str
    agent_name: str
    description: str
    capabilities: List[AgentCapability]
    version: str = "1.0.0"
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def to_agent_card(self, base_url: str) -> AgentCard:
        """
        Build the A2A-compliant Agent Card for this agent.

        Args:
            base_url: Server base URL, e.g. 'http://127.0.0.1:8001'

        Returns:
            AgentCard ready to be serialized and served at /.well-known/agent.json
        """
        return AgentCard(
            name=self.agent_name,
            description=self.description,
            url=f"{base_url}/agents/{self.agent_id}",
            version=self.version,
            skills=[cap.to_skill() for cap in self.capabilities],
        )


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
                    if tags is None or any(tag in (cap.tags or []) for tag in tags):
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
        self.tasks = TaskManager()
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
        # Task lifecycle methods are intercepted before general handler dispatch.
        if message.method == "tasks/send":
            return await self._handle_tasks_send(message)
        if message.method == "tasks/get":
            return await self._handle_tasks_get(message)
        if message.method == "tasks/cancel":
            return await self._handle_tasks_cancel(message)

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
            result = await method_handler(message.params) if inspect.iscoroutinefunction(method_handler) else method_handler(message.params)
            
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
    
    # ------------------------------------------------------------------
    # Task lifecycle handlers
    # ------------------------------------------------------------------

    _TASK_PARAM_KEYS = frozenset({"id", "sessionId", "message", "skill", "metadata"})

    async def _handle_tasks_send(self, message: A2AMessage) -> A2AMessage:
        """
        Handle tasks/send — create a task, call the skill handler, attach results.

        params:
          id        (optional) — client-supplied task ID; auto-generated if omitted
          sessionId (optional) — groups related tasks into a session
          skill     (required) — the registered handler key to invoke
          message   (optional) — TaskMessage dict with role + parts
          <extra>   (optional) — any additional key/value pairs forwarded to the handler
        """
        params = message.params
        task_id = params.get("id")
        skill = params.get("skill")
        user_msg_data = params.get("message")

        # Retrieve existing task (multi-turn) or create a new one.
        task = self.tasks.get(task_id) if task_id else None
        if task is None:
            task = self.tasks.create(
                task_id=task_id,
                session_id=params.get("sessionId"),
                metadata=params.get("metadata"),
            )

        if user_msg_data:
            self.tasks.add_message(task.id, TaskMessage.from_dict(user_msg_data))

        self.tasks.update_state(task.id, TaskState.WORKING)

        handler = self._handlers.get(skill) if skill else None
        if handler is None:
            self.tasks.update_state(
                task.id, TaskState.FAILED,
                TaskMessage.agent_text(f"No handler registered for skill: {skill!r}"),
            )
            logger.warning(f"tasks/send: unknown skill {skill!r}")
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32601,
                message=f"No handler registered for skill: {skill!r}",
            ).to_message()

        try:
            # Build handler params: extra top-level keys + DataPart.data from message.
            handler_params: Dict[str, Any] = {
                k: v for k, v in params.items() if k not in self._TASK_PARAM_KEYS
            }
            if user_msg_data:
                for part in user_msg_data.get("parts", []):
                    if part.get("type") == "data":
                        handler_params.update(part.get("data", {}))
                        break

            result = (
                await handler(handler_params)
                if inspect.iscoroutinefunction(handler)
                else handler(handler_params)
            )
            result = result or {}

            self.tasks.add_artifact(
                task.id,
                Artifact(
                    name=f"{skill}_result",
                    parts=[DataPart(data=result)],
                    index=len(task.artifacts),
                ),
            )
            self.tasks.add_message(task.id, TaskMessage.agent_data(result))
            self.tasks.update_state(task.id, TaskState.COMPLETED)

            logger.info(f"tasks/send completed task {task.id} via skill {skill!r}")
            return A2AResponse(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                result=task.to_dict(),
            ).to_message()

        except Exception as e:
            logger.error(f"tasks/send error in skill {skill!r}: {e}")
            self.tasks.update_state(
                task.id, TaskState.FAILED,
                TaskMessage.agent_text(str(e)),
            )
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32603,
                message=f"Internal error: {e}",
            ).to_message()

    async def _handle_tasks_get(self, message: A2AMessage) -> A2AMessage:
        """Handle tasks/get — return current task state by ID."""
        task_id = message.params.get("id")
        if not task_id:
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32602,
                message="params.id is required for tasks/get",
            ).to_message()

        task = self.tasks.get(task_id)
        if task is None:
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32001,
                message=f"Task not found: {task_id}",
            ).to_message()

        return A2AResponse(
            sender=message.recipient,
            recipient=message.sender,
            request_id=message.id,
            result=task.to_dict(),
        ).to_message()

    async def _handle_tasks_cancel(self, message: A2AMessage) -> A2AMessage:
        """Handle tasks/cancel — move a task to CANCELLED state."""
        task_id = message.params.get("id")
        if not task_id:
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32602,
                message="params.id is required for tasks/cancel",
            ).to_message()

        task = self.tasks.get(task_id)
        if task is None:
            return A2AError(
                sender=message.recipient,
                recipient=message.sender,
                request_id=message.id,
                code=-32001,
                message=f"Task not found: {task_id}",
            ).to_message()

        self.tasks.cancel(task_id)
        logger.info(f"Cancelled task {task_id}")
        return A2AResponse(
            sender=message.recipient,
            recipient=message.sender,
            request_id=message.id,
            result=task.to_dict(),
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
