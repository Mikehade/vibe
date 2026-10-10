# Product feedback — draft

Required for every tool, API or SDK used. This draft records what we used each one for and what we
observed while building; **edit it so it reflects your own experience** before submitting.

## Vega SDK / Vega OS WebView (`@amazon-devices/webview`)
- **Used for:** the Fire TV app — a React Native for Vega shell hosting the Vibe web UI; Vega Virtual Device for testing.
- **Worked well:** reusing one web codebase on the TV; `hasTVPreferredFocus` and the black background tip to avoid a white flash.
- **Needs work:** the web-app guides don't say how the Back key reaches the page (key event vs. `BackHandler`) or whether
  `onMessage`/`postMessage` are supported; the hello-world guide covers only the Vega Studio GUI, and older CLI docs still
  say `kepler`. Some versioned doc URLs 404 (e.g. `/docs/vega/0.23/set-up-webview`) while the 0.21 version exists.
- **Onboarding:** <your experience installing the SDK on Apple silicon, Rosetta, simulator start-up time>
- **Would build again:** <yes/no + why>

## Alexa+ (MCP)
- **Used for:** a self-hosted MCP server (spec 2025-11-25, Streamable HTTP) so an assistant can plan the night and push it to the TV.
- **Worked well:** building on the open MCP standard meant the same server works with any MCP client (Inspector, Claude, Alexa+).
- **Needs work:** the MCP Toolkit is US-only; from Nigeria we couldn't test with Alexa+ itself and demoed through MCP clients.
  <add anything about the web simulator if you could access it>
- **Would build again:** <…>

## Amazon Bedrock
- **Used for:** the planner (Claude Sonnet via ConverseStream with tool use) and short tasks (Claude Haiku via Converse).
- **Worked well:** ConverseStream with tool use let us stream picks to the TV line by line while the model still works;
  cross-region inference profiles (`us.` model ids) worked out of the box.
- **Needs work:** <e.g. model access per region, tool-use streaming event docs, latency observations>
- **Would build again:** <…>

## AWS App Runner, RDS, CloudFront, S3, Secrets Manager, ECR
- **Used for:** hosting (App Runner), database (RDS PostgreSQL), web delivery + single-domain routing of `/api` and `/mcp`
  (CloudFront + S3), secrets injection, container registry — one CloudFormation template.
- **Worked well:** App Runner secrets from Secrets Manager; CloudFront streaming NDJSON with caching disabled.
- **Needs work:** App Runner has no WebSocket support (we used streaming HTTP + polling); connecting App Runner to a private
  RDS needs a VPC connector *and* NAT for outbound calls, so we used a TLS-only public endpoint with a generated password.
  <your deployment experience>
- **Would build again:** <…>

## TMDB API (third-party)
- **Used for:** discovery, metadata, artwork, watch providers by region.
