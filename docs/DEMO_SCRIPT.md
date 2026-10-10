# Demo video script (target 2:45)

Judges may stop at 3:00 — the strongest moments come first. Record the **Vega Virtual Device** window
(the rules require the Fire TV/Vega simulator or a device). Use real Bedrock for the recording.

| Time | Screen | Say (roughly) |
|---|---|---|
| 0:00 | Vega simulator, Vibe home | "It's Sunday night. I'm tired and I've got two hours. Instead of scrolling for forty minutes, I tell my TV how I feel." |
| 0:12 | Select **Tired** → **Two hours** | "Vibe already started building a shortlist the moment I picked a mood." |
| 0:18 | Plan streaming: status lines, tool call, picks landing | "Everything streams: it's checking what's on *my* services, calling tools, and each pick lands the moment Claude on Amazon Bedrock decides it." |
| 0:40 | Finished lineup, energy arc, done-by time | "An opener, a main event, a nightcap — shaped to wind me down, done by 11:20. Every reason is specific to the title and its place in the night." |
| 0:55 | **Not this one** on the main event | "Not feeling it? One press, a new pick for that slot." |
| 1:05 | Couch Mode: QR, two phones join | "Watching with others? Everyone scans, adds their mood and hard no's." |
| 1:25 | Build our night → phones vote skip → TV swaps | "Vibe blends the room, and a majority vote swaps a pick live." |
| 1:45 | MCP Inspector / Alexa+ next to TV | "And by voice: through our Alexa+ MCP server, 'plan a chill night' builds the lineup live on the TV." |
| 2:10 | Start watching → I've finished → *Wind me down* | "After each title it checks in, and re-plans the rest around how I feel now." |
| 2:30 | Architecture slide | "Vega OS WebView app, FastAPI on App Runner, Bedrock with streaming tool use, RDS, CloudFront, and an MCP server — all open source." |
| 2:45 | Home screen | "Vibe. Your evening, programmed." |

**Recording tips**
- Warm the system first (one plan) so the recorded run is fast.
- Rights: the rules ask you not to include third-party copyrighted footage/music. Don't play trailers or
  music. Posters and service names are third-party artwork and trademarks; if you'd rather avoid them,
  record with `FAKE_SERVICES=true` (generated artwork) for the UI walkthrough and show one real-data plan briefly —
  and say which is which.
- Keep the remote on-screen or narrate the button presses so it's clear it's D-pad driven.
