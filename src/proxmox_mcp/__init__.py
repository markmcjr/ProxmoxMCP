"""
Proxmox MCP Server - A Model Context Protocol server for interacting with Proxmox hypervisors.
"""

from .server import ProxmoxMCPServer

__version__ = "0.1.0"
__all__ = ["ProxmoxMCPServer"]


def main():
    """Entry point for running the MCP server."""
    import os
    import sys

    config_path = os.getenv("PROXMOX_MCP_CONFIG")
    try:
        server = ProxmoxMCPServer(config_path)
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
