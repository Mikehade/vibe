"""MCP smoke test — acts as a voice assistant talking to Vibe's MCP server."""

import asyncio
import sys
import uuid

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
API = MCP_URL.rsplit("/mcp", 1)[0] + "/api/v1"
TV = {"X-Device-ID": f"smoke-tv-{uuid.uuid4().hex[:8]}"}


async def main():
    async with httpx.AsyncClient(timeout=30) as http:
        await http.patch(f"{API}/profile/onboarding", headers=TV, json={"name": "Smoke test"})
        code = (await http.post(f"{API}/tv/pair-code?tz_offset_minutes=60", headers=TV)).json()["code"]
        print(f"TV pair code: {code}")
        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as s:
                init = await s.initialize()
                print(f"✓ initialize — protocol {init.protocolVersion}, server '{init.serverInfo.name}'")
                tools = await s.list_tools()
                print("✓ tools:", ", ".join(t.name for t in tools.tools))
                print("→", (await s.call_tool("link_tv", {"code": code})).content[0].text)
                print("→ planning (streams progress)…")
                res = await s.call_tool("plan_movie_night", {"request": "something funny, nothing scary", "minutes": 120})
                print(res.content[0].text)
                print("→", (await s.call_tool("whats_next", {})).content[0].text)
        inbox = (await http.get(f"{API}/tv/inbox", headers=TV)).json()
        print("✓ TV inbox received:", [e["type"] for e in inbox["events"]])


asyncio.run(main())
