from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

from .base import Tool
from .builtins import BUILTIN_TOOLS


class ToolRegistry:
    """Manages available tools, schema definitions, and safe execution with timeout."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        for tool in BUILTIN_TOOLS:
            self.register(tool)

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool | None:
        tool = self._tools.get(name)
        if tool is not None:
            return tool
        # Resilient alias mapping for tool discovery
        if name in ("get_tool_list", "tool_list", "tools_list", "list_tools", "get_tools"):
            return self._tools.get("get_available_tools") or self._tools.get("get_tool_list")
        if name in ("get_available_tools", "available_tools"):
            return self._tools.get("get_tool_list") or self._tools.get("get_available_tools")
        return None

    def get_all_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_enabled_tools(self) -> list[Tool]:
        return [t for t in self._tools.values() if t.enabled]

    def get_tool_definitions(self, only_enabled: bool = True) -> list[dict[str, Any]]:
        """Returns standard function definitions for LLM API calls."""
        tools = self.get_enabled_tools() if only_enabled else self.get_all_tools()
        return [t.to_openai_schema() for t in tools]

    def get_tools_summary(self) -> list[dict[str, Any]]:
        """Returns summary list for client Settings UI."""
        summaries = []
        for t in self.get_all_tools():
            # Hide redundant internal alias in Settings screen
            if t.name == "get_tool_list":
                continue
            summaries.append(t.to_summary_dict())
        return summaries

    async def execute_tool(
        self, name: str, arguments: dict[str, Any] | str, timeout: float = 10.0
    ) -> dict[str, Any]:
        """Safely executes a tool by name with timeout and structured error isolation."""
        tool = self.get_tool(name)
        if tool is None:
            return {
                "status": "error",
                "error": f"Tool '{name}' is not recognized or available.",
            }

        if not tool.enabled:
            return {
                "status": "error",
                "error": f"Tool '{name}' is currently disabled.",
            }

        parsed_args: dict[str, Any] = {}
        if isinstance(arguments, str):
            trimmed = arguments.strip()
            if trimmed:
                try:
                    parsed_args = json.loads(trimmed)
                except Exception as err:
                    return {
                        "status": "error",
                        "error": f"Failed to parse arguments JSON: {err}",
                    }
        elif isinstance(arguments, dict):
            parsed_args = arguments

        try:
            if inspect.iscoroutinefunction(tool.func):
                result = await asyncio.wait_for(
                    tool.func(**parsed_args), timeout=timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool.func, **parsed_args), timeout=timeout
                )

            if isinstance(result, (dict, list)):
                return result
            return {"status": "success", "result": result}

        except asyncio.TimeoutError:
            print(f"[ToolRegistry] Tool '{name}' timed out after {timeout}s.")
            return {
                "status": "error",
                "error": f"Tool '{name}' timed out after {timeout} seconds.",
            }
        except Exception as err:
            print(f"[ToolRegistry] Error executing tool '{name}': {err}")
            return {
                "status": "error",
                "error": f"Tool '{name}' failed during execution: {err}",
            }


# Global tool registry instance
tool_registry = ToolRegistry()
