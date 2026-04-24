"""
A2A Task model — the central unit of work in the A2A protocol.

A Task tracks the full lifecycle of an agent interaction:
  submitted → working → completed
                      ↘ failed
                      ↘ input-required → working (clarification loop)
           → cancelled  (from any non-terminal state)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid


# ---------------------------------------------------------------------------
# TaskState
# ---------------------------------------------------------------------------

class TaskState(str, Enum):
    """A2A Task lifecycle states."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """True for states from which no further transitions occur."""
        return self in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)


_TERMINAL_STATES = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}


# ---------------------------------------------------------------------------
# Parts — typed content units inside a Message or Artifact
# ---------------------------------------------------------------------------

@dataclass
class TextPart:
    """Plain-text content."""

    text: str
    type: str = field(default="text", init=False)

    def to_dict(self) -> dict:
        return {"type": self.type, "text": self.text}


@dataclass
class DataPart:
    """Structured JSON content."""

    data: Dict[str, Any] = field(default_factory=dict)
    type: str = field(default="data", init=False)

    def to_dict(self) -> dict:
        return {"type": self.type, "data": self.data}


@dataclass
class FilePart:
    """File reference (URI) or inline content."""

    mime_type: str = "application/octet-stream"
    uri: Optional[str] = None
    type: str = field(default="file", init=False)

    def to_dict(self) -> dict:
        d: dict = {"type": self.type, "mimeType": self.mime_type}
        if self.uri is not None:
            d["uri"] = self.uri
        return d


Part = Union[TextPart, DataPart, FilePart]


def _part_from_dict(d: dict) -> Part:
    """Deserialize a Part from a dict based on its 'type' discriminator."""
    t = d.get("type", "text")
    if t == "data":
        return DataPart(data=d.get("data", {}))
    if t == "file":
        return FilePart(
            mime_type=d.get("mimeType", "application/octet-stream"),
            uri=d.get("uri"),
        )
    return TextPart(text=d.get("text", ""))


# ---------------------------------------------------------------------------
# TaskMessage — one turn in the conversation thread
# ---------------------------------------------------------------------------

@dataclass
class TaskMessage:
    """A single message in the task conversation."""

    role: str  # "user" | "agent"
    parts: List[Part] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"role": self.role, "parts": [p.to_dict() for p in self.parts]}

    @classmethod
    def from_dict(cls, d: dict) -> "TaskMessage":
        return cls(
            role=d.get("role", "user"),
            parts=[_part_from_dict(p) for p in d.get("parts", [])],
        )

    @classmethod
    def user_text(cls, text: str) -> "TaskMessage":
        return cls(role="user", parts=[TextPart(text=text)])

    @classmethod
    def agent_text(cls, text: str) -> "TaskMessage":
        return cls(role="agent", parts=[TextPart(text=text)])

    @classmethod
    def agent_data(cls, data: dict) -> "TaskMessage":
        return cls(role="agent", parts=[DataPart(data=data)])


# ---------------------------------------------------------------------------
# Artifact — an output produced by the agent
# ---------------------------------------------------------------------------

@dataclass
class Artifact:
    """An output produced by an agent for a task."""

    name: str
    parts: List[Part] = field(default_factory=list)
    description: str = ""
    index: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "index": self.index,
            "parts": [p.to_dict() for p in self.parts],
        }


# ---------------------------------------------------------------------------
# TaskStatus — current state snapshot
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


@dataclass
class TaskStatus:
    """Current state of a task, with an optional agent status message."""

    state: TaskState
    message: Optional[TaskMessage] = None
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        d: dict = {"state": self.state.value, "timestamp": self.timestamp}
        if self.message is not None:
            d["message"] = self.message.to_dict()
        return d


# ---------------------------------------------------------------------------
# Task — the central unit of work
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """
    A2A Task — a unit of work with a managed lifecycle.

    Created by tasks/send. Lives until it reaches a terminal state
    (completed, failed, or cancelled).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    status: TaskStatus = field(
        default_factory=lambda: TaskStatus(state=TaskState.SUBMITTED)
    )
    messages: List[TaskMessage] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {
            "id": self.id,
            "status": self.status.to_dict(),
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
        }
        if self.session_id is not None:
            d["sessionId"] = self.session_id
        if self.metadata:
            d["metadata"] = self.metadata
        return d


# ---------------------------------------------------------------------------
# TaskManager — in-memory task store
# ---------------------------------------------------------------------------

class TaskManager:
    """In-memory store for task lifecycle management."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}

    def create(
        self,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create and store a new task in SUBMITTED state."""
        task = Task(
            id=task_id or str(uuid.uuid4()),
            session_id=session_id,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID, or None if not found."""
        return self._tasks.get(task_id)

    def update_state(
        self,
        task_id: str,
        state: TaskState,
        message: Optional[TaskMessage] = None,
    ) -> Optional[Task]:
        """Transition a task to a new state with an optional status message."""
        task = self._tasks.get(task_id)
        if task is not None:
            task.status = TaskStatus(state=state, message=message)
        return task

    def add_message(self, task_id: str, message: TaskMessage) -> None:
        """Append a message to the task's conversation history."""
        task = self._tasks.get(task_id)
        if task is not None:
            task.messages.append(message)

    def add_artifact(self, task_id: str, artifact: Artifact) -> None:
        """Add an output artifact to the task."""
        task = self._tasks.get(task_id)
        if task is not None:
            task.artifacts.append(artifact)

    def cancel(self, task_id: str) -> Optional[Task]:
        """Cancel a task. No-op if the task is already in a terminal state."""
        task = self._tasks.get(task_id)
        if task is not None and task.status.state not in _TERMINAL_STATES:
            task.status = TaskStatus(state=TaskState.CANCELLED)
        return task

    def list_all(self) -> List[Task]:
        """Return all stored tasks."""
        return list(self._tasks.values())
