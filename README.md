# MCP Router

A Python package for orchestrating multiple MCP (Model Context Protocol) servers through a unified interface.

## Overview

MCP Router provides a single entry point for interacting with multiple MCP servers, enabling developers to:

- **Orchestrate multiple MCP servers** through a unified interface
- **Execute tools synchronously** for quick operations
- **Run tools in the background** for long-running tasks
- **Monitor and poll** background task execution
- **Discover and inspect** available tools across connected servers

## Features

- **Multi-server orchestration**: Connect and manage multiple MCP servers simultaneously
- **Flexible transport**: Support for both HTTP and stdio transport methods
- **Async/sync execution**: Choose between immediate execution or background processing
- **Schema inspection**: Always validate tool schemas before execution
- **Comprehensive logging**: Built-in logging for debugging and monitoring
- **Error handling**: Robust timeout and error management for background tasks

## Installation

```bash
pip install mcp-router
```

## Quick Start

### Basic Usage

```python
from mcp_router import MCPEngine
import asyncio

async def main():
    async with MCPEngine() as engine:
        # Load configuration
        config = engine.load_configs("config.json")

        # Start all MCP servers
        description = await engine.start_all_mcp_servers(config)

        # Define and start the router
        engine.define_tools(description)
        await engine.start_engine(transport="stdio")

asyncio.run(main())
```

### Command Line Interface

```bash
# Start with stdio transport
mcp-router -c config.json -t stdio

# Start with HTTP transport
mcp-router -c config.json -t http --host localhost --port 8080
```

## Configuration

Create a JSON configuration file to define your MCP servers:

```json
{
    "mcpServers": [
        {
            "name": "github",
            "description": "GitHub integration server",
            "timeout": 30,
            "startup": {
                "command": "npx",
                "args": ["-y", "@github/mcp-server@latest"],
                "env": {
                    "GITHUB_TOKEN": "your-token"
                }
            }
        }
    ]
}
```

## API Reference

### MCPEngine

The main class for orchestrating MCP servers.

#### Methods

- `load_configs(path2json_config: str)` - Load server configuration
- `start_all_mcp_servers(config: MCPRouterConfig)` - Initialize all servers
- `define_tools(description: str)` - Set up routing tools
- `start_engine(transport: str, host: str, port: int)` - Start the router

### Router Actions

- **list_tools**: Discover available tools on a server
- **get_tool_schema**: Get tool parameter requirements
- **execute_tool**: Run tool synchronously
- **spawn_tool_in_background**: Start async execution
- **poll_tool_result**: Check background task status

## Development

### Requirements

- Python >= 3.12
- Dependencies listed in `pyproject.toml`

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd mcp_router

# Install in development mode
pip install -e .

# Run tests
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.