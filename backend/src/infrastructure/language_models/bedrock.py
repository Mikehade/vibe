"""Bedrock model — async aioboto3, Converse API with tool calling."""

import json
from typing import Any, AsyncGenerator

import aioboto3

from src.core.domain.interfaces import ILanguageModel
from src.infrastructure.language_models.base import BaseLLMModel
from utils.logger import get_logger

logger = get_logger(__name__)


class BedrockModel(BaseLLMModel, ILanguageModel):
    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-6",
        region: str = "us-east-1",
        max_tool_iterations: int = 11,
    ):
        self._model_id = model_id
        self._region = region
        self._max_tool_iterations = max_tool_iterations
        self._session = aioboto3.Session()

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: list[dict] | None = None,
        **kwargs,
    ) -> dict:
        """Invoke Bedrock Converse API. Handles tool calling loop."""
        async with self._session.client(
            "bedrock-runtime", region_name=self._region
        ) as client:
            params: dict[str, Any] = {
                "modelId": self._model_id,
                "messages": messages,
                "inferenceConfig": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "maxTokens": kwargs.get("max_tokens", 4096),
                },
            }

            if system:
                params["system"] = system

            if tools:
                params["toolConfig"] = {"tools": tools}

            logger.debug("Invoking Bedrock model=%s", self._model_id)
            response = await client.converse(**params)

            # Handle tool calls if present
            iterations = 0
            while (
                response.get("stopReason") == "tool_use"
                and iterations < self._max_tool_iterations
            ):
                iterations += 1
                tool_results = await self._handle_tool_calls(response, kwargs.get("tool_handler"))
                if not tool_results:
                    break

                # Add assistant message and tool results to conversation
                messages = list(messages)
                messages.append(response["output"]["message"])
                messages.append({"role": "user", "content": tool_results})

                params["messages"] = messages
                response = await client.converse(**params)

            return response

    async def prompt(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response via Bedrock ConverseStream API."""
        async with self._session.client(
            "bedrock-runtime", region_name=self._region
        ) as client:
            params: dict[str, Any] = {
                "modelId": self._model_id,
                "messages": messages,
                "inferenceConfig": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "maxTokens": kwargs.get("max_tokens", 4096),
                },
            }

            if kwargs.get("system"):
                params["system"] = kwargs["system"]

            response = await client.converse_stream(**params)

            async for event in response.get("stream", []):
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        yield delta["text"]

    async def _handle_tool_calls(self, response: dict, tool_handler=None) -> list[dict]:
        """Extract tool calls from response and return tool results."""
        content = response.get("output", {}).get("message", {}).get("content", [])
        results = []

        for block in content:
            if "toolUse" in block:
                tool_use = block["toolUse"]
                tool_name = tool_use["name"]
                tool_input = tool_use["input"]

                logger.debug("Tool call: %s(%s)", tool_name, json.dumps(tool_input)[:200])

                try:
                    if tool_handler:
                        result = await tool_handler(tool_name, tool_input)
                    else:
                        result = {"error": "No tool handler configured"}

                    results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"json": result if isinstance(result, dict) else {"result": str(result)}}],
                        }
                    })
                except Exception as e:
                    logger.error("Tool execution failed: %s — %s", tool_name, e)
                    results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"json": {"error": str(e)}}],
                            "status": "error",
                        }
                    })

        return results
