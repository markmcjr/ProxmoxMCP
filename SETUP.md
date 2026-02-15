# Hardened ProxmoxMCP - Setup & Configuration

This is a security-hardened fork of [canvrno/ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP), configured as an MCP server for Claude Code.

**Fork**: [markmcjr/ProxmoxMCP](https://github.com/markmcjr/ProxmoxMCP)
**Local path**: `/home/mark/LinuxShare/scripts/proxmox-mcp`

---

## What Was Changed (and Why)

### Security Hardening

| Change | File | Why |
|--------|------|-----|
| **Removed `execute_vm_command` tool** | `server.py` | Prevents arbitrary command execution on VMs via MCP. The console code remains in `tools/console/` but is never registered as a tool. |
| **Added input validation** | `server.py` | Node names validated against `^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$`, VM IDs against `^[1-9][0-9]{0,8}$` to prevent injection. |
| **SSL verification enabled by default** | `config.example.json` | Changed `verify_ssl` from `false` to `true`. |
| **Environment variable authentication** | `config/loader.py` | Tokens passed via env vars instead of plain JSON files. Supports `PROXMOX_HOST`, `PROXMOX_TOKEN_ID`, `PROXMOX_TOKEN_SECRET`. |

### Bug Fixes (from community PRs #14 and #15)

| Change | File | Why |
|--------|------|-----|
| **Fixed Python version** | `pyproject.toml` | Changed `>=3.9` to `>=3.10` (MCP SDK requires 3.10+) |
| **Fixed MCP dependency** | `pyproject.toml` | Replaced broken `git+` URL with `mcp>=1.0.0,<1.7.0` |
| **Added `main()` entry point** | `__init__.py` | Required for `python -m proxmox_mcp` to work |
| **Added `__main__.py`** | `__main__.py` | Enables `python -m proxmox_mcp` invocation |
| **Wrapped node VM listing in try/except** | `tools/vm.py` | One offline node no longer crashes `get_vms()` |
| **Fixed test import path** | `tests/test_vm_console.py` | `vm_console` -> `console.manager` |
| **Updated test assertions** | `tests/test_server.py` | Reflects removal of `execute_vm_command`, fixes mock paths, updates env var names |

### Available MCP Tools (5 read-only tools)

| Tool | Description |
|------|-------------|
| `get_nodes` | List all cluster nodes with status, CPU, memory |
| `get_node_status` | Get detailed status for a specific node |
| `get_vms` | List all VMs across the cluster |
| `get_storage` | List storage pools with usage |
| `get_cluster_status` | Get overall cluster health |

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- A Proxmox VE server with API access
- A Proxmox API token (see "Create API Token" below)

### Step 1: Create a Read-Only Proxmox API Token

1. Log into Proxmox web UI (https://your-proxmox:8006)
2. Go to **Datacenter** -> **Permissions** -> **API Tokens**
3. Click **Add**
4. Settings:
   - **User**: `root@pam` (or any user)
   - **Token ID**: `claude-readonly`
   - **Privilege Separation**: **Yes** (checked)
5. Click **Add** - copy the token secret (shown only once!)
6. Go to **Datacenter** -> **Permissions** -> **Add** -> **API Token Permission**
   - **Path**: `/`
   - **API Token**: `root@pam!claude-readonly`
   - **Role**: `PVEAuditor` (read-only)
   - **Propagate**: Yes

Your token ID will be: `root@pam!claude-readonly`

### Step 2: Activate the Virtual Environment

The venv is already created at `/home/mark/LinuxShare/scripts/proxmox-mcp/venv/`.

```bash
# Verify it works
/home/mark/LinuxShare/scripts/proxmox-mcp/venv/bin/python -c "import proxmox_mcp; print('OK')"
```

If you need to recreate it:

```bash
cd /home/mark/LinuxShare/scripts/proxmox-mcp
python3 -m venv venv
venv/bin/pip install -e ".[dev]"
```

### Step 3: Configure Claude Code MCP Server

Add the following to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "/home/mark/LinuxShare/scripts/proxmox-mcp/venv/bin/python",
      "args": ["-m", "proxmox_mcp"],
      "env": {
        "PROXMOX_HOST": "YOUR_PROXMOX_IP",
        "PROXMOX_TOKEN_ID": "root@pam!claude-readonly",
        "PROXMOX_TOKEN_SECRET": "YOUR_TOKEN_SECRET",
        "PROXMOX_VERIFY_SSL": "false"
      }
    }
  }
}
```

**Note**: Set `PROXMOX_VERIFY_SSL` to `"false"` if using a self-signed certificate (common for home labs). For production, use `"true"` and optionally set `PROXMOX_SSL_CERT` to your CA cert path.

### Step 4: Verify

1. Restart Claude Code (or start a new session)
2. Run `/mcp` to check the server is detected
3. Ask Claude to "list my Proxmox nodes" or "show my VMs"

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROXMOX_HOST` | Yes | - | Proxmox server IP or hostname |
| `PROXMOX_TOKEN_ID` | Yes | - | Full token ID (e.g., `root@pam!tokenname`) |
| `PROXMOX_TOKEN_SECRET` | Yes | - | Token secret value |
| `PROXMOX_PORT` | No | `8006` | API port |
| `PROXMOX_VERIFY_SSL` | No | `true` | SSL certificate verification |
| `PROXMOX_SERVICE` | No | `PVE` | Service type |
| `PROXMOX_LOG_LEVEL` | No | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `PROXMOX_MCP_CONFIG` | No | - | Path to JSON config file (fallback if env vars not set) |

---

## Continuing in Another Terminal

To pick up development in a new Claude Code session:

```bash
cd /home/mark/LinuxShare/scripts/proxmox-mcp
```

Key locations:
- **Source code**: `src/proxmox_mcp/`
- **Server entry point**: `src/proxmox_mcp/server.py`
- **Config loader (env vars)**: `src/proxmox_mcp/config/loader.py`
- **MCP tool definitions**: `src/proxmox_mcp/tools/definitions.py`
- **Tests**: `tests/`
- **Venv**: `venv/bin/python`

To run tests:
```bash
venv/bin/python -m pytest tests/ -v
```

To test the server manually (will fail without Proxmox connection but confirms imports work):
```bash
PROXMOX_HOST=test PROXMOX_TOKEN_ID=test@pam!test PROXMOX_TOKEN_SECRET=test \
  venv/bin/python -m proxmox_mcp
```

---

## Files Modified (from original canvrno/ProxmoxMCP)

```
pyproject.toml                          # Fixed deps, Python version
src/proxmox_mcp/__init__.py             # Added main() entry point
src/proxmox_mcp/__main__.py             # NEW - enables python -m invocation
src/proxmox_mcp/server.py               # Removed execute_vm_command, added validation
src/proxmox_mcp/config/loader.py        # Added env var config support
src/proxmox_mcp/tools/vm.py             # Skip unreachable nodes
proxmox-config/config.example.json      # SSL verification default
tests/test_server.py                    # Updated for removed tool, fixed mocks
tests/test_vm_console.py                # Fixed import path
```
