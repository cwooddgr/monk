"""Project state management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .render import render_project
from .rpp import ReaperProject


@dataclass
class Message:
    """A message in the conversation history."""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class MonkProject:
    """Manages a Monk music project."""

    path: Path
    rpp: ReaperProject
    conversation: list[Message] = field(default_factory=list)

    @classmethod
    def load(cls, rpp_path: Path) -> "MonkProject":
        """Load a project from an RPP file path."""
        rpp_path = Path(rpp_path).resolve()
        project_dir = rpp_path.parent

        rpp = ReaperProject.load(rpp_path)

        project = cls(path=project_dir, rpp=rpp)

        # Load conversation history if exists
        history_path = project_dir / ".monk_history.json"
        if history_path.exists():
            with open(history_path) as f:
                data = json.load(f)
                project.conversation = [
                    Message(role=m["role"], content=m["content"])
                    for m in data.get("messages", [])
                ]

        return project

    def save(self) -> None:
        """Save the project state."""
        self.rpp.save()
        self._save_history()

    def _save_history(self) -> None:
        """Save conversation history."""
        history_path = self.path / ".monk_history.json"
        data = {
            "messages": [
                {"role": m.role, "content": m.content} for m in self.conversation
            ]
        }
        with open(history_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation.append(Message(role=role, content=content))
        self._save_history()

    @property
    def midi_dir(self) -> Path:
        """Path to the MIDI files directory."""
        midi_dir = self.path / "midi"
        midi_dir.mkdir(exist_ok=True)
        return midi_dir

    @property
    def renders_dir(self) -> Path:
        """Path to the renders directory."""
        renders_dir = self.path / "renders"
        renders_dir.mkdir(exist_ok=True)
        return renders_dir

    def render_preview(self, timeout: int = 60) -> Path:
        """Render the project and return the audio path."""
        if not self.rpp.path:
            raise ValueError("Project has no path")
        return render_project(self.rpp.path, timeout=timeout)

    def get_context(self) -> str:
        """Get project context for the LLM."""
        return self.rpp.get_context_string()

    def get_messages_for_api(self) -> list[dict]:
        """Get conversation history formatted for the API."""
        return [{"role": m.role, "content": m.content} for m in self.conversation]
