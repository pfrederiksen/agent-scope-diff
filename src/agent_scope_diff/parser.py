from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Tuple

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised when PyYAML is absent.
    yaml = None


class ParseError(ValueError):
    pass


def load_config(path: str) -> Any:
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParseError(f"could not read {path}: {exc}") from exc

    suffix = file_path.suffix.lower()
    try:
        if suffix == ".json":
            return json.loads(text)
        if suffix in {".yaml", ".yml"}:
            return _load_yaml(text)
        return _load_unknown(text)
    except (json.JSONDecodeError, YamlParseError) as exc:
        raise ParseError(f"could not parse {path}: {exc}") from exc


def _load_unknown(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _load_yaml(text)


class YamlParseError(ValueError):
    pass


def _load_yaml(text: str) -> Any:
    if yaml is not None:
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise YamlParseError(str(exc)) from exc
    return _load_simple_yaml(text)


def _load_simple_yaml(text: str) -> Any:
    lines = _preprocess_yaml(text)
    if not lines:
        return None
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise YamlParseError(f"unexpected content near line {index + 1}")
    return value


def _preprocess_yaml(text: str) -> List[Tuple[int, str]]:
    lines: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:indent]:
            raise YamlParseError("tabs are not supported by the fallback YAML parser")
        lines.append((indent, _strip_comment(raw.strip())))
    return lines


def _parse_block(lines: List[Tuple[int, str]], index: int, indent: int) -> Tuple[Any, int]:
    if index >= len(lines):
        return None, index
    current_indent, content = lines[index]
    if current_indent < indent:
        return None, index
    if current_indent != indent:
        raise YamlParseError(f"unexpected indentation near line {index + 1}")
    if content.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: List[Tuple[int, str]], index: int, indent: int) -> Tuple[dict, int]:
    mapping = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise YamlParseError(f"unexpected indentation near line {index + 1}")
        if content.startswith("- "):
            break
        key, value = _split_key_value(content, index)
        if value == "":
            if index + 1 < len(lines) and lines[index + 1][0] > indent:
                child, index = _parse_block(lines, index + 1, lines[index + 1][0])
                mapping[key] = child
            else:
                mapping[key] = None
                index += 1
        else:
            mapping[key] = _parse_scalar(value)
            index += 1
    return mapping, index


def _parse_list(lines: List[Tuple[int, str]], index: int, indent: int) -> Tuple[list, int]:
    items = []
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise YamlParseError(f"unexpected indentation near line {index + 1}")
        if not content.startswith("- "):
            break
        rest = content[2:].strip()
        if rest == "":
            child, index = _parse_block(lines, index + 1, lines[index + 1][0])
            items.append(child)
        elif ":" in rest and not rest.startswith(("'", '"')):
            key, value = _split_key_value(rest, index)
            item = {key: _parse_scalar(value) if value else None}
            index += 1
            if index < len(lines) and lines[index][0] > indent:
                child, index = _parse_mapping(lines, index, lines[index][0])
                item.update(child)
            items.append(item)
        else:
            items.append(_parse_scalar(rest))
            index += 1
    return items, index


def _split_key_value(content: str, index: int) -> Tuple[str, str]:
    if ":" not in content:
        raise YamlParseError(f"expected key/value pair near line {index + 1}")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key:
        raise YamlParseError(f"empty key near line {index + 1}")
    return key, value.strip()


def _parse_scalar(value: str) -> Any:
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _strip_comment(value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value
