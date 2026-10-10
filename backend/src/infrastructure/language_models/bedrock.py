"""Bedrock model — async aioboto3, Converse / ConverseStream APIs with tool calling.

One long-lived client is reused across requests (opening a client per call adds
hundreds of milliseconds of TLS + credential resolution).
"""

import asyncio
import json
from typing import Any, AsyncGenerator

import aioboto3
from botocore.config import Config

from src.core.domain.interfaces import ILanguageModel
from src.infrastructure.language_models.base import BaseLLMModel
from utils.logger import get_logger

logger = get_logger(__name__)


class BedrockModel(BaseLLMModel, ILanguageModel):
    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-6",
        region: str = "us-east-1",
        max_tool_iterations: int = 4,
        fast_model_id: str | None = None,
    ):
        self._model_id = model_id
        self._fast_model_id = fast_model_id or model_id
        self._region = region
        self._max_tool_iterations = max_tool_iterations
        self._session = aioboto3.Session()
        self._client = None
        self._client_ctx = None
        self._lock = asyncio.Lock()

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def fast_model_id(self) -> str:
        return self._fast_model_id

    async def _get_client(self):
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is None:
                cfg = Config(read_timeout=60, connect_timeout=5, retries={"max_attempts": 3, "mode": "adaptive"})
                self._client_ctx = self._session.client("bedrock-runtime", region_name=self._region, config=cfg)
                self._client = await self._client_ctx.__aenter__()
        return self._client

    async def close(self):
        if self._client_ctx is not None:
            await self._client_ctx.__aexit__(None, None, None)
            self._client = None
            self._client_ctx = None

    def _params(self, messages, system=None, tools=None, **kwargs) -> dict[str, Any]:
        params: dict[str, Any] = {
            "modelId": kwargs.get("model_id") or self._model_id,
            "messages": messages,
            "inferenceConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxTokens": kwargs.get("max_tokens", 2048),
            },
        }
        if system:
            params["system"] = system
        if tools:
            params["toolConfig"] = {"tools": tools}
        return params

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: list[dict] | None = None,
        **kwargs,
    ) -> dict:
        """Invoke Bedrock Converse API (non-streaming). Handles a bounded tool loop."""
        client = await self._get_client()
        params = self._params(messages, system, tools, **kwargs)
        response = await client.converse(**params)

        iterations = 0
        while response.get("stopReason") == "tool_use" and iterations < self._max_tool_iterations:
            iterations += 1
            tool_results = await self._handle_tool_calls(response, kwargs.get("tool_handler"))
            if not tool_results:
                break
            messages = list(messages)
            messages.append(response["output"]["message"])
            messages.append({"role": "user", "content": tool_results})
            params["messages"] = messages
            response = await client.converse(**params)
        return response

    async def stream_turn(
        self,
        messages: list[dict],
        system: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> AsyncGenerator[dict, None]:
        """Stream one assistant turn via ConverseStream."""
        client = await self._get_client()
        params = self._params(messages, system, tools, **kwargs)
        response = await client.converse_stream(**params)

        blocks: dict[int, dict] = {}
        stop_reason = "end_turn"

        async for event in response["stream"]:
            if "contentBlockStart" in event:
                start = event["contentBlockStart"]
                idx = start.get("contentBlockIndex", 0)
                tool = start.get("start", {}).get("toolUse")
                if tool:
                    blocks[idx] = {"toolUse": {"toolUseId": tool["toolUseId"], "name": tool["name"]}, "_input": ""}
            elif "contentBlockDelta" in event:
                d = event["contentBlockDelta"]
                idx = d.get("contentBlockIndex", 0)
                delta = d.get("delta", {})
                if "text" in delta:
                    blk = blocks.setdefault(idx, {"text": ""})
                    blk["text"] = blk.get("text", "") + delta["text"]
                    yield {"type": "text", "text": delta["text"]}
                elif "toolUse" in delta:
                    blk = blocks.setdefault(idx, {"toolUse": {}, "_input": ""})
                    blk["_input"] = blk.get("_input", "") + delta["toolUse"].get("input", "")
            elif "contentBlockStop" in event:
                idx = event["contentBlockStop"].get("contentBlockIndex", 0)
                blk = blocks.get(idx)
                if blk and "toolUse" in blk:
                    try:
                        blk["toolUse"]["input"] = json.loads(blk.get("_input") or "{}")
                    except json.JSONDecodeError:
                        blk["toolUse"]["input"] = {}
                    yield {
                        "type": "tool_use",
                        "id": blk["toolUse"]["toolUseId"],
                        "name": blk["toolUse"]["name"],
                        "input": blk["toolUse"]["input"],
                    }
            elif "messageStop" in event:
                stop_reason = event["messageStop"].get("stopReason", "end_turn")

        content = []
        for idx in sorted(blocks):
            blk = blocks[idx]
            if "toolUse" in blk:
                content.append({"toolUse": blk["toolUse"]})
            elif blk.get("text"):
                content.append({"text": blk["text"]})
        yield {"type": "stop", "reason": stop_reason, "message": {"role": "assistant", "content": content}}

    async def prompt(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        async for ev in self.stream_turn(messages, kwargs.get("system") or [], None, **kwargs):
            if ev["type"] == "text":
                yield ev["text"]

    async def _handle_tool_calls(self, response: dict, tool_handler=None) -> list[dict]:
        content = response.get("output", {}).get("message", {}).get("content", [])
        results = []
        for block in content:
            if "toolUse" not in block:
                continue
            tool_use = block["toolUse"]
            try:
                result = await tool_handler(tool_use["name"], tool_use["input"]) if tool_handler else {"error": "No tool handler"}
                results.append({
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": result if isinstance(result, dict) else {"result": result}}],
                    }
                })
            except Exception as e:  # noqa: BLE001
                logger.error("Tool execution failed: %s — %s", tool_use["name"], e)
                results.append({
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": {"error": str(e)}}],
                        "status": "error",
                    }
                })
        return results
