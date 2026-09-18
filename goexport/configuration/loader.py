"""Read and validate the optional user-editable GoExport TOML file."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when the external GoExport configuration is invalid."""


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    values = data.get(name, {})
    if not isinstance(values, dict):
        raise ConfigurationError(f"[{name}] must be a TOML table")
    return values


def _string(values: dict[str, Any], name: str, setting: str) -> str | None:
    if name not in values:
        return None
    value = values[name]
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{setting} must be a non-empty string")
    return value


def _positive_integer(values: dict[str, Any], name: str, setting: str) -> int | None:
    if name not in values:
        return None
    value = values[name]
    if type(value) is not int or value <= 0:
        raise ConfigurationError(f"{setting} must be a positive integer")
    return value


def _boolean(values: dict[str, Any], name: str, setting: str) -> bool | None:
    if name not in values:
        return None
    value = values[name]
    if type(value) is not bool:
        raise ConfigurationError(f"{setting} must be a boolean")
    return value


def _path(
    values: dict[str, Any], name: str, setting: str, base_dir: Path
) -> Path | None:
    value = _string(values, name, setting)
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _add(result: dict[str, Any], name: str, value: Any) -> None:
    if value is not None:
        result[name] = value


def load_overrides(
    path: Path, base_dir: Path, supported_formats: set[str]
) -> dict[str, Any]:
    """Load validated effective-value overrides from an optional TOML file."""
    if not path.is_file():
        return {}

    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(f"Invalid TOML in {path}: {error}") from error
    except OSError as error:
        raise ConfigurationError(
            f"Could not read configuration file {path}: {error}"
        ) from error

    video = _section(data, "video")
    wrapper = _section(data, "wrapper")
    paths = _section(data, "paths")
    flash = _section(data, "flash")
    result: dict[str, Any] = {}

    output_format = _string(video, "format", "video.format")
    if output_format is not None and output_format not in supported_formats:
        supported = ", ".join(sorted(supported_formats))
        raise ConfigurationError(
            f"video.format must be one of {supported}; got '{output_format}'"
        )
    _add(result, "OUTPUT_FORMAT", output_format)
    _add(result, "IS_WIDE", _boolean(video, "wide", "video.wide"))
    _add(result, "WIDTH", _positive_integer(video, "width", "video.width"))
    _add(result, "HEIGHT", _positive_integer(video, "height", "video.height"))
    _add(result, "FPS", _positive_integer(video, "fps", "video.fps"))

    for key, name in (
        ("URL", "url"),
        ("API_URL", "api_url"),
        ("SWF_URL", "swf_url"),
        ("STORE_PATH", "store_path"),
        ("CLIENT_THEME_PATH", "client_theme_path"),
    ):
        _add(result, key, _string(wrapper, name, f"wrapper.{name}"))

    for key, name in (
        ("CHROME_PATH", "chrome"),
        ("CHROMEDRIVER_PATH", "chromedriver"),
        ("FFMPEG_PATH", "ffmpeg"),
    ):
        _add(result, key, _path(paths, name, f"paths.{name}", base_dir))

    _add(
        result,
        "FLASH_PLUGIN_PATH",
        _path(flash, "plugin_path", "flash.plugin_path", base_dir),
    )
    _add(
        result,
        "FLASH_PLUGIN_VERSION",
        _string(flash, "plugin_version", "flash.plugin_version"),
    )
    return result
