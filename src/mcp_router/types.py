from enum import Enum 
from typing import List, Dict, Optional  
from pydantic import BaseModel
from mcp.types import CallToolResult

class MCPStartupConfig(BaseModel):
    command:str 
    args:list[str] = []
    env:Dict[str, str] = {}

class MCPServer(BaseModel):
    name:str 
    description:str
    timeout:float=30
    startup:MCPStartupConfig

class MCPRouterConfig(BaseModel):
    mcpServers:List[MCPServer]

class BackgroundToolCallStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

class BackgroundToolCallResult(BaseModel):
    status:BackgroundToolCallStatus
    error_message:Optional[str] = None
    results:Optional[List[CallToolResult]] = None