import click 
from .mcp_engine import MCPEngine

@click.command()
@click.option("--config-file", "-c", type=click.Path(exists=True), required=True, help="Path to the MCP Router configuration file.")
@click.option("--transport", "-t", type=click.Choice(["http", "stdio"]), default="stdio", help="Transport method to use for the MCP Router.")
@click.option("--host", type=str, default=None, help="Host address for the MCP Router (only for HTTP transport).")
@click.option("--port", type=int, default=None, help="Port number for the MCP Router (only for HTTP transport).")
def main(config_file:str, transport:str, host:str, port:int):
    async def run_mcp_router():
        async with MCPEngine() as mcp_engine:
            mcp_router_config = mcp_engine.load_configs(path2json_config=config_file)
            description = await mcp_engine.start_all_mcp_servers(mcp_router_config=mcp_router_config)
            print("MCP Router is running with the following MCP servers:")
            print(description)
            mcp_engine.define_tools(description=description)
            await mcp_engine.start_engine(
                transport=transport,
                host=host,
                port=port
            )
    import asyncio
    asyncio.run(run_mcp_router()) 
