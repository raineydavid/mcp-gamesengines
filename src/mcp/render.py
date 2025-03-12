from mcp.server.fastmcp import FastMCP, Context
import socket
import json
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@dataclass
class PlatformConnection:
    host: str
    port: int
    sock: socket.socket = None

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logging.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logging.error(f"Connection error: {e}")
            return False

    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            logging.info(f"Disconnected from {self.host}:{self.port}")

    def send_command(self, command_type, params=None):
        command = json.dumps({"type": command_type, "params": params or {}})
        try:
            self.sock.sendall(command.encode('utf-8'))
            response = self.sock.recv(8192)
            return json.loads(response.decode('utf-8'))
        except Exception as e:
            logging.error(f"Error sending command: {e}")
            return {"status": "error", "message": str(e)}

# Load platform connections from external JSON or environment (placeholder)
PLATFORM_CONNECTIONS: Dict[str, PlatformConnection] = {}

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    try:
        for platform, conn in PLATFORM_CONNECTIONS.items():
            if not conn.connect():
                logging.warning(f"Could not connect to {platform} at startup")
        yield {}
    finally:
        for conn in PLATFORM_CONNECTIONS.values():
            conn.disconnect()

mcp = FastMCP(
    "MultiPlatformMCP",
    description="Integration with various 3D platforms via Model Context Protocol",
    lifespan=server_lifespan
)

def get_platform_connection(platform_name: str):
    conn = PLATFORM_CONNECTIONS.get(platform_name)
    if conn is None or not conn.connect():
        raise ConnectionError(f"Unable to connect to {platform_name}")
    return conn

@mcp.tool()
def get_platform_info(ctx: Context, platform: str) -> Dict[str, Any]:
    """Get general information from the specified platform."""
    conn = get_platform_connection(platform)
    return conn.send_command("get_info")

@mcp.tool()
def create_object(ctx: Context, platform: str, object_type: str, location: list = None):
    """Create an object in the specified platform."""
    conn = get_platform_connection(platform)
    params = {"type": object_type, "location": location or [0,0,0]}
    return conn.send_command("create_object", params)

@mcp.tool()
def modify_object(ctx: Context, platform: str, object_name: str, properties: Dict[str, Any]):
    """Modify properties of an existing object on the specified platform."""
    conn = get_platform_connection(platform)
    params = {"name": object_name, **properties}
    return conn.send_command("modify_object", params)

@mcp.tool()
def delete_object(ctx: Context, platform: str, object_name: str):
    """Delete an object from the specified platform."""
    conn = get_platform_connection(platform)
    return conn.send_command("delete_object", {"name": object_name})

def main():
    mcp.run()

if __name__ == "__main__":
    main()
