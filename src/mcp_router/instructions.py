SYSTEM_PROMPT = """
This server orchestrates access to multiple MCP servers through a single unified interface.

Use the mcp_router tool to interact with any connected MCP server:

1. Discovery: Call list_tools to see what tools are available on a server
2. Schema inspection: Always call get_tool_schema before executing any tool
3. Execution: Use execute_tool for quick operations or spawn_tool_in_background for long-running tasks
4. Monitoring: Poll background tasks with poll_tool_result using the returned tool_call_id

CRITICAL: Never execute a tool without first getting its schema. This prevents malformed requests.

For quick operations, use execute_tool directly.
For operations that may take >30 seconds, use spawn_tool_in_background then poll_tool_result.

CURRENT LOADED MCP SERVERS:
{description}
"""

TOOL_DESCRIPTION = """
Meta-tool for interacting with MCP (Model Context Protocol) servers.

Enables discovery, inspection, and execution (both synchronous and asynchronous) 
of tools exposed by MCP server sessions. This router provides a unified interface 
for managing tool calls across multiple MCP servers.

Supported Actions
-----------------
- **list_tools**: List all available tools on the specified MCP server
- **get_description**: Retrieve the description of a specific tool (use only if the tool name is ambiguous)
- **get_tool_schema**: Retrieve the complete input schema for a specific tool
- **execute_tool**: Execute a tool synchronously and wait for results
- **spawn_tool_in_background**: Start a tool execution asynchronously and receive a tracking ID
- **poll_tool_result**: Check the status and retrieve results of a background tool execution

Parameters
----------
server_name : str
    Name of the MCP server to interact with. Must exist in hmap_mcp_server_to_session.
action : str
    The action to perform. Must be one of: "list_tools", "get_description", 
    "get_tool_schema", "execute_tool", "spawn_tool_in_background", "poll_tool_result"
tool_name : Optional[str], default=None
    Name of the tool on the MCP server. Required for: get_description, get_tool_schema,
    execute_tool, and spawn_tool_in_background.
tool_arguments : Optional[Dict], default=None
    Dictionary of arguments for tool execution. Required for: execute_tool and 
    spawn_tool_in_background.
tool_call_id : Optional[str], default=None
    Unique identifier for a background tool execution. Required for: poll_tool_result.
    Generated automatically by spawn_tool_in_background.
timeout : float, default=60
    Timeout in seconds for background tool executions. Only applies to spawn_tool_in_background.

Returns
-------
List[Dict]
    A list of content blocks (dicts with "type" and "text" keys) containing the results.
    The format varies by action:
    - list_tools: Returns tool names and usage instructions
    - get_description: Returns the tool's description
    - get_tool_schema: Returns the tool's JSON schema
    - execute_tool: Returns the tool execution results
    - spawn_tool_in_background: Returns tool_call_id and polling instructions
    - poll_tool_result: Returns status and results (if completed) or error message

Usage Workflow
--------------
**Synchronous Execution:**
1. Use `list_tools` to discover available tools
2. Use `get_tool_schema` to understand required parameters (CRITICAL: always do this before execution)
3. Use `execute_tool` to run the tool and get immediate results

**Asynchronous Execution (for long-running tools):**
1. Use `list_tools` and `get_tool_schema` as above
2. Use `spawn_tool_in_background` to start execution and receive a tool_call_id
3. Use `poll_tool_result` periodically to check status and retrieve results when complete

Important Notes
---------------
- **CRITICAL**: Never call execute_tool or spawn_tool_in_background without first 
    calling get_tool_schema to understand the required arguments. This prevents 
    malformed requests and execution errors.
- Always verify tool availability with list_tools before attempting to use a tool.
- Do not make assumptions about tool schemas; always retrieve them explicitly.
- Use get_description only when a tool name is ambiguous or unclear.
- Background tasks are tracked in hmap_call_id_to_results and cleaned up after 
    polling completes or errors.
- Polling a completed or errored task will automatically clean it up from the tracking map.

Current Loaded MCP Servers
--------------------------
{loaded_mcp_servers}
"""