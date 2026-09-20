"""Player placeholder and Flashvar handling shared by both export workflows."""

from __future__ import annotations

import argparse
import html
import re
from collections.abc import Mapping, Sequence
from urllib.parse import parse_qsl, urlencode

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_replacement(value: str) -> tuple[str, str]:
    """Parse a NAME=VALUE CLI replacement without restricting the value."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("Replacement must use the format NAME=VALUE")
    name, replacement = value.split("=", 1)
    name = name.strip()
    if not _NAME.fullmatch(name):
        raise argparse.ArgumentTypeError(
            "Replacement names must start with a letter or underscore and contain "
            "only letters, numbers, and underscores"
        )
    return name, replacement


def parse_flashvars(value: str) -> dict[str, str]:
    """Parse an ampersand-separated Flashvar string with last-value-wins semantics."""
    result: dict[str, str] = {}
    if not value:
        return result
    for entry in value.split("&"):
        if "=" not in entry:
            raise argparse.ArgumentTypeError(
                "Additional Flashvars must use the format NAME=VALUE&NAME=VALUE"
            )
    for name, item in parse_qsl(value, keep_blank_values=True, strict_parsing=True):
        if not name:
            raise argparse.ArgumentTypeError("Flashvar names cannot be empty")
        result[name] = item
    return result


def replacement_overrides(values: Sequence[tuple[str, str]] | None) -> dict[str, str]:
    """Collapse repeatable CLI replacements using last-value-wins behavior."""
    return dict(values or ())


def resolve_placeholders(
    value: object,
    runtime_values: Mapping[str, object],
    configured_replacements: Mapping[str, str],
    overrides: Mapping[str, str] | None = None,
) -> str:
    """Resolve configured aliases and runtime fields in one player-setting value."""
    definitions = dict(configured_replacements)
    definitions.update(overrides or {})
    runtime = {
        name: str(item) for name, item in runtime_values.items() if item is not None
    }

    def resolve_name(name: str, stack: tuple[str, ...]) -> str:
        if name in runtime:
            return runtime[name]
        if name in stack:
            chain = " -> ".join((*stack, name))
            raise ValueError(f"Circular player replacement: {chain}")
        if name not in definitions:
            raise ValueError(f"No value is available for player placeholder {{{name}}}")
        return expand(definitions[name], (*stack, name))

    def expand(text: str, stack: tuple[str, ...]) -> str:
        return _PLACEHOLDER.sub(lambda match: resolve_name(match.group(1), stack), text)

    return expand(str(value), ())


def build_player_replacements(
    values: Mapping[str, object],
    additional_flashvars: Mapping[str, str] | None,
    runtime_values: Mapping[str, object],
    configured_replacements: Mapping[str, str],
    overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve player values and serialize merged Flashvars for the HTML template."""
    resolved = {
        name: resolve_placeholders(
            value, runtime_values, configured_replacements, overrides
        )
        for name, value in values.items()
    }
    flashvars = {
        "autostart": "1",
        "isWide": resolved["IS_WIDE"],
        "apiserver": resolved["API_SERVER"],
        "storePath": resolved["STORE_PATH"],
        "clientThemePath": resolved["CLIENT_THEME_PATH"],
        "movieId": resolved["MOVIE_ID"],
        "isVideoRecord": "1",
        "playerWidth": resolved["PLAYER_WIDTH"],
        "playerHeight": resolved["PLAYER_HEIGHT"],
    }
    for name, value in (additional_flashvars or {}).items():
        resolved_name = resolve_placeholders(
            name, runtime_values, configured_replacements, overrides
        )
        flashvars[resolved_name] = resolve_placeholders(
            value, runtime_values, configured_replacements, overrides
        )
    resolved["FLASHVARS"] = html.escape(urlencode(flashvars), quote=True)
    return resolved
