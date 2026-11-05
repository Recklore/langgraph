# Master Notes: Model Context Protocol (MCP)

**Based on the CampusX MCP Playlist & Architectural Blueprint**

## Table of Contents

1. [Module 1: Introduction to Model Context Protocol (MCP)](#module-1-introduction-to-model-context-protocol-mcp)

2. [Module 2: The Why – Problem Statement & Architectural Need](#module-2-the-why--problem-statement--architectural-need)

3. [Module 3: MCP Architecture & Core Primitives](#module-3-mcp-architecture--core-primitives)

4. [Module 4: The MCP Lifecycle & Protocol Flow](#module-4-the-mcp-lifecycle--protocol-flow)

5. [Module 5: Connecting MCP Servers to Claude Desktop](#module-5-connecting-mcp-servers-to-claude-desktop)

6. [Module 6: Building Local MCP Servers from Scratch](#module-6-building-local-mcp-servers-from-scratch)

7. [Module 7: Building & Deploying Remote MCP Servers](#module-7-building--deploying-remote-mcp-servers)

8. [Module 8: Building Custom MCP Clients](#module-8-building-custom-mcp-clients)

9. [Cheatsheet & Key Takeaways](#cheatsheet--key-takeaways)

## Module 1: Introduction to Model Context Protocol (MCP)

### What is MCP?

The **Model Context Protocol (MCP)** is an open, standardized, client-server protocol introduced by Anthropic designed to seamlessly connect Large Language Model (LLM) applications (hosts/clients) with external data sources, tools, local environments, and enterprise software systems.

In simple terms, **MCP is the "USB-C port for AI applications."**

Just as USB-C replaced hundreds of proprietary charging and data cables with a single open standard, MCP replaces custom, fragmented integration code with a unified, open protocol.

```
+-----------------------------------------------------------------------+
|                             AI HOST / CLIENT                          |
|             (Claude Desktop, Cursor, Custom Agent, VS Code)          |
+-----------------------------------------------------------------------+
                                   |
                         Model Context Protocol (MCP)
                                   |
     +-----------------------------+-----------------------------+
     |                             |                             |
+----+----+                   +----+----+                   +----+----+
| Filesystem|                 | Postgres|                 | GitHub  |
| MCP Server|                 | MCP Server|                | MCP Server|
+---------+                   +---------+                   +---------+

```

### Philosophy & Vision

* **Decoupling Data from Models:** LLMs should not need custom glue code for every distinct tool or database.

* **Standardization:** Establish a universal language using JSON-RPC 2.0 over standardized transports (`stdio`, `SSE`).

* **Dynamic Context Provisioning:** Expose state, data, actions, and prompts to models on-demand at runtime rather than hardcoding static contexts.

## Module 2: The Why – Problem Statement & Architectural Need

### The $M \times N$ Integration Crisis

Before MCP, connecting $N$ AI client applications (e.g., Claude Desktop, Cursor, ChatGPT, custom LangChain apps) to $M$ data sources or tools (e.g., PostgreSQL, GitHub, Jira, local Filesystem, Slack) required building bespoke connectors for every single pair.

$$
\text{Total Custom Integrations Required} = M \times N
$$

If you have $5$ AI clients and $10$ enterprise databases/APIs:

$$
\text{Integrations} = 5 \times 10 = 50 \text{ custom implementations}
$$

```
TRADITIONAL INTEGRATION ($M \times N$ Complexity):

  AI Client 1 ------> [ Custom Code ] ------> PostgreSQL
  AI Client 1 ------> [ Custom Code ] ------> GitHub
  AI Client 2 ------> [ Custom Code ] ------> PostgreSQL
  AI Client 2 ------> [ Custom Code ] ------> Slack
  AI Client 3 ------> [ Custom Code ] ------> Jira

```

### The $1 \times N$ & $M \times 1$ Solution with MCP

With MCP as an open standard, every tool vendor builds **one** MCP Server, and every AI client platform builds **one** MCP Client interface.

$$
\text{Total Integrations Required} = M + N
$$

For $5$ AI clients and $10$ tools:

$$
\text{Integrations} = 5 + 10 = 15 \text{ standard components}
$$

```
MCP STANDARDIZED INTEGRATION ($M + N$ Complexity):

  AI Clients (N)                    MCP Standard                     MCP Servers (M)
+----------------+               +----------------+               +-----------------+
| Claude Desktop |               |                | ------------> | PostgreSQL Server|
| Cursor IDE     | ------------> | MCP PROTOCOL   | ------------> | GitHub Server   |
| Custom App     |               | (JSON-RPC 2.0) | ------------> | Slack Server    |
+----------------+               +----------------+               +-----------------+

```

### Core Problems Solved by MCP

| Feature / Challenge | Traditional Approach (RAG / Function Calling) | MCP Standard Approach | 
| ----- | ----- | ----- | 
| **Tool/Data Discovery** | Static hardcoding of JSON schemas into system prompts. | **Dynamic Runtime Discovery** via standard protocol endpoints. | 
| **Context Boundaries** | Dumping whole documents or unfiltered vector chunks into prompts. | Structured **Resources** with clear URI schemas (`file:///`, `db://`). | 
| **Security & Auditing** | Arbitrary API keys embedded everywhere; unchecked tool execution. | **Host Sandbox & User Approval Gate** for execution and permissions. | 
| **Reusability** | Tool definitions tied strictly to one framework (e.g., OpenAI, LangChain). | **Universal Compatibility** across any client supporting MCP. | 

## Module 3: MCP Architecture & Core Primitives

### The Triad Architecture

MCP operates on a three-tier model:

1. **Host Application:** The overarching program where the user interacts with the AI (e.g., Claude Desktop, Cursor, VS Code, Custom Python App).

2. **MCP Client:** An internal component within the Host that maintains a 1-to-1 connection with an MCP Server.

3. **MCP Server:** A lightweight server (local process or remote service) exposing specific data, tools, or prompts via the MCP protocol.

```
+--------------------------------------------------------------------------+
| HOST APPLICATION (e.g., Claude Desktop)                                  |
|                                                                          |
|   +-------------------+                     +------------------------+   |
|   |  User Interface   |                     |   LLM Engine / API     |   |
|   +---------+---------+                     +-----------+------------+   |
|             |                                           ^                |
|             v                                           |                |
|   +-----------------------------------------------------+------------+   |
|   |                       MCP CLIENT LAYER                           |   |
|   +---------------+--------------------+------------------+----------+   |
+-------------------|--------------------|------------------|--------------+
                    | (stdio/SSE)        | (stdio/SSE)      | (stdio/SSE)
                    v                    v                  v
            +---------------+    +---------------+  +---------------+
            |  MCP Server 1 |    |  MCP Server 2 |  |  MCP Server 3 |
            |  (Filesystem) |    |  (Database)   |  |   (GitHub)    |
            +---------------+    +---------------+  +---------------+

```

### The 3 Core Primitives of MCP

MCP divides all interactions into three foundational building blocks:

```
                  +----------------------------------+
                  |         MCP PRIMITIVES           |
                  +----------------------------------+
                  |                                  |
     +------------+------------+          +----------+----------+
     |                         |          |                     |
     v                         v          v                     v
+----------+             +-----------+ +----------+       +-----------+
| RESOURCES|             |   TOOLS   | | PROMPTS  |       | SAMPLING  |
|  (Data)  |             | (Actions) | |(Templates|       |(LLM-in-loop|
+----------+             +-----------+ +----------+       +-----------+

```

#### 1. Resources (Passive Context / Nouns)

* **What they are:** Read-only data endpoints exposed by the server to provide context to the LLM (e.g., file contents, database schemas, application logs).

* **Identifier:** Identified via unique **URIs** (e.g., `file:///logs/app.log`, `postgres://users/schema`).

* **Types:**

  * **Text Resources:** Plain text, JSON, Source Code.

  * **Binary Resources:** Blob data encoded in Base64 (e.g., PDF documents, images).

* **Resource Templates:** Allow dynamic URI matching (e.g., `github://{owner}/{repo}/issues`).

#### 2. Tools (Active Capabilities / Verbs)

* **What they are:** Executable functions that allow the LLM to perform side-effects or query live computations (e.g., execute SQL, post a Slack message, fetch API data).

* **Schema:** Parameterized using standard **JSON Schema**.

* **Control:** Executed only when the LLM requests a tool call and the Host/User approves it.

#### 3. Prompts (Reusable Workflow Patterns)

* **What they are:** Server-side predefined prompt templates that guide user-LLM interactions.

* **Use Case:** Exposing slash commands or workflow shortcuts directly in the host interface (e.g., `/analyze-codebase`, `/summarize-ticket`).

* **Parameters:** Prompts take arguments and expand into messages/context blocks.

#### 4. Advanced Primitive: Sampling (Client Capability)

* Allows an **MCP Server** to request the **MCP Client/Host** to run an LLM completion on its behalf.

* Enables agentic server logic without giving the server direct access to secret API keys!

### Transport Layer Architecture

MCP communicates using two standard transport mechanisms:

```
+----------------------------------------------------------------------+
|                         TRANSPORT MECHANISMS                         |
+----------------------------------+-----------------------------------+
| 1. STDIO (Standard IO)           | 2. SSE (Server-Sent Events)       |
+----------------------------------+-----------------------------------+
| * Used for Local Process Execution| * Used for Remote Network Servers |
| * Fast, zero network overhead    | * HTTP POST + SSE streaming       |
| * Server spawned via child process| * Ideal for Docker, APIs, Cloud   |
+----------------------------------+-----------------------------------+

```

1. **`stdio` (Standard Input/Output):**

   * Host spawns the server as a subprocess.

   * Communication occurs via `stdin` and `stdout`.

   * Ideal for local system tools (filesystem, local SQLite, shell scripting).

2. **`SSE` (Server-Sent Events over HTTP):**

   * Client opens an HTTP connection to receive SSE streams from a remote server.

   * Client sends requests to the server via standard HTTP `POST` requests.

   * Ideal for hosted microservices, remote databases, and cloud APIs.

### MCP Sampling, Elicitation, and Authentication

These features are easy to confuse because they all involve an MCP server
asking for something during an active request. They solve different problems:

| Feature | Who initiates the request? | What is requested? | Main safety boundary |
| --- | --- | --- | --- |
| **Sampling** | Server -> Client/Host | An LLM completion | The host controls the model, context, and user approval |
| **Elicitation** | Server -> Client/Host -> User | Additional user input | The user reviews, accepts, declines, or cancels |
| **Authentication** | Client/Host <-> Authorization Server/Server | Identity and access permission | Tokens and scopes protect the remote server |

#### 1. Sampling: server-requested model generation

Sampling lets a server ask the connected client to obtain an LLM completion
while the server remains isolated from the model provider's API key. A typical
flow is:

```text
MCP server
    -> sampling/createMessage
       (messages, optional modelPreferences, optional tools)
MCP client/host
    -> checks capability, policy, and user approval
    -> calls its configured LLM
    -> returns the generated assistant message
MCP server
    -> uses the result to continue its task
```

The client must advertise the `sampling` capability before a server can use
this feature. If sampling includes tool use, the client must also advertise
support for sampling tools. The host should show the request to the user and
retain control over model selection, maximum tokens, temperature, context
sharing, and whether the request is allowed at all. Servers should not assume
that a particular model or provider is available.

**Current specification status:** the latest MCP specification marks Sampling
as deprecated and recommends that new implementations do not adopt it. Existing
implementations should plan a migration to direct model integration. Older MCP
material may still describe it as a normal advanced primitive, so always check
the protocol version used by the client and server.

#### 2. Elicitation: requesting information from the user

Elicitation provides a standard way for a server to request missing information
through the client instead of guessing or silently using defaults. The server
sends an `elicitation/create` request containing a clear message and a mode.

**Form mode** collects structured, in-band data:

```json
{
  "method": "elicitation/create",
  "params": {
    "mode": "form",
    "message": "Which project should I inspect?",
    "requestedSchema": {
      "type": "object",
      "properties": {
        "project": {
          "type": "string",
          "description": "Project name"
        }
      },
      "required": ["project"]
    }
  }
}
```

The client displays the form, lets the user review or edit the values, and
returns an action such as `accept`, `decline`, or `cancel`. Form schemas are
intentionally limited to simple, flat structures so clients can render them
consistently. Form mode must not be used to collect passwords, API keys,
payment details, or other credentials.

**URL mode** is for sensitive or external interactions. The client shows the
destination and obtains user consent before opening it; the sensitive data is
handled outside the MCP client. This is appropriate for OAuth sign-in, payment
authorization, or entering a secret into a trusted provider page. URL mode
does not change the MCP client's bearer token and is not a replacement for the
MCP authorization flow.

Clients should clearly identify which server requested the information and
provide explicit decline and cancel controls. Servers should request only the
minimum information needed and must handle refusal without treating it as a
successful result.

#### 3. Authentication and authorization

Authentication answers **who is calling**; authorization answers **what that
identity may access**. Local `stdio` servers normally rely on the host's local
process permissions and should not use the HTTP OAuth flow. Remote HTTP MCP
servers may require authorization.

For an HTTP-based protected MCP server, the usual roles are:

1. **MCP client:** an OAuth client acting on behalf of the user.
2. **Authorization server:** authenticates the user and issues access tokens.
3. **MCP server:** the protected resource server that validates the token and
   enforces scopes and permissions.

An OAuth-oriented flow is:

```text
Client discovers the authorization server
    -> user authenticates and grants consent
    -> client receives an authorization code
    -> client exchanges it for an access token (use PKCE)
    -> client sends: Authorization: Bearer <access-token>
    -> MCP server validates issuer, audience/resource, expiry, and scopes
```

Practical rules:

* Prefer OAuth for user-specific access and short-lived, least-privilege
  tokens. Use refresh tokens only in a secure client-side store.
* Use an API key or personal access token only when the server requires a
  shared identity; keep it in a secret manager or protected connection, never
  in source code, prompts, or committed configuration.
* Do not forward a token issued for one MCP server to another server. Bind
  tokens to the intended resource/audience and validate scopes on every
  protected operation.
* Use TLS for remote transports, validate authorization-server metadata and
  redirect responses, and rotate or revoke credentials according to the
  provider's policy.
* Return an explicit authentication or insufficient-scope error. Do not
  silently fall back to unauthenticated access.

Authentication protects the MCP connection; it does not automatically make a
tool safe. Hosts should still display tool details, require approval for
high-impact actions, restrict server permissions, and log security-relevant
events without recording secrets.

**Further reading**

* [MCP Sampling specification](https://modelcontextprotocol.io/specification/latest/client/sampling)
* [MCP Elicitation specification](https://modelcontextprotocol.io/specification/latest/client/elicitation)
* [MCP Authorization specification](https://modelcontextprotocol.io/specification/latest/basic/authorization)
* [Microsoft Learn: Set up MCP server authentication](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/mcp-authentication)

## Module 4: The MCP Lifecycle & Protocol Flow

MCP is built on **JSON-RPC 2.0**. All requests, responses, and notifications strictly conform to JSON-RPC specs.

```
CLIENT                                                    SERVER
  |                                                          |
  |------------------- 1. Transport Connect ---------------->|
  |                                                          |
  |------------------- 2. initialize request --------------->|
  |                    (capabilities, protocolVersion)       |
  |                                                          |
  |<------------------ 3. initialize response ---------------|
  |                    (capabilities, serverInfo)            |
  |                                                          |
  |------------------- 4. initialized notification --------->|
  |                                                          |
  |=================== HANDSHAKE COMPLETE ===================|
  |                                                          |
  |------------------- 5. tools/list ----------------------->|
  |<------------------ 6. Array of Tool Schemas -------------|
  |                                                          |
  |------------------- 7. tools/call (name, args) ----------->|
  |<------------------ 8. Execution Result ------------------|
  |                                                          |
  |<-- 9. notifications/tools/list_changed (Optional) -------|
  |                                                          |

```

### Step-by-Step Lifecycle Phases

#### Phase 1: Handshake & Negotiation

1. **Client Sends `initialize`:** Transmits protocol version (`2024-11-05` / latest) and client capabilities.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {}
    },
    "clientInfo": { "name": "ClaudeDesktop", "version": "1.0.0" }
  }
}

```

2. **Server Responds:** Sends server information and its supported primitives/capabilities (`tools`, `resources`, `prompts`).

3. **Initialized Acknowledgment:** Client sends `notifications/initialized` to confirm ready state.

#### Phase 2: Capability Discovery

* `tools/list`: Client requests available tools.

* `resources/list`: Client discovers available resources/URIs.

* `prompts/list`: Client requests prompt templates.

#### Phase 3: Execution & Message Exchange

* **Reading Resource:** `resources/read` with URI `{"uri": "file:///data.json"}`.

* **Executing Tool:** `tools/call` with tool name and structured arguments.

* **Getting Prompt:** `prompts/get` with prompt name and arguments.

#### Phase 4: Dynamic Notifications

* When server state changes (e.g., a file is added or database schema updates), the server sends notifications like `notifications/tools/list_changed` or `notifications/resources/updated`.

## Module 5: Connecting MCP Servers to Claude Desktop

Claude Desktop acts as a primary **MCP Host Application**. You can connect both official pre-built MCP servers and your own custom servers.

### Configuration File Setup

The configuration file is located at:

* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Standard Configuration Format

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/username/Desktop",
        "/Users/username/Projects"
      ]
    },
    "sqlite": {
      "command": "uvx",
      "args": [
        "mcp-server-sqlite",
        "--db-path",
        "/Users/username/data/app.db"
      ]
    },
    "custom-python-server": {
      "command": "python",
      "args": [
        "/Users/username/mcp-projects/server.py"
      ],
      "env": {
        "API_KEY": "your_secret_api_key_here"
      }
    }
  }
}

```

### Steps to Verify Connection

1. Edit `claude_desktop_config.json`.

2. Fully quit and restart Claude Desktop.

3. Look for the **Hammer Icon (**$\hat{\mathbf{\sigma}}$**)** in the Claude Desktop chat UI.

4. Clicking the hammer icon displays available tools registered from your MCP servers.

### Debugging & Inspecting Logs

* **Claude Desktop Logs:**

  * macOS: `~/Library/Logs/Claude/mcp*.log`

  * Windows: `%APPDATA%\Claude\logs\mcp*.log`

* **MCP Inspector Tool:** Run Anthropic's developer inspector tool to test servers visually in the browser:

  ```bash
  npx @modelcontextprotocol/inspector node build/index.js
  # or for Python
  npx @modelcontextprotocol/inspector python server.py
  
  ```

## Module 6: Building Local MCP Servers from Scratch

We can write MCP servers using either Python (via `mcp` library or `FastMCP`) or TypeScript (`@modelcontextprotocol/sdk`).

### Option A: Building with Python (`FastMCP`)

`FastMCP` provides a clean, high-level Python interface inspired by FastAPI.

#### 1. Setup Environment

```bash
pip install mcp

```

#### 2. Complete Python MCP Server (`server.py`)

```python
import json
import sqlite3
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Company Intelligence Server")

# -------------------------------------------------------------
# 1. REGISTERING A RESOURCE (Read-only Context)
# -------------------------------------------------------------
@mcp.resource("company://policy/privacy")
def get_privacy_policy() -> str:
    """Returns the company's internal privacy policy document."""
    return "All data processed by this system must adhere to strict zero-retention policies."

@mcp.resource("config://version")
def get_system_version() -> str:
    """Returns current system configuration version."""
    return json.dumps({"version": "2.4.0", "environment": "production"})

# -------------------------------------------------------------
# 2. REGISTERING A TOOL (Executable Action)
# -------------------------------------------------------------
@mcp.tool()
def calculate_employee_bonus(salary: float, performance_score: float) -> float:
    """
    Calculates employee annual bonus based on salary and performance score (1.0 to 5.0).
    
    Args:
        salary: Base annual salary in USD.
        performance_score: Score between 1.0 and 5.0.
    """
    if performance_score < 3.0:
        multiplier = 0.05
    elif performance_score < 4.5:
        multiplier = 0.15
    else:
        multiplier = 0.30
        
    return salary * multiplier

@mcp.tool()
def query_database(query: str) -> str:
    """Executes a read-only query on the local employee database."""
    # Safety Check
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed for security."
        
    try:
        conn = sqlite3.connect("company.db")
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return json.dumps(rows)
    except Exception as e:
        return f"Database Query Failed: {str(e)}"

# -------------------------------------------------------------
# 3. REGISTERING A PROMPT (Workflow Template)
# -------------------------------------------------------------
@mcp.prompt()
def generate_review_prompt(employee_name: str, role: str) -> str:
    """Generates a structured prompt template for performance reviews."""
    return f"""
You are an executive HR assistant. Write a formal performance review for {employee_name}, who works as a {role}.
Please cover:
1. Key achievements
2. Areas of growth
3. Recommended bonus strategy using the calculate_employee_bonus tool.
"""

# Entrypoint for stdio transport
if __name__ == "__main__":
    mcp.run(transport="stdio")

```

### Option B: Building with TypeScript / Node.js

#### 1. Setup Environment

```bash
npm init -y
npm install @modelcontextprotocol/sdk zod
npm install -D typescript @types/node

```

#### 2. Complete TypeScript MCP Server (`index.ts`)

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

const server = new Server(
  {
    name: "ts-math-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define Tool Schema
const MultiplyArgsSchema = z.object({
  a: z.number().describe("First number"),
  b: z.number().describe("Second number"),
});

// List Available Tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "multiply",
        description: "Multiplies two numbers together",
        inputSchema: {
          type: "object",
          properties: {
            a: { type: "number", description: "First number" },
            b: { type: "number", description: "Second number" },
          },
          required: ["a", "b"],
        },
      },
    ],
  };
});

// Handle Tool Execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "multiply") {
    const { a, b } = MultiplyArgsSchema.parse(request.params.arguments);
    const result = a * b;
    return {
      content: [
        {
          type: "text",
          text: `The product of ${a} and ${b} is ${result}`,
        },
      ],
    };
  }
  throw new Error(`Tool not found: ${request.params.name}`);
});

// Start Server with STDIO Transport
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);

```

## Module 7: Building & Deploying Remote MCP Servers

While `stdio` works locally, remote web-based deployments require **SSE (Server-Sent Events)** transport over HTTP/HTTPS.

### Remote Server Architecture (SSE)

```
+------------------+                    +-------------------------------+
|    MCP CLIENT    |                    |    REMOTE MCP SERVER          |
|                  |                    |    (FastAPI / Express)        |
|                  |  HTTP GET /sse     |                               |
|                  |------------------->|  Establishes SSE Stream Channel|
|                  |<-------------------|  Sends 'endpoint' session URI |
|                  |  SSE Connection    |                               |
|                  |                    |                               |
|                  |  HTTP POST /message|                               |
|                  |------------------->|  Executes Tool / Resource     |
|                  |<-------------------|  Returns JSON-RPC Response    |
+------------------+                    +-------------------------------+

```

### Implementing Remote SSE Server in Python (FastAPI)

```python
from fastapi import FastAPI
from starlette.responses import StreamingResponse
from mcp.server.fastmcp import FastMCP

# Instantiate FastMCP
mcp = FastMCP("Remote Analytics MCP Server")

@mcp.tool()
def get_live_stock_price(symbol: str) -> str:
    """Fetches real-time stock price for a ticker symbol."""
    # Simulated stock API call
    data = {"AAPL": "$235.50", "GOOGL": "$178.20", "MSFT": "$420.10"}
    price = data.get(symbol.upper(), "Symbol not found")
    return f"Stock {symbol.upper()}: {price}"

# Get the underlying ASGI / FastAPI app from FastMCP for SSE deployment
app = mcp.sse_app()

# Run using Uvicorn: uvicorn server:app --host 0.0.0.0 --port 8000

```

### Security & Deployment Best Practices for Remote MCP

1. **Authentication:** For remote HTTP servers, use TLS and an appropriate
   OAuth bearer token or API key. Store credentials outside source code and
   validate identity, audience, expiry, and scopes on the server.

2. **Reverse Proxy:** Place behind Nginx or Cloudflare with SSL/TLS termination enabled.

3. **Containerization (Docker):**

```docker
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

```

## Module 8: Building Custom MCP Clients

Building your own MCP Client allows custom AI applications (LangChain, LlamaIndex, custom agents) to connect dynamically to any MCP Server.

```
+-------------------------------------------------------------------------+
|                         CUSTOM MCP CLIENT APP                           |
|                                                                         |
| 1. Connect Transport (stdio/sse)                                        |
| 2. Initialize Session                                                   |
| 3. Fetch Tools List -> Convert Schemas -> Inject into LLM API Call       |
| 4. User Query -> LLM returns Tool Call Request                          |
| 5. Client routes Tool Call to MCP Server via session.call_tool()       |
| 6. Return Tool Result back to LLM -> Final Answer                       |
+-------------------------------------------------------------------------+

```

### Complete Python Custom MCP Client Implementation

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import openai

async def run_custom_mcp_client():
    # 1. Define Server Connection Parameters
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"], # Path to local MCP server
        env=None
    )

    # 2. Connect via Stdio Transport
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize Protocol Handshake
            await session.initialize()
            print("[Client] Handshake with MCP Server successful!")

            # 3. Discover Available Tools from Server
            tools_response = await session.list_tools()
            available_tools = tools_response.tools
            print(f"[Client] Discovered {len(available_tools)} tool(s).")

            # Format tools for OpenAI function calling format
            openai_tools = []
            for tool in available_tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })

            # 4. User Interaction & LLM Query
            user_prompt = "Calculate the bonus for an employee earning $100,000 with a performance score of 4.8."
            print(f"\n[User Query]: {user_prompt}")

            client = openai.OpenAI()
            messages = [{"role": "user", "content": user_prompt}]

            # Call LLM with tool schemas
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=openai_tools,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            
            # 5. Check if LLM requested a Tool Call
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"[LLM Decision] Executing Tool: '{tool_name}' with arguments: {tool_args}")

                # 6. Dispatch Tool Call to MCP Server
                mcp_result = await session.call_tool(tool_name, arguments=tool_args)
                tool_output_text = mcp_result.content[0].text
                print(f"[MCP Server Output]: {tool_output_text}")

                # Pass Tool Result back to LLM for final synthesis
                messages.append(response_message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output_text
                })

                final_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )

                print(f"\n[Final Response]:\n{final_response.choices[0].message.content}")

if __name__ == "__main__":
    asyncio.run(run_custom_mcp_client())

```

## Cheatsheet & Key Takeaways

### Core Architectural Equations

$$
\text{Traditional Integration Complexity} = M \times N
$$

$$
\text{MCP Standard Complexity} = M + N
$$

### MCP Primitives Summary

* **Resources:** `read-only` data context (URIs: `file://`, `postgres://`).

* **Tools:** `executable` functions with side-effects or computations.

* **Prompts:** `reusable` workflow prompt templates.

* **Sampling:** Server requests LLM generation through the client safely.

* **Elicitation:** Server requests additional user input through the client;
  use form mode for non-sensitive structured data and URL mode for sensitive
  external flows.

* **Authentication:** Remote HTTP servers can protect requests with OAuth and
  bearer tokens; local `stdio` servers generally rely on host process
  permissions.

* **Sampling status:** Deprecated in the latest MCP specification; verify the
  protocol version before implementing it.

### Transport Comparison

* **`stdio`:** Local subprocess; high speed; communicates over standard I/O streams (`stdin`/`stdout`).

* **`SSE`:** Network service; over HTTP/HTTPS; server-sent events for streaming + HTTP POST for requests.

### Configuration Quick Reference

* Path: