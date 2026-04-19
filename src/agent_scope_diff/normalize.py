from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Set, Tuple
from urllib.parse import urlparse

from .models import Snapshot


TOOL_KEYS = {
    "tool",
    "tools",
    "allowed_tools",
    "allowedTools",
    "enabled_tools",
    "enabledTools",
    "toolDefinitions",
    "tool_definitions",
}
PERMISSION_KEYS = {
    "permission",
    "permissions",
    "scope",
    "scopes",
    "allowed_scopes",
    "allowedScopes",
    "capabilities",
}
MODEL_KEYS = {
    "model",
    "model_name",
    "modelName",
    "default_model",
    "defaultModel",
}
ENV_KEYS = {
    "env",
    "environment",
    "environment_variables",
    "environmentVariables",
    "env_vars",
    "envVars",
    "secrets",
    "secret_refs",
    "secretRefs",
}
MCP_KEYS = {"mcpServers", "mcp_servers", "servers"}
IDENTITY_KEYS = {
    "identity",
    "auth",
    "authentication",
    "provider",
    "providers",
    "service_account",
    "serviceAccount",
    "credentials",
    "oauth",
}
ENDPOINT_KEYS = {
    "url",
    "uri",
    "endpoint",
    "host",
    "base_url",
    "baseUrl",
    "command",
}
SENSITIVE_KEY_RE = re.compile(r"(secret|token|password|credential|private[_-]?key|api[_-]?key)", re.I)
ENV_REF_RE = re.compile(r"(?:\$\{?([A-Z_][A-Z0-9_]{2,})\}?)")


NORMALIZER_NAMES = ("auto", "generic", "openai-agents", "claude-desktop", "langgraph")


def normalize_config(data: Any, normalizer: str = "auto") -> Snapshot:
    if normalizer not in NORMALIZER_NAMES:
        raise ValueError(f"unknown normalizer: {normalizer}")
    snapshot = Snapshot()
    if normalizer in {"auto", "openai-agents"}:
        _apply_openai_agents(data, snapshot)
    if normalizer in {"auto", "claude-desktop"}:
        _apply_claude_desktop(data, snapshot)
    if normalizer in {"auto", "langgraph"}:
        _apply_langgraph(data, snapshot)
    _walk(data, (), snapshot)
    snapshot.tools = {_clean_name(item) for item in snapshot.tools if _clean_name(item)}
    snapshot.env_vars = {_clean_name(item) for item in snapshot.env_vars if _clean_name(item)}
    snapshot.models = {_clean_name(item) for item in snapshot.models if _clean_name(item)}
    snapshot.permissions = {
        _clean_name(group): _clean_name(level)
        for group, level in snapshot.permissions.items()
        if _clean_name(group) and _clean_name(level)
    }
    return snapshot


def list_normalizers() -> Tuple[str, ...]:
    return NORMALIZER_NAMES


def _apply_openai_agents(data: Any, snapshot: Snapshot) -> None:
    if not isinstance(data, MutableMapping):
        return
    agents = data.get("agents")
    if not isinstance(agents, list):
        return
    for agent in agents:
        if not isinstance(agent, MutableMapping):
            continue
        snapshot.models.update(_extract_names(agent.get("model")))
        snapshot.tools.update(_extract_names(agent.get("tools", [])))
        snapshot.tools.update(_extract_names(agent.get("handoffs", [])))
        for name in _extract_names(agent.get("instructions", [])):
            if name.startswith("$"):
                snapshot.env_vars.update(ENV_REF_RE.findall(name))


def _apply_claude_desktop(data: Any, snapshot: Snapshot) -> None:
    if isinstance(data, MutableMapping) and "mcpServers" in data:
        snapshot.mcp_servers.update(_extract_mcp_servers(data["mcpServers"]))


def _apply_langgraph(data: Any, snapshot: Snapshot) -> None:
    if not isinstance(data, MutableMapping):
        return
    graph = data.get("graph") or data.get("langgraph")
    if not isinstance(graph, MutableMapping):
        return
    nodes = graph.get("nodes")
    if isinstance(nodes, MutableMapping):
        for node_name, node in nodes.items():
            if isinstance(node, MutableMapping):
                snapshot.tools.update(_extract_names(node.get("tools", [])))
                snapshot.models.update(_extract_names(node.get("model")))
            elif isinstance(node, str):
                snapshot.tools.add(f"langgraph.node.{node_name}")


def _walk(value: Any, path: Tuple[str, ...], snapshot: Snapshot) -> None:
    if isinstance(value, MutableMapping):
        _collect_mapping(value, path, snapshot)
        for key, child in value.items():
            _walk(child, path + (str(key),), snapshot)
        return

    if isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, path + (str(index),), snapshot)
        return

    if isinstance(value, str):
        _collect_string_value(value, path, snapshot)


def _collect_mapping(mapping: MutableMapping[Any, Any], path: Tuple[str, ...], snapshot: Snapshot) -> None:
    for raw_key, value in mapping.items():
        key = str(raw_key)
        key_path = path + (key,)

        if key in TOOL_KEYS:
            snapshot.tools.update(_extract_names(value))
            snapshot.permissions.update(_extract_tool_permissions(value))

        if key in PERMISSION_KEYS:
            for name in _extract_names(value):
                snapshot.permissions[_permission_group(name)] = _permission_level(name)

        if key in MODEL_KEYS:
            snapshot.models.update(_extract_names(value))

        if key in ENV_KEYS:
            snapshot.env_vars.update(_extract_env_names(value))

        if key in MCP_KEYS:
            snapshot.mcp_servers.update(_extract_mcp_servers(value))

        if key in IDENTITY_KEYS:
            snapshot.identity.update(_flatten_identity(value, key_path))

        if key in ENDPOINT_KEYS and not _inside_mcp(path):
            endpoint = _stringify_endpoint(value)
            if endpoint:
                snapshot.endpoints[".".join(key_path)] = endpoint

        if isinstance(value, str):
            for env_name in ENV_REF_RE.findall(value):
                snapshot.env_vars.add(env_name)


def _collect_string_value(value: str, path: Tuple[str, ...], snapshot: Snapshot) -> None:
    last = path[-1] if path else ""
    if last in MODEL_KEYS:
        snapshot.models.add(value)
    for env_name in ENV_REF_RE.findall(value):
        snapshot.env_vars.add(env_name)


def _extract_names(value: Any) -> Set[str]:
    names: Set[str] = set()
    if value is None:
        return names
    if isinstance(value, str):
        names.add(value)
    elif isinstance(value, list):
        for item in value:
            names.update(_extract_names(item))
    elif isinstance(value, MutableMapping):
        for key, child in value.items():
            if isinstance(child, bool):
                if child:
                    names.add(str(key))
            elif isinstance(child, str):
                if str(key).lower() in {"name", "id", "tool", "scope", "permission", "model"}:
                    names.add(child)
                else:
                    names.add(str(key))
            elif isinstance(child, MutableMapping):
                if "name" in child:
                    names.add(str(child["name"]))
                else:
                    names.add(str(key))
            elif isinstance(child, list):
                names.add(str(key))
                names.update(_extract_names(child))
            else:
                names.add(str(key))
    return names


def _extract_tool_permissions(value: Any) -> Dict[str, str]:
    permissions: Dict[str, str] = {}
    if isinstance(value, MutableMapping):
        for tool_name, details in value.items():
            if isinstance(details, MutableMapping):
                for key in PERMISSION_KEYS:
                    if key in details:
                        for scope in _extract_names(details[key]):
                            permissions[_permission_group(f"{tool_name}.{scope}")] = _permission_level(scope)
            elif isinstance(details, str):
                permissions[_permission_group(f"{tool_name}.{details}")] = _permission_level(details)
    elif isinstance(value, list):
        for item in value:
            permissions.update(_extract_tool_permissions(item))
    return permissions


def _extract_env_names(value: Any) -> Set[str]:
    names: Set[str] = set()
    if isinstance(value, str):
        names.add(value)
        names.update(ENV_REF_RE.findall(value))
    elif isinstance(value, list):
        for item in value:
            names.update(_extract_env_names(item))
    elif isinstance(value, MutableMapping):
        for key, child in value.items():
            names.add(str(key))
            if isinstance(child, str):
                names.update(ENV_REF_RE.findall(child))
            elif isinstance(child, (list, MutableMapping)):
                names.update(_extract_env_names(child))
    return names


def _extract_mcp_servers(value: Any) -> Dict[str, Dict[str, Any]]:
    servers: Dict[str, Dict[str, Any]] = {}
    if isinstance(value, MutableMapping):
        for name, details in value.items():
            server_name = str(name)
            if isinstance(details, MutableMapping):
                servers[server_name] = {
                    "endpoint": _first_endpoint(details),
                    "tools": sorted(_extract_names(details.get("tools", []))),
                }
            else:
                servers[server_name] = {"endpoint": _stringify_endpoint(details), "tools": []}
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, MutableMapping):
                name = str(item.get("name") or item.get("id") or item.get("server") or _first_endpoint(item) or "unknown")
                servers[name] = {
                    "endpoint": _first_endpoint(item),
                    "tools": sorted(_extract_names(item.get("tools", []))),
                }
    return servers


def _flatten_identity(value: Any, path: Tuple[str, ...]) -> Dict[str, str]:
    flattened: Dict[str, str] = {}
    if isinstance(value, MutableMapping):
        for key, child in value.items():
            child_path = path + (str(key),)
            if isinstance(child, (MutableMapping, list)):
                flattened.update(_flatten_identity(child, child_path))
            elif child is not None:
                flattened[".".join(child_path)] = _mask_if_sensitive(str(key), str(child))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            flattened.update(_flatten_identity(child, path + (str(index),)))
    elif value is not None:
        flattened[".".join(path)] = str(value)
    return flattened


def _first_endpoint(mapping: MutableMapping[Any, Any]) -> Optional[str]:
    for key in ENDPOINT_KEYS:
        if key in mapping:
            endpoint = _stringify_endpoint(mapping[key])
            if endpoint:
                return endpoint
    return None


def _inside_mcp(path: Tuple[str, ...]) -> bool:
    return any(part in MCP_KEYS for part in path)


def _stringify_endpoint(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return _host_or_value(cleaned)
    return None


def _host_or_value(value: str) -> str:
    parsed = urlparse(value)
    if parsed.netloc:
        return parsed.netloc
    return value


def _mask_if_sensitive(key: str, value: str) -> str:
    if SENSITIVE_KEY_RE.search(key):
        return "<redacted>"
    return value


def _clean_name(value: str) -> str:
    return str(value).strip()


def _permission_group(permission: str) -> str:
    parts = _clean_name(permission).replace(":", ".").split(".")
    if len(parts) <= 1:
        return parts[0]
    if _permission_rank(parts[-1]) > 0:
        return ".".join(parts[:-1])
    return ".".join(parts)


def _permission_level(permission: str) -> str:
    cleaned = _clean_name(permission)
    parts = cleaned.replace(":", ".").split(".")
    candidate = parts[-1] if parts else cleaned
    if "_" in candidate and candidate.endswith("write"):
        return "write"
    rank = _permission_rank(candidate)
    if rank >= 3:
        return "admin"
    if rank == 2:
        return "write"
    if rank == 1:
        return "read"
    return candidate or "unknown"


def permission_rank(level: str) -> int:
    return _permission_rank(level)


def _permission_rank(level: str) -> int:
    normalized = level.lower().replace("-", "_")
    if normalized in {"read", "reader", "readonly", "read_only", "view", "viewer", "list"}:
        return 1
    if normalized in {
        "write",
        "writer",
        "read_write",
        "readwrite",
        "send",
        "create",
        "update",
        "edit",
        "modify",
        "manage",
    }:
        return 2
    if normalized in {"delete", "destroy", "admin", "administrator", "owner", "full", "root", "*"}:
        return 3
    return 0
