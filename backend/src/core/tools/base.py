"""BaseTool ABC with introspection-based Bedrock toolSpec generation and ToolRegistry."""

import inspect
from abc import ABC, abstractmethod
from typing import Any, get_type_hints

from utils.logger import get_logger

logger = get_logger(__name__)


class BaseTool(ABC):
    """Abstract base class for tools that can be called by Bedrock.

    Subclasses define methods prefixed with '_' that become available tools.
    Method signatures are introspected to auto-generate Bedrock toolSpec configs.
    """

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Human-readable tool group name."""
        ...

    def get_tool_specs(self) -> list[dict]:
        """Generate Bedrock toolSpec definitions from method signatures."""
        specs = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("_") and not name.startswith("__"):
                spec = self._method_to_spec(name, method)
                if spec:
                    specs.append(spec)
        return specs

    def _method_to_spec(self, name: str, method) -> dict | None:
        """Convert a method signature to a Bedrock toolSpec."""
        tool_name = f"{self.tool_name}_{name.lstrip('_')}"
        sig = inspect.signature(method)
        hints = get_type_hints(method)
        doc = inspect.getdoc(method) or f"Tool: {tool_name}"

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_type = hints.get(param_name, str)
            json_type = self._python_type_to_json(param_type)
            properties[param_name] = {"type": json_type}

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "toolSpec": {
                "name": tool_name,
                "description": doc,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    }
                },
            }
        }

    @staticmethod
    def _python_type_to_json(python_type) -> str:
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        origin = getattr(python_type, "__origin__", None)
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
        return type_map.get(python_type, "string")

    async def execute(self, tool_name: str, tool_input: dict) -> Any:
        """Execute a tool method by its full name."""
        # Strip the tool group prefix to get the method name
        method_name = "_" + tool_name.replace(f"{self.tool_name}_", "")
        method = getattr(self, method_name, None)
        if method is None:
            raise ValueError(f"Unknown tool method: {tool_name}")

        logger.debug("Executing tool %s with input %s", tool_name, tool_input)

        if inspect.iscoroutinefunction(method):
            return await method(**tool_input)
        return method(**tool_input)


class ToolRegistry:
    """Registry that holds all tools and routes Bedrock tool calls."""

    def __init__(self, tools: list[BaseTool]):
        self._tools: dict[str, BaseTool] = {}
        for tool in tools:
            for spec in tool.get_tool_specs():
                name = spec["toolSpec"]["name"]
                self._tools[name] = tool

    def get_all_specs(self) -> list[dict]:
        """Get all tool specs for Bedrock."""
        specs = []
        seen = set()
        for tool in set(self._tools.values()):
            for spec in tool.get_tool_specs():
                name = spec["toolSpec"]["name"]
                if name not in seen:
                    specs.append(spec)
                    seen.add(name)
        return specs

    async def execute(self, tool_name: str, tool_input: dict) -> Any:
        """Route a tool call to the correct tool."""
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await tool.execute(tool_name, tool_input)

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())
