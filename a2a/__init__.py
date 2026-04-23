"""
A2A (Agent-to-Agent) Protocol Module.

This module provides a protocol for agents to discover each other,
communicate asynchronously, and coordinate tasks using JSON-RPC 2.0 messages.
"""

from .message import A2AMessage, A2ARequest, A2AResponse, A2AError, MessageType
from .a2a_protocol import A2AProtocol, AgentRegistry, AgentInfo, AgentCapability
from .agents import (
    HealthcareAgentBase,
    MemberAssistAgent,
    ClaimsAgent,
    ProviderAdvocateAgent,
    BenefitsAgent,
)

__all__ = [
    # Messages
    "A2AMessage",
    "A2ARequest",
    "A2AResponse",
    "A2AError",
    "MessageType",
    # Protocol
    "A2AProtocol",
    "AgentRegistry",
    "AgentInfo",
    "AgentCapability",
    # Agents
    "HealthcareAgentBase",
    "MemberAssistAgent",
    "ClaimsAgent",
    "ProviderAdvocateAgent",
    "BenefitsAgent",
]
