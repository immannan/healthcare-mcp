"""
A2A Protocol Message definitions and serialization.

Implements JSON-RPC 2.0 based message format for Agent-to-Agent communication.
"""

from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import uuid
from datetime import datetime, timezone


class MessageType(str, Enum):
    """A2A Message types."""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    NOTIFICATION = "notification"


@dataclass
class A2AMessage:
    """A2A Protocol Message (JSON-RPC 2.0 compatible)."""
    
    jsonrpc: str = "2.0"
    method: str = ""
    params: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    result: Optional[dict] = None
    error: Optional[dict] = None
    message_type: MessageType = MessageType.REQUEST
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))
    sender: str = ""
    recipient: str = ""
    
    def to_dict(self) -> dict:
        """Convert message to dictionary."""
        msg_dict = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params,
            "id": self.id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.message_type.value,
        }
        if self.result is not None:
            msg_dict["result"] = self.result
        if self.error is not None:
            msg_dict["error"] = self.error
        return msg_dict
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "A2AMessage":
        """Create message from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            params=data.get("params", {}),
            id=data.get("id", str(uuid.uuid4())),
            result=data.get("result"),
            error=data.get("error"),
            message_type=MessageType(data.get("type", "request")),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "A2AMessage":
        """Create message from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class A2ARequest:
    """Helper class for A2A request creation."""
    
    sender: str
    recipient: str
    method: str
    params: dict
    
    def to_message(self) -> A2AMessage:
        """Convert to A2A message."""
        return A2AMessage(
            method=self.method,
            params=self.params,
            message_type=MessageType.REQUEST,
            sender=self.sender,
            recipient=self.recipient,
        )


@dataclass
class A2AResponse:
    """Helper class for A2A response creation."""
    
    sender: str
    recipient: str
    request_id: str
    result: dict
    
    def to_message(self) -> A2AMessage:
        """Convert to A2A message."""
        return A2AMessage(
            method="response",
            result=self.result,
            id=self.request_id,
            message_type=MessageType.RESPONSE,
            sender=self.sender,
            recipient=self.recipient,
        )


@dataclass
class A2AError:
    """Helper class for A2A error response creation."""
    
    sender: str
    recipient: str
    request_id: str
    code: int
    message: str
    data: Optional[dict] = None
    
    def to_message(self) -> A2AMessage:
        """Convert to A2A message."""
        error_obj = {
            "code": self.code,
            "message": self.message,
        }
        if self.data:
            error_obj["data"] = self.data
        
        return A2AMessage(
            method="error",
            error=error_obj,
            id=self.request_id,
            message_type=MessageType.ERROR,
            sender=self.sender,
            recipient=self.recipient,
        )
