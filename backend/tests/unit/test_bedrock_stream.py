"""BedrockModel.stream_turn parses ConverseStream events (text deltas + tool use) correctly."""

from src.infrastructure.language_models.bedrock import BedrockModel


class _Stream:
    def __init__(self, events):
        self._events = events

    def __aiter__(self):
        async def gen():
            for e in self._events:
                yield e

        return gen()


class _Client:
    def __init__(self, events):
        self.events = events
        self.params = None

    async def converse_stream(self, **params):
        self.params = params
        return {"stream": _Stream(self.events)}


async def test_stream_turn_text_and_tool_use():
    events = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "TRAJECTORY {\"energy_trajectory\": \"x\"}\n"}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "Let me check."}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"contentBlockStart": {"contentBlockIndex": 1, "start": {"toolUse": {"toolUseId": "tu1", "name": "search_titles"}}}},
        {"contentBlockDelta": {"contentBlockIndex": 1, "delta": {"toolUse": {"input": "{\"query\": \"Padd"}}}},
        {"contentBlockDelta": {"contentBlockIndex": 1, "delta": {"toolUse": {"input": "ington\"}"}}}},
        {"contentBlockStop": {"contentBlockIndex": 1}},
        {"messageStop": {"stopReason": "tool_use"}},
        {"metadata": {"usage": {}}},
    ]
    model = BedrockModel(model_id="m")
    model._client = _Client(events)
    out = [e async for e in model.stream_turn([{"role": "user", "content": [{"text": "hi"}]}], [{"text": "sys"}], [{"toolSpec": {}}])]
    texts = "".join(e["text"] for e in out if e["type"] == "text")
    assert texts.startswith("TRAJECTORY")
    tool = next(e for e in out if e["type"] == "tool_use")
    assert tool == {"type": "tool_use", "id": "tu1", "name": "search_titles", "input": {"query": "Paddington"}}
    stop = out[-1]
    assert stop["type"] == "stop" and stop["reason"] == "tool_use"
    assert stop["message"]["content"][0]["text"].endswith("Let me check.")
    assert stop["message"]["content"][1] == {"toolUse": {"toolUseId": "tu1", "name": "search_titles", "input": {"query": "Paddington"}}}
    assert model._client.params["toolConfig"] == {"tools": [{"toolSpec": {}}]}


async def test_model_id_override_for_fast_calls():
    model = BedrockModel(model_id="main", fast_model_id="fast")
    params = model._params([], None, None, model_id="fast")
    assert params["modelId"] == "fast"
    assert model._params([], None, None)["modelId"] == "main"
