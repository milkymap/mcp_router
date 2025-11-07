import json 
import yaml
import asyncio 

from uuid import uuid4

from os import path 
from typing import Optional, List, Dict, Self 
from contextlib import AsyncExitStack

from mcp import ClientSession, stdio_client, StdioServerParameters
from mcp.types import ListToolsResult, CallToolResult

from fastmcp import FastMCP
from fastmcp.tools import Tool

from .log import logger 
from .types import MCPStartupConfig, MCPServer, MCPRouterConfig, BackgroundToolCallStatus, BackgroundToolCallResult 
from .instructions import SYSTEM_PROMPT, TOOL_DESCRIPTION

class MCPEngine:
    def __init__(self):
        self.hmap_mcp_server_to_session:Dict[str, ClientSession] = {}
        self.hmap_call_id_to_results:Dict[str, BackgroundToolCallResult] = {}

    async def __aenter__(self) -> Self:
        self.mutex = asyncio.Lock()
        self.stack_handler = AsyncExitStack()
        self.background_tasks:List[asyncio.Task] = []
        self.app = FastMCP(
            name="mcp-server-orchestrator",
            version="0.1.0",
            instructions=SYSTEM_PROMPT,
        )
        return self
        
    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type:
            logger.error(f"Exception occurred: {exc_value}")
            logger.exception(traceback)
        for task in self.background_tasks:
            task.cancel()
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        await self.stack_handler.aclose()
    
    def load_configs(self, path2json_config: str) -> MCPRouterConfig:
        with open(path2json_config, 'r') as f:
            data = json.load(f)
        return MCPRouterConfig(**data)
    
    def define_tools(self, description: str):
        self.app.tool(
            name="mcp_router",
            title="MCP Router Tool",
            description=TOOL_DESCRIPTION.format(loaded_mcp_servers=description),
        )(self.mcp_router)
        

    async def start_engine(self, transport:str, host:Optional[str]=None, port:Optional[int]=None):
        if transport not in ["http", "stdio"]:
            raise ValueError(f"Unsupported transport: {transport}, value must be one of ['http', 'stdio']")
        if transport == "http":
            await self.app.run_async(transport=transport, host=host, port=port)
        await self.app.run_async(transport=transport)
       
    async def start_mcp_server(self, mcp_server:MCPServer) -> Optional[ClientSession]:
        server_params = StdioServerParameters(
            command=mcp_server.startup.command,
            args=mcp_server.startup.args,
            env=mcp_server.startup.env
        )
        session:Optional[ClientSession] = None
        timeout = mcp_server.timeout
        try:
            async with asyncio.timeout(delay=timeout):
                stdio_transport = await self.stack_handler.enter_async_context(
                    stdio_client(server_params)
                )
                reader, writer = stdio_transport
                session = await self.stack_handler.enter_async_context(ClientSession(reader, writer))
                await session.initialize()
                result = await session.list_tools()
                number_of_tools = len(result.tools)
                logger.info(f"Successfully started MCP server for config {mcp_server.name} with {number_of_tools} tools (timeout: {timeout}s)")
                return session
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({timeout}s) while starting MCP server for config {mcp_server.name}")
        except Exception as e:
            logger.error(f"Failed to start MCP server for config {mcp_server.name}: {e}")  
    
    async def start_all_mcp_servers(self, mcp_router_config:MCPRouterConfig) -> str:
        mcp_info = []
        for mcp_server in mcp_router_config.mcpServers:
            logger.info(f"Starting MCP server for config {mcp_server.name}")
            session = await self.start_mcp_server(mcp_server)
            if not session:
                logger.error(f"Failed to start MCP server for config {mcp_server.name}")
                continue 
            self.hmap_mcp_server_to_session[mcp_server.name] = session
            mcp_info.append(yaml.dump({
                "name": mcp_server.name,
                "description": mcp_server.description,
                "number_of_tools": len((await session.list_tools()).tools)
            }, sort_keys=False))
        logger.info(f"Successfully started {len(self.hmap_mcp_server_to_session)} MCP servers")
        return "\n###\n".join(mcp_info) if mcp_info else "No MCP servers started successfully."

    async def run_tool(self, session:ClientSession, tool_name:str, tool_arguments:Dict) -> List[CallToolResult]:
        tool_call_result = await session.call_tool(name=tool_name, arguments=tool_arguments)
        clean_contents:List[CallToolResult] = []
        for content in tool_call_result.content:
            content_hmap = content.model_dump()
            content_hmap.pop("annotations", None)
            content_hmap.pop("meta", None)
            clean_contents.append(content_hmap)
        return clean_contents

    async def background_tool_execution(self, tool_call_id:str, session:ClientSession, tool_name:str, tool_arguments:Dict, timeout:float) -> str:
        try: 
            async with asyncio.timeout(delay=timeout):
                tool_results = await self.run_tool(session, tool_name, tool_arguments)
                self.hmap_call_id_to_results[tool_call_id] = BackgroundToolCallResult(
                    status=BackgroundToolCallStatus.COMPLETED,
                    results=tool_results
                )
        except asyncio.TimeoutError: 
            self.hmap_call_id_to_results[tool_call_id] = BackgroundToolCallResult(
                status=BackgroundToolCallStatus.TIMEOUT,
                error_message=f"Tool execution exceeded timeout of {timeout} seconds.",
                results=None
            )
        except Exception as e:
            logger.error(f"Error during background tool execution for call ID {tool_call_id}: {e}")
            self.hmap_call_id_to_results[tool_call_id] = BackgroundToolCallResult(
                status=BackgroundToolCallStatus.FAILED,
                error_message=str(e),
                results=None
            )

    async def mcp_router(
        self, 
        server_name:str, 
        action:str, 
        tool_name:Optional[str]=None, 
        tool_arguments:Optional[str]=None, 
        tool_call_id:Optional[str]=None,
        timeout:float=60
        ) -> List[Dict]:
        
        if action not in ["list_tools", "get_description", "get_tool_schema", "execute_tool", "spawn_tool_in_background", "poll_tool_result"]:
            raise ValueError(f"Unsupported action: {action}")
        
        if tool_arguments is not None:
            tool_arguments = json.loads(tool_arguments)

        session = self.hmap_mcp_server_to_session[server_name]
        match action:
            case "list_tools":
                result = await session.list_tools()
                tool_names = [{"type": "text", "text": f"tool_name: {tool.name}"} for tool in result.tools]
                remainder = [
                    {"type": "text", "text": "Do not make assumptions about tool schema, if you have found a tool you want to use, call get_tool_schema action to get its schema. This is important to avoid malformed requests."},
                    {"type": "text", "text": "Only use get_description action if you are unsure about what a tool does based on its name."}
                ]
                return tool_names + remainder
            case "get_description":
                result = await session.list_tools()
                hmap_tool_to_description = { tool.name: tool.description for tool in result.tools }
                return [
                    {
                        "type": "text", 
                        "text": hmap_tool_to_description[tool_name]
                    }
                ]
            case "get_tool_schema":
                result = await session.list_tools()
                hmap_tool_to_schema = { tool.name: tool.inputSchema for tool in result.tools }
                return [
                    {
                        "type": "text", 
                        "text": yaml.dump({
                            "name": tool_name,
                            "description": "if you feel confused, use get_description action to get the tool description",
                            "input_schema": hmap_tool_to_schema[tool_name]
                        }, sort_keys=False)
                    }
                ]
            case "execute_tool":
                tool_results = await self.run_tool(session, tool_name, tool_arguments)
                return tool_results
            case "spawn_tool_in_background":
                tool_call_id = str(uuid4())
                task = asyncio.create_task(
                    self.background_tool_execution(
                        tool_call_id=tool_call_id,
                        session=session,
                        tool_name=tool_name,
                        tool_arguments=tool_arguments,
                        timeout=timeout
                    )
                )
                self.hmap_call_id_to_results[tool_call_id] = BackgroundToolCallResult(
                    status=BackgroundToolCallStatus.PENDING,
                    results=None
                )
                self.background_tasks.append(task)
                return [
                    {
                        "type": "text",
                        "text": f"tool_call_id: {tool_call_id}"
                    },
                    {
                        "type": "text",
                        "text": "Use poll_tool_result action with the tool_call_id to check the status and retrieve results."
                    }
                ]
            case "poll_tool_result":
                result = self.hmap_call_id_to_results[tool_call_id]
                if result.status != BackgroundToolCallStatus.PENDING:
                    del self.hmap_call_id_to_results[tool_call_id]
                if result.status == BackgroundToolCallStatus.PENDING:
                    return [
                        {
                            "type": "text",
                            "text": f"Status: {result.status}. The tool execution is still in progress. Please check back later."
                        }
                    ]
                if result.status == BackgroundToolCallStatus.COMPLETED:
                    return result.results 
                return [
                        {
                            "type": "text",
                            "text": f"Status: {result.status}. Error Message: {result.error_message}"
                        }
                    ]




            
    