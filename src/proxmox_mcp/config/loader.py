"""
Configuration loading utilities for the Proxmox MCP server.

This module handles loading and validation of server configuration:
- Environment variable configuration (preferred)
- JSON configuration file loading (fallback)
- Configuration validation using Pydantic models
- Error handling for invalid configurations

Environment variables take precedence over config file values.
"""
import json
import os
from typing import Optional
from .models import Config


def _load_from_env() -> Optional[Config]:
    """Attempt to build configuration from environment variables.

    Supported variables:
        PROXMOX_HOST          - Proxmox host address (required)
        PROXMOX_PORT          - API port (default: 8006)
        PROXMOX_TOKEN_ID      - Full token ID e.g. 'user@pve!tokenname' (required)
        PROXMOX_TOKEN_SECRET  - Token secret value (required)
        PROXMOX_VERIFY_SSL    - 'true'/'false' (default: true)
        PROXMOX_SSL_CERT      - Path to custom CA certificate
        PROXMOX_SERVICE       - Service type (default: PVE)
        PROXMOX_LOG_LEVEL     - Log level (default: INFO)

    Returns:
        Config if all required env vars are present, None otherwise.
    """
    host = os.getenv("PROXMOX_HOST")
    token_id = os.getenv("PROXMOX_TOKEN_ID")
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET")

    if not host or not token_id or not token_secret:
        return None

    # Parse token_id: "user@realm!tokenname" -> user="user@realm", token_name="tokenname"
    if "!" in token_id:
        user, token_name = token_id.rsplit("!", 1)
    else:
        # Fallback: use PROXMOX_USER env var or default
        user = os.getenv("PROXMOX_USER", "root@pam")
        token_name = token_id

    verify_ssl_str = os.getenv("PROXMOX_VERIFY_SSL", "true").lower()
    verify_ssl = verify_ssl_str not in ("false", "0", "no")

    return Config(
        proxmox={
            "host": host,
            "port": int(os.getenv("PROXMOX_PORT", "8006")),
            "verify_ssl": verify_ssl,
            "service": os.getenv("PROXMOX_SERVICE", "PVE"),
        },
        auth={
            "user": user,
            "token_name": token_name,
            "token_value": token_secret,
        },
        logging={
            "level": os.getenv("PROXMOX_LOG_LEVEL", "INFO"),
        },
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and validate configuration.

    Priority:
    1. Environment variables (PROXMOX_HOST, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET)
    2. JSON config file (path from config_path arg or PROXMOX_MCP_CONFIG env var)

    Args:
        config_path: Optional path to JSON configuration file.

    Returns:
        Validated Config object.

    Raises:
        ValueError: If no valid configuration source is found.
    """
    # Try environment variables first
    env_config = _load_from_env()
    if env_config is not None:
        return env_config

    # Fall back to config file
    config_path = config_path or os.getenv("PROXMOX_MCP_CONFIG")
    if not config_path:
        raise ValueError(
            "No configuration found. Set PROXMOX_HOST + PROXMOX_TOKEN_ID + "
            "PROXMOX_TOKEN_SECRET environment variables, or provide a config file "
            "via PROXMOX_MCP_CONFIG."
        )

    try:
        with open(config_path) as f:
            config_data = json.load(f)
            if not config_data.get('proxmox', {}).get('host'):
                raise ValueError("Proxmox host cannot be empty")
            return Config(**config_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load config: {e}")
