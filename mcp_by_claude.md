# Model Context Protocol (MCP): Detailed Notes

> **Note on source:** These notes are a self-contained study guide on MCP, organized the way a hands-on course would teach it (problem → concepts → architecture → building → testing → deployment). They were **not** transcribed from the CampusX videos (video titles/transcripts were not accessible). Use them alongside the playlist and map each section to the matching video.

---

## Table of Contents
1. [What is MCP and why does it exist?](#1-what-is-mcp-and-why-does-it-exist)
2. [The problem MCP solves (N×M integrations)](#2-the-problem-mcp-solves)
3. [Architecture: Host, Client, Server](#3-architecture-host-client-server)
4. [Protocol basics: JSON-RPC 2.0 & lifecycle](#4-protocol-basics)
5. [Server primitives: Tools, Resources, Prompts](#5-server-primitives)
6. [Client features: Sampling, Roots, Elicitation](#6-client-features)
7. [Transports: stdio vs Streamable HTTP](#7-transports)
8. [Prerequisites & setup](#8-prerequisites--setup)
9. [Hands-on: your first MCP server (Python / FastMCP)](#9-hands-on-first-mcp-server)
10. [Testing with MCP Inspector](#10-testing-with-mcp-inspector)
11. [Connecting to Claude Desktop / other hosts](#11-connecting-to-hosts)
12. [Building an MCP client](#12-building-an-mcp-client)
13. [End-to-end example: SQL / database MCP server](#13-end-to-end-example-sql-mcp-server)
14. [Adding resources and prompts](#14-adding-resources-and-prompts)
15. [Remote servers, deployment & auth](#15-remote-servers-deployment--auth)
16. [Security best practices](#16-security-best-practices)
17. [MCP vs Function calling vs REST vs RAG vs Agents](#17-comparisons)
18. [Common pitfalls & debugging](#18-common-pitfalls--debugging)
19. [Cheat sheet & revision questions](#19-cheat-sheet--revision-questions)

---

## 1. What is MCP and why does it exist?

**Model Context Protocol (MCP)** is an **open standard**, introduced by Anthropic in November 2024, that defines how AI applications (LLM-powered apps) connect to **external tools, data sources, and services** in a uniform way.

**Analogy:** MCP is the **USB-C of AI applications**. Before USB-C, every device had its own connector. Before MCP, every AI app needed custom glue code for every tool.

**Key ideas**
- An LLM on its own only knows its training data and can't *do* anything (no file access, no DB, no API calls).
- To be useful, it needs **context** (data) and **capabilities** (actions).
- MCP standardizes how that context/capability is **exposed** (by servers) and **consumed** (by clients).
- It is **open**, **language-agnostic**, and has official SDKs (Python, TypeScript, Java, Kotlin, C#, and others).

---

## 2. The problem MCP solves

### Before MCP: the N×M problem
- N AI apps (Claude, ChatGPT-style apps, Cursor, custom agents…)
- M tools/services (GitHub, Slack, Postgres, Google Drive, Jira…)
- Each pair needed a **custom integration** → **N × M** integrations.

### With MCP: N + M
- Each tool is wrapped **once** as an MCP **server**.
- Each AI app implements MCP **once** as a **client**.
- Any client can talk to any server → **N + M** integrations.

```
Before:                          After:
App1 ──┬── Tool1                 App1 ─┐             ┌─ Server(Tool1)
App1 ──┼── Tool2                 App2 ─┼── MCP ──────┼─ Server(Tool2)
App2 ──┼── Tool1                 App3 ─┘             └─ Server(Tool3)
App2 ──┴── Tool2
(custom code per pair)           (one standard protocol)
```

**Benefits:** reusability, ecosystem growth, vendor/model neutrality, separation of concerns (tool authors vs. app authors), easier maintenance.

---

## 3. Architecture: Host, Client, Server

MCP uses a **client–server architecture** with three roles:

| Role | What it is | Example |
|---|---|---|
| **Host** | The AI application the user interacts with; manages clients, enforces permissions, runs the LLM | Claude Desktop, Cursor, VS Code, a custom chatbot |
| **Client** | A component inside the host that keeps a **1:1 connection** with one MCP server | The connector object the host creates per server |
| **Server** | A lightweight program exposing capabilities (tools/resources/prompts) over MCP | Filesystem server, GitHub server, your SQL server |

```
┌──────────────── HOST (e.g. Claude Desktop) ────────────────┐
│   LLM                                                       │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│   │ Client 1 │  │ Client 2 │  │ Client 3 │                  │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└────────┼─────────────┼─────────────┼────────────────────────┘
         │ MCP         │ MCP         │ MCP
   ┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐
   │ Server A │  │ Server B │  │ Server C │
   │ (files)  │  │ (GitHub) │  │ (SQL DB) │
   └──────────┘  └──────────┘  └──────────┘
```

**Important points**
- One host → **many clients** → each connected to **one server**.
- Servers can be **local** (same machine, via stdio) or **remote** (over HTTP).
- Servers are isolated from each other; the host decides what each can see.
- The **LLM never talks to the server directly**; the host/client mediates (and can ask the user for approval).

### Typical request flow
1. User asks a question in the host.
2. Host sends the question + **list of available tools** (discovered from servers) to the LLM.
3. LLM decides to call a tool (e.g. `query_database`) with arguments.
4. Host/client sends a `tools/call` request to the right server.
5. Server executes and returns the result.
6. Host feeds the result back to the LLM.
7. LLM produces the final answer.

---

## 4. Protocol basics

### 4.1 JSON-RPC 2.0
MCP messages are **JSON-RPC 2.0**. Three message types:
- **Request**: has `id`, `method`, `params`; expects a response.
- **Response**: has the same `id`, and `result` **or** `error`.
- **Notification**: has `method`, **no `id`**; no response expected.

```json
// Request
{ "jsonrpc": "2.0", "id": 1, "method": "tools/call",
  "params": { "name": "add", "arguments": { "a": 2, "b": 3 } } }

// Response
{ "jsonrpc": "2.0", "id": 1,
  "result": { "content": [ { "type": "text", "text": "5" } ] } }

// Notification
{ "jsonrpc": "2.0", "method": "notifications/tools/list_changed" }
```

### 4.2 Connection lifecycle
1. **Initialize**: client sends `initialize` with its protocol version and capabilities; server replies with its own version and capabilities.
2. **Initialized**: client sends `notifications/initialized`.
3. **Operation**: normal requests (list/call tools, read resources, get prompts…).
4. **Shutdown**: connection closed (stdin closed / HTTP session ended).

**Capability negotiation:** during `initialize`, each side declares what it supports (e.g. server says "I support tools and resources, with `listChanged`"). Only negotiated features are used.

### 4.3 Common methods
| Method | Purpose |
|---|---|
| `tools/list`, `tools/call` | Discover and invoke tools |
| `resources/list`, `resources/read`, `resources/templates/list`, `resources/subscribe` | Discover/read data |
| `prompts/list`, `prompts/get` | Discover/fetch prompt templates |
| `sampling/createMessage` | Server asks client's LLM for a completion |
| `roots/list` | Server asks which roots (dirs) it may access |
| `elicitation/create` | Server asks the user for extra input |
| `ping` | Health check |
| `notifications/*` | One-way events (progress, cancelled, list_changed…) |

---

## 5. Server primitives

Servers expose three core primitives. A key mental model is **who controls each one**:

| Primitive | Controlled by | Purpose | Analogy |
|---|---|---|---|
| **Tools** | **Model** (LLM decides to call) | Perform actions / computations / side effects | POST / function call |
| **Resources** | **Application** (host decides what to load) | Provide read-only data/context | GET / file |
| **Prompts** | **User** (user picks, e.g. slash command) | Reusable prompt templates/workflows | Saved template |

### 5.1 Tools
- Functions the LLM can invoke. Each has a **name**, **description**, and **JSON Schema** for inputs (optionally for outputs).
- Descriptions matter a lot: the LLM uses them to decide *when* and *how* to call the tool.
- Can have side effects (send email, write DB row) → host should ask user approval for risky ones.
- Results are returned as **content blocks** (text, image, embedded resource, structured content).
- Errors: protocol errors (JSON-RPC) vs. **tool execution errors** (`isError: true` in result, so the LLM can see and recover).

```json
{
  "name": "get_weather",
  "description": "Get current weather for a city",
  "inputSchema": {
    "type": "object",
    "properties": { "city": { "type": "string" } },
    "required": ["city"]
  }
}
```

### 5.2 Resources
- **Read-only data** identified by a **URI**: `file:///path/doc.txt`, `postgres://db/table`, `config://app`.
- **Direct resources**: fixed URIs. **Resource templates**: parameterized URIs, e.g. `users://{user_id}/profile`.
- Contents are text or binary (base64) with a MIME type.
- Clients can **subscribe** to changes (`notifications/resources/updated`).
- Use for: files, DB schemas, logs, API responses, documentation.

### 5.3 Prompts
- Server-defined **templates** with optional arguments that produce structured messages.
- Surfaced to the user (e.g. as slash commands) for common workflows: "Summarize this table", "Code review", "Explain error".
- Can embed resources inside the messages.

### Tool vs Resource: the rule of thumb
- Needs **computation/side effects/parameters from the LLM** → **Tool**.
- Just **exposing data** for context → **Resource**.

---

## 6. Client features

Features that **clients** offer to servers:

- **Sampling**: the server asks the **client's LLM** to generate a completion (so server authors don't need their own API key/model). The user stays in control and can approve/modify requests. Enables agentic server behavior.
- **Roots**: the client tells the server which filesystem/URI boundaries it may operate within.
- **Elicitation**: the server pauses to ask the **user** for missing info or confirmation via the client (structured form schema).

Also supported in the spec: **progress notifications**, **cancellation**, **logging**, **completion (autocomplete) for arguments**, and **pagination** for lists.

---

## 7. Transports

A transport defines **how bytes move** between client and server. The protocol layer (JSON-RPC) is the same.

### 7.1 stdio (Standard I/O)
- Client **launches the server as a subprocess** and talks over **stdin/stdout**.
- Messages are newline-delimited JSON.
- **Best for local** servers; simple, fast, no networking, no auth needed.
- ⚠️ **Never `print()` to stdout** in a stdio server, since it corrupts the protocol stream. Log to **stderr** (or use the logging facility).

### 7.2 Streamable HTTP
- For **remote** servers. Single HTTP endpoint (e.g. `https://example.com/mcp`).
- Client sends JSON-RPC via **HTTP POST**; server can reply with plain JSON **or** open an **SSE stream** for streaming/server-initiated messages.
- Supports **sessions** (via `Mcp-Session-Id` header), resumability, and multiple concurrent clients.
- Introduced in spec version **2025-03-26**; it **replaces the older HTTP+SSE transport** (two endpoints), which is now deprecated.

### 7.3 Comparison
| | stdio | Streamable HTTP |
|---|---|---|
| Location | Local machine | Local or remote |
| Clients per server | 1 (subprocess) | Many |
| Auth | Environment/OS-level | OAuth 2.1 / headers / tokens |
| Setup | Easiest | Needs a web server & deployment |
| Use case | Dev tools, desktop apps | SaaS integrations, shared team servers |

Custom transports are also allowed as long as they preserve JSON-RPC semantics.

---

## 8. Prerequisites & setup

**Knowledge**
- Python basics (functions, type hints, async/await helps)
- APIs/JSON, basic HTTP
- Basic LLM concepts (prompts, tool/function calling)
- Basic SQL (if doing the DB example)

**Tools**
- Python ≥ 3.10
- **uv** (fast Python package/project manager), recommended by MCP docs
- Node.js (needed for **MCP Inspector** via `npx`, and many community servers)
- An MCP host: Claude Desktop, Cursor, VS Code, etc.
- Code editor (VS Code)

**Setup commands**
```bash
# install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
# powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

uv init my-mcp-server
cd my-mcp-server
uv venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
uv add "mcp[cli]"              # official Python SDK + CLI tools
```

---

## 9. Hands-on: first MCP server

Using the official Python SDK's **FastMCP** API (decorator-based, type hints → JSON Schema automatically).

```python
# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo")          # server name

# ---- TOOL ----
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""      # docstring = tool description
    return a + b

@mcp.tool()
def get_weather(city: str) -> str:
    """Return a (fake) weather report for a city."""
    return f"It is sunny in {city}."

# ---- RESOURCE (template) ----
@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """A personalized greeting."""
    return f"Hello, {name}!"

# ---- PROMPT ----
@mcp.prompt()
def review_code(code: str) -> str:
    """Prompt template for reviewing code."""
    return f"Please review this code and suggest improvements:\n\n{code}"

if __name__ == "__main__":
    mcp.run()                     # default transport: stdio
```

**What FastMCP does for you**
- Function name → tool name; **docstring → description**; **type hints → input schema**.
- Handles JSON-RPC, initialization, capability negotiation.

**Running**
```bash
uv run mcp dev server.py      # launches with MCP Inspector
python server.py              # runs over stdio (waits for a client)
```

**Async tools & Context**
```python
from mcp.server.fastmcp import FastMCP, Context
mcp = FastMCP("Demo")

@mcp.tool()
async def long_task(n: int, ctx: Context) -> str:
    for i in range(n):
        await ctx.info(f"step {i}")
        await ctx.report_progress(i, n)
    return "done"
```

**Choosing transport**
```python
mcp.run()                              # stdio
mcp.run(transport="streamable-http")   # HTTP server (default http://127.0.0.1:8000/mcp)
```

**Tool design tips**
- Write **clear, specific descriptions**: say what it does, when to use it, argument meaning.
- Keep tools **small and focused**; prefer few well-named tools over many vague ones.
- Validate inputs; return helpful error messages.
- Return concise results (don't dump huge payloads into the LLM context).
- Mark destructive tools clearly; consider confirmation/elicitation.

---

## 10. Testing with MCP Inspector

**MCP Inspector** is the official visual debugger/test UI for servers.

```bash
npx @modelcontextprotocol/inspector uv run server.py
# or
uv run mcp dev server.py
```

Opens a web UI (default `http://localhost:6274`) where you can:
- Connect via **stdio** or **Streamable HTTP**
- See server **capabilities** and negotiated info
- **List and call tools** with a generated form, view raw JSON responses
- **Browse resources** and templates, read them
- **List/get prompts** with arguments
- View **request/response history & logs/notifications**

Workflow: build server → test in Inspector → fix → then wire into a real host. This isolates server bugs from LLM/host behavior.

---

## 11. Connecting to hosts

### Claude Desktop (local, stdio)
Edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "demo": {
      "command": "uv",
      "args": ["--directory", "/ABSOLUTE/PATH/to/my-mcp-server", "run", "server.py"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/Documents"]
    }
  }
}
```
- Use **absolute paths**; restart the host after editing.
- Pass secrets with `"env": { "API_KEY": "..." }`.
- Look for the tools/connector indicator in the chat UI to confirm connection.

### Other hosts
- **Claude Code**: `claude mcp add <name> -- <command>` (or `--transport http <url>` for remote).
- **Cursor / VS Code / Windsurf**: each has an `mcp.json`/settings entry with the same command/args pattern.
- Remote servers are added as connectors/URLs in hosts that support them.

---

## 12. Building an MCP client

Understanding clients clarifies what hosts do internally.

```python
# client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command="python", args=["server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()                       # handshake

            tools = await session.list_tools()
            print([t.name for t in tools.tools])

            result = await session.call_tool("add", {"a": 2, "b": 3})
            print(result.content[0].text)                    # "5"

            res = await session.read_resource("greeting://Ravi")
            print(res.contents[0].text)

asyncio.run(main())
```

### Integrating with an LLM (agent loop)
1. `session.list_tools()` → convert to the LLM provider's tool format.
2. Send user message + tools to the LLM.
3. If the LLM returns a tool call → `session.call_tool(name, args)`.
4. Append the tool result to the conversation → call the LLM again.
5. Repeat until the LLM returns a normal answer.

(LangChain/LangGraph provide `langchain-mcp-adapters` to load MCP tools straight into agents.)

---

## 13. End-to-end example: SQL MCP server

**Goal:** let an LLM query a database in natural language (the LLM writes SQL; the server executes it safely).

```python
# sql_server.py
import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQL Explorer")
DB = "world.db"

def run(query: str, params=()):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query, params).fetchall()]

@mcp.tool()
def list_tables() -> list[str]:
    """List all tables in the database."""
    rows = run("SELECT name FROM sqlite_master WHERE type='table'")
    return [r["name"] for r in rows]

@mcp.tool()
def describe_table(table: str) -> list[dict]:
    """Return column names and types for a table."""
    if not table.isidentifier():
        raise ValueError("Invalid table name")
    return run(f"PRAGMA table_info({table})")

@mcp.tool()
def get_countries(continent: str | None = None, limit: int = 20) -> list[dict]:
    """Get countries, optionally filtered by continent."""
    if continent:
        return run("SELECT * FROM country WHERE continent = ? LIMIT ?", (continent, limit))
    return run("SELECT * FROM country LIMIT ?", (limit,))

@mcp.tool()
def run_select(query: str) -> list[dict]:
    """Run a READ-ONLY SQL SELECT query and return rows."""
    if not query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")
    return run(query)

if __name__ == "__main__":
    mcp.run()
```

**Design considerations**
- **Read-only** DB user/connection where possible; block `INSERT/UPDATE/DELETE/DROP`.
- Use **parameterized queries** (avoid SQL injection); whitelist identifiers.
- **Limit rows** returned; add timeouts.
- Expose **schema as a resource** so the LLM knows table structure before writing SQL (see next section).
- For Postgres/MySQL use `psycopg`/`mysql-connector` (+ connection pooling); keep credentials in env vars.

---

## 14. Adding resources and prompts

### Schema as a resource
```python
@mcp.resource("schema://main")
def get_schema() -> str:
    """Full database schema (DDL)."""
    rows = run("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")
    return "\n".join(r["sql"] for r in rows)

@mcp.resource("table://{name}/sample")
def table_sample(name: str) -> str:
    """First 5 rows of a table."""
    import json
    return json.dumps(run(f"SELECT * FROM {name} LIMIT 5"), default=str)
```

### Prompt for a guided workflow
```python
@mcp.prompt()
def analyze_table(table: str) -> str:
    """Guide the model to analyze a table."""
    return (f"Inspect the schema of '{table}', run 3 useful SELECT queries, "
            f"and summarize key insights with numbers.")
```

### Dynamic updates
- If tools/resources change at runtime, send `notifications/tools/list_changed` / `resources/list_changed` so clients refresh.

---

## 15. Remote servers, deployment & auth

### Run over Streamable HTTP
```python
mcp = FastMCP("Remote Demo", host="0.0.0.0", port=8000)
mcp.run(transport="streamable-http")     # endpoint: http://host:8000/mcp
```
Test with Inspector (choose Streamable HTTP, enter URL).

### Deployment options
- Containerize with **Docker** → deploy to Render, Railway, Fly.io, AWS (ECS/Lambda), GCP Cloud Run, Azure, etc.
- Put behind **HTTPS** (reverse proxy such as nginx/Caddy or the platform's TLS).
- Prefer **stateless** design when possible so it scales horizontally.
- Use health checks, structured logging, and rate limiting.

### Authorization
- The MCP spec's remote authorization is based on **OAuth 2.1** (MCP server acts as an OAuth **resource server**; supports metadata discovery, PKCE, dynamic client registration in the spec).
- For simple/private setups: **API keys / bearer tokens** in headers.
- Never hardcode secrets, so use environment variables or a secret manager.

---

## 16. Security best practices

MCP gives LLMs real power, so treat it like exposing an API to an untrusted caller.

- **Prompt injection / tool poisoning:** malicious content in tool descriptions or tool output (web pages, emails, issues) can instruct the model to do harmful things. Treat all tool output as **untrusted data**.
- **Least privilege:** give servers minimum scopes (read-only tokens, restricted directories, narrow DB roles).
- **Human in the loop:** require user approval for destructive/sensitive actions; show tool inputs before execution.
- **Validate & sanitize** all inputs (SQL injection, path traversal, command injection). Never `shell=True` with model-provided strings.
- **Trust only vetted servers:** third-party servers run code on your machine (stdio) or receive your data (remote). Review source, pin versions.
- **Rug pulls:** a server can change tool descriptions after approval; re-review on updates.
- **Confused deputy / token passthrough:** don't forward tokens blindly; validate audiences.
- **Isolate secrets:** don't expose env secrets to the model; avoid logging sensitive data.
- **Sandboxing:** run local servers in containers/limited users when possible.
- **Origin validation / localhost binding** for local HTTP servers (mitigate DNS-rebinding).

---

## 17. Comparisons

### MCP vs Function/Tool Calling
| | Function calling | MCP |
|---|---|---|
| Level | LLM API feature: model emits structured call | Protocol for **discovering & executing** tools across apps |
| Tool definition | Hardcoded per app/provider | Served dynamically by servers |
| Reuse | Low (rewrite per app) | High (one server, many clients) |
| Relationship | **Complementary**: MCP tools are typically presented to the LLM via its function-calling interface |

### MCP vs REST API
- REST: designed for **developers**/programs with fixed endpoints and docs.
- MCP: designed for **AI agents**: self-describing, discoverable (`tools/list`), with schemas and descriptions the model can read; stateful sessions; bidirectional (sampling, notifications).
- Many MCP servers **wrap** existing REST APIs.

### MCP vs RAG
- RAG: retrieve relevant text chunks (usually from a vector store) and stuff them into the prompt: a *technique*.
- MCP: a *protocol* for connecting to data/tools; an MCP server can **implement** retrieval (e.g. a "search_docs" tool) but also do actions.

### MCP vs Agent frameworks (LangChain/LangGraph/CrewAI)
- Frameworks orchestrate **agent logic** (planning, memory, flows).
- MCP standardizes **tool/data connectivity**. They work together (agent uses MCP tools).

### MCP vs A2A (Agent2Agent)
- MCP: agent ↔ tools/data. A2A: agent ↔ agent communication. Complementary.

---

## 18. Common pitfalls & debugging

| Symptom | Likely cause / fix |
|---|---|
| Server connects then breaks immediately (stdio) | `print()` to stdout. Use stderr/logging. |
| Host doesn't show the server | Wrong/relative path in config; invalid JSON; forgot to restart host |
| `command not found` (uv/npx) | Host has different PATH. Use absolute path to the executable |
| LLM never calls your tool | Vague name/description; too many similar tools |
| LLM passes wrong args | Poor parameter names/docs; add type hints and descriptions |
| Huge responses slow/blow context | Paginate, limit rows, summarize server-side |
| Works in Inspector, not in host | Environment differences (env vars, cwd, venv). Pass `env`, use `--directory` |
| Timeouts | Long-running tools: use progress notifications, async, increase timeout |
| Windows path issues | Escape backslashes in JSON or use forward slashes |

**Debugging tips:** use Inspector first; check host logs (Claude Desktop: `~/Library/Logs/Claude/mcp*.log` on macOS); log to stderr; test the function as plain Python before wrapping it.

---

## 19. Cheat sheet & revision questions

### Cheat sheet
- **MCP** = open standard to connect LLM apps ↔ tools/data. "USB-C for AI."
- **Roles:** Host (app) → Client (1:1 connector) → Server (capabilities).
- **Wire format:** JSON-RPC 2.0 (request / response / notification).
- **Server primitives:** Tools (model-controlled), Resources (app-controlled), Prompts (user-controlled).
- **Client features:** Sampling, Roots, Elicitation.
- **Transports:** stdio (local) · Streamable HTTP (remote; replaced HTTP+SSE).
- **Python:** `pip/uv add "mcp[cli]"` → `FastMCP` → `@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()` → `mcp.run()`.
- **Test:** `npx @modelcontextprotocol/inspector` or `uv run mcp dev server.py`.
- **Config:** `mcpServers` → `command`, `args`, `env` in host config JSON.
- **Security:** least privilege, human approval, treat tool output as untrusted.

### Revision questions
1. What problem does MCP solve? Explain N×M vs N+M.
2. Differentiate Host, Client, Server. How many servers can one client connect to?
3. Why is a *tool* "model-controlled" while a *resource* is "application-controlled"?
4. What are the three phases of the MCP lifecycle? What is capability negotiation?
5. Why must a stdio server never write to stdout?
6. Compare stdio and Streamable HTTP. Why did Streamable HTTP replace HTTP+SSE?
7. What is sampling and why is it useful for server authors?
8. How does FastMCP generate a tool's JSON Schema?
9. Design a safe SQL MCP server: list at least four safeguards.
10. How do MCP and function calling relate? Are they competitors?
11. List three MCP-specific security threats and mitigations.
12. How would you deploy a server remotely and secure it?

### Suggested practice projects
1. **Calculator/utility server** (tools only): to learn basics.
2. **File notes server** (tools + resources): add/search notes in a folder.
3. **SQL explorer** (as above) with schema resource and analysis prompt.
4. **API wrapper server** (weather/news/GitHub) with API-key via env.
5. **Remote Streamable-HTTP server** in Docker, deployed to a cloud platform, connected from a host.
6. **Custom MCP client + LLM agent loop** (LangGraph) using multiple servers.

### Official references
- Spec & docs: https://modelcontextprotocol.io
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- TypeScript SDK: https://github.com/modelcontextprotocol/typescript-sdk
- Reference servers: https://github.com/modelcontextprotocol/servers
- Inspector: https://github.com/modelcontextprotocol/inspector

> ⚠️ MCP evolves quickly (spec versions, SDK APIs, auth details). Verify code snippets and spec details against the official docs for the version you install.