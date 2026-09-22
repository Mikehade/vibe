"""Unit tests for the tool system — spec generation and registry."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.tools.base import BaseTool, ToolRegistry
from src.core.tools.content_tools import ContentTools
from src.core.tools.availability_tools import AvailabilityTools


class TestToolSpecGeneration:
    def test_content_tools_specs(self):
        mock_tmdb = MagicMock()
        tools = ContentTools(tmdb_client=mock_tmdb)
        specs = tools.get_tool_specs()

        assert len(specs) > 0
        # Each spec should have the Bedrock toolSpec shape
        for spec in specs:
            assert "toolSpec" in spec
            assert "name" in spec["toolSpec"]
            assert "description" in spec["toolSpec"]
            assert "inputSchema" in spec["toolSpec"]

    def test_tool_names_are_unique(self):
        mock_tmdb = MagicMock()
        mock_jw = MagicMock()
        content = ContentTools(tmdb_client=mock_tmdb)
        avail = AvailabilityTools(justwatch_client=mock_jw)

        all_specs = content.get_tool_specs() + avail.get_tool_specs()
        names = [s["toolSpec"]["name"] for s in all_specs]
        assert len(names) == len(set(names)), "Duplicate tool names found"


class TestToolRegistry:
    def test_get_all_specs(self):
        mock_tmdb = MagicMock()
        mock_jw = MagicMock()
        content = ContentTools(tmdb_client=mock_tmdb)
        avail = AvailabilityTools(justwatch_client=mock_jw)
        registry = ToolRegistry(tools=[content, avail])

        specs = registry.get_all_specs()
        assert len(specs) > 0

    @pytest.mark.asyncio
    async def test_execute_routes_to_search(self):
        mock_tmdb = AsyncMock()
        mock_tmdb.search = AsyncMock(return_value={"results": []})
        content = ContentTools(tmdb_client=mock_tmdb)
        registry = ToolRegistry(tools=[content])

        result = await registry.execute("content_search_tmdb", {"query": "test"})
        assert result is not None
        mock_tmdb.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_routes_to_details(self):
        mock_tmdb = AsyncMock()
        mock_tmdb.get_details = AsyncMock(return_value={"id": 550, "title": "Fight Club"})
        content = ContentTools(tmdb_client=mock_tmdb)
        registry = ToolRegistry(tools=[content])

        result = await registry.execute("content_get_title_details", {"tmdb_id": 550})
        assert result is not None
        mock_tmdb.get_details.assert_called_once_with(550)
