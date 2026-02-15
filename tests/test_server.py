"""
Tests for the Proxmox MCP server.
"""

import os
import json
import pytest
from unittest.mock import patch

from mcp.server.fastmcp.exceptions import ToolError
from proxmox_mcp.server import ProxmoxMCPServer

@pytest.fixture
def mock_env_vars():
    """Fixture to set up test environment variables."""
    env_vars = {
        "PROXMOX_HOST": "test.proxmox.com",
        "PROXMOX_TOKEN_ID": "test@pve!test_token",
        "PROXMOX_TOKEN_SECRET": "test_value",
        "PROXMOX_LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def mock_proxmox():
    """Fixture to mock ProxmoxAPI."""
    with patch("proxmox_mcp.core.proxmox.ProxmoxAPI") as mock:
        mock.return_value.version.get.return_value = {"version": "8.0"}
        mock.return_value.nodes.get.return_value = [
            {"node": "node1", "status": "online"},
            {"node": "node2", "status": "online"}
        ]
        yield mock

@pytest.fixture
def server(mock_env_vars, mock_proxmox):
    """Fixture to create a ProxmoxMCPServer instance."""
    return ProxmoxMCPServer()

def test_server_initialization(server, mock_proxmox):
    """Test server initialization with environment variables."""
    assert server.config.proxmox.host == "test.proxmox.com"
    assert server.config.auth.user == "test@pve"
    assert server.config.auth.token_name == "test_token"
    assert server.config.auth.token_value == "test_value"
    assert server.config.logging.level == "DEBUG"

@pytest.mark.asyncio
async def test_list_tools(server):
    """Test listing available tools."""
    tools = await server.mcp.list_tools()

    assert len(tools) > 0
    tool_names = [tool.name for tool in tools]
    assert "get_nodes" in tool_names
    assert "get_vms" in tool_names
    assert "get_storage" in tool_names
    assert "get_cluster_status" in tool_names
    assert "execute_vm_command" not in tool_names  # Intentionally removed for security

@pytest.mark.asyncio
async def test_get_nodes(server, mock_proxmox):
    """Test get_nodes tool."""
    mock_proxmox.return_value.nodes.get.return_value = [
        {"node": "node1", "status": "online"},
        {"node": "node2", "status": "online"}
    ]
    response = await server.mcp.call_tool("get_nodes", {})
    result = json.loads(response[0].text)

    assert len(result) == 2
    assert result[0]["node"] == "node1"
    assert result[1]["node"] == "node2"

@pytest.mark.asyncio
async def test_get_node_status_missing_parameter(server):
    """Test get_node_status tool with missing parameter."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("get_node_status", {})

@pytest.mark.asyncio
async def test_get_node_status(server, mock_proxmox):
    """Test get_node_status tool with valid parameter."""
    mock_proxmox.return_value.nodes.return_value.status.get.return_value = {
        "status": "running",
        "uptime": 123456
    }

    response = await server.mcp.call_tool("get_node_status", {"node": "node1"})
    result = json.loads(response[0].text)
    assert result["status"] == "running"
    assert result["uptime"] == 123456

@pytest.mark.asyncio
async def test_get_vms(server, mock_proxmox):
    """Test get_vms tool."""
    mock_proxmox.return_value.nodes.get.return_value = [{"node": "node1", "status": "online"}]
    mock_proxmox.return_value.nodes.return_value.qemu.get.return_value = [
        {"vmid": "100", "name": "vm1", "status": "running"},
        {"vmid": "101", "name": "vm2", "status": "stopped"}
    ]

    response = await server.mcp.call_tool("get_vms", {})
    result = json.loads(response[0].text)
    assert len(result) > 0
    assert result[0]["name"] == "vm1"
    assert result[1]["name"] == "vm2"

@pytest.mark.asyncio
async def test_get_storage(server, mock_proxmox):
    """Test get_storage tool."""
    mock_proxmox.return_value.storage.get.return_value = [
        {"storage": "local", "type": "dir"},
        {"storage": "ceph", "type": "rbd"}
    ]

    response = await server.mcp.call_tool("get_storage", {})
    result = json.loads(response[0].text)
    assert len(result) == 2
    assert result[0]["storage"] == "local"
    assert result[1]["storage"] == "ceph"

@pytest.mark.asyncio
async def test_get_cluster_status(server, mock_proxmox):
    """Test get_cluster_status tool."""
    mock_proxmox.return_value.cluster.status.get.return_value = {
        "quorate": True,
        "nodes": 2
    }

    response = await server.mcp.call_tool("get_cluster_status", {})
    result = json.loads(response[0].text)
    assert result["quorate"] is True
    assert result["nodes"] == 2

@pytest.mark.asyncio
async def test_execute_vm_command_removed(server):
    """Verify execute_vm_command is NOT available (security hardening)."""
    tools = await server.mcp.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "execute_vm_command" not in tool_names
