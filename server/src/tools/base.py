from __future__ import annotations

from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field


@dataclass
class Tool:
    """Represents a callable tool/function for LLM tool calling."""

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Any | Awaitable[Any]]
    user_friendly_name: str = ""
    enabled: bool = True

    def to_openai_schema(self) -> dict[str, Any]:
        """Converts tool to standard OpenAI / Mistral function tool specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_summary_dict(self) -> dict[str, Any]:
        """Summary dictionary sent to frontend for Settings UI display."""
        return {
            "id": self.name,
            "name": self.user_friendly_name or self.name.replace("_", " ").title(),
            "description": self.description,
            "enabled": self.enabled,
        }
