# MCP Production Setup

> Deploy and secure Model Context Protocol servers for AI agent tool integration. Covers server creation, transport selection, OAuth 2.1 auth, schema pinning, and production hardening.

## When to Use

- You need to expose tools (database queries, file access, APIs) to AI agents via a standard protocol
- You're integrating MCP servers into a production agent framework (LlamaIndex, Pydantic AI, LangChain)
- You need to audit, secure, or harden an existing MCP deployment
- You want to build a custom MCP server for internal tooling

## Prerequisites

- Python 3.10+ or Node.js 18+
- `pip install mcp` (Python SDK) or `npm install @modelcontextprotocol/sdk` (JS SDK)
- Understanding of JSON-RPC 2.0 basics

## Quick Start — Python MCP Server

```python
# server.py — Minimal MCP server with tool registration
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("my-tool-server")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_database",
            description="Execute a read-only SQL query against the analytics database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query"}
                },
                "required": ["query"]
            },
            # v1.1 tool annotations
            annotations={
                "readOnly": True,
                "idempotent": True,
                "openWorldHint": False
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "query_database":
        # Validate: only SELECT allowed
        query = arguments["query"].strip().upper()
        if not query.startswith("SELECT"):
            return [TextContent(type="text", text="ERROR: Only SELECT queries allowed")]
        result = execute_query(arguments["query"])
        return [TextContent(type="text", text=str(result))]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Transport Selection

| Transport | Use Case | Latency | Security |
|-----------|----------|---------|----------|
| **stdio** | Local processes, IDE integrations | Lowest (~1ms) | Process isolation only |
| **Streamable HTTP** (v1.1) | Remote servers, production | Medium (~10-50ms) | OAuth 2.1, TLS |
| **HTTP+SSE** (deprecated) | Legacy — migrate away | Medium | Limited |

### Streamable HTTP Server (Production)

```python
from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServer

server = Server("production-tools")
# ... register tools ...

http_server = StreamableHTTPServer(
    server,
    host="0.0.0.0",
    port=8080,
    # OAuth 2.1 config
    auth={
        "issuer": "https://auth.yourcompany.com",
        "audience": "mcp-tools",
        "jwks_uri": "https://auth.yourcompany.com/.well-known/jwks.json"
    }
)
await http_server.serve()
```

## Security Hardening Checklist

### 1. Tool Description Hygiene
- Keep descriptions factual and minimal — no instructions to the LLM
- Never include phrases like "always", "first", "before anything else" in descriptions
- Review descriptions for prompt injection vectors

### 2. Schema Pinning
```python
# Pin tool schemas with content hashing
import hashlib, json

def hash_tool_schema(tool):
    canonical = json.dumps(tool.model_dump(), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()

# Store hashes, alert on changes
EXPECTED_HASHES = {
    "query_database": "a1b2c3...",
}
```

### 3. Input Validation
- Validate ALL tool inputs server-side — never trust the LLM's judgment
- Use allowlists over denylists (allow specific SQL tables, not "block DROP")
- Rate-limit tool calls per session

### 4. Scope Limitation
- One server per domain (database server, file server — not "everything server")
- Read-only tools on separate servers from write tools
- Use tool annotations to declare capabilities honestly

### 5. Audit Logging
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    log.info(f"tool_call: {name}", extra={
        "arguments": arguments,
        "session_id": server.session_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    # ... execute tool ...
```

## Connecting MCP to Agent Frameworks

### Pydantic AI
```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP

agent = Agent(
    "openai:gpt-4o",
    mcp_servers=[
        MCPServerHTTP("https://tools.yourcompany.com:8080", auth_token="...")
    ]
)
```

### LlamaIndex
```python
from llama_index.tools.mcp import MCPToolSpec

mcp_tools = MCPToolSpec(server_url="https://tools.yourcompany.com:8080")
agent = ReActAgent.from_tools(mcp_tools.to_tool_list())
```

## Production Deployment (Docker)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
EXPOSE 8080
HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "server.py"]
```

```yaml
# docker-compose.yml
services:
  mcp-tools:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - MCP_AUTH_ISSUER=https://auth.yourcompany.com
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
```

## Pitfalls

- **Don't expose MCP servers to the public internet without OAuth** — the default is zero auth
- **Don't trust tool descriptions from third-party registries** — audit them for prompt injection
- **Don't mix read and write tools on the same server** — blast radius increases
- **HTTP+SSE transport breaks behind load balancers** — use Streamable HTTP (v1.1)
- **Tool schemas can change silently** — pin and hash schemas, alert on drift
- **MCP adds latency per tool call** — for hot-path tools called 20+ times, consider native integration

## Verification

```bash
# Test server connectivity
mcp ping https://tools.yourcompany.com:8080

# List available tools
mcp tools https://tools.yourcompany.com:8080

# Call a tool
mcp call https://tools.yourcompany.com:8080 query_database '{"query": "SELECT 1"}'
```

---

*Source: EVAL #009 — April 7, 2026*
*Protocol: MCP v1.1 (Streamable HTTP, OAuth 2.1, Tool Annotations)*
