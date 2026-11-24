"""Parse and validate goexport:// URLs into V2 recording requests.

Every URL is untrusted: it can come from any web page or application. Only a
fixed set of parameters is accepted, each is validated, and a request becomes
ordinary ``record`` command arguments. URLs can never choose output paths,
executables, plugins, or arbitrary command-line options.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from goexport import config

SCHEME = "goexport"
MAX_URL_LENGTH = 4096
MAX_VALUE_LENGTH = 2048
MAX_DIMENSION = 16384

ACTIONS = ("record",)
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
RESOLUTION = re.compile(r"([1-9][0-9]{0,4})x([1-9][0-9]{0,4})")
BOOLEANS = {
    "true": True,
    "1": True,
    "yes": True,
    "false": False,
    "0": False,
    "no": False,
}
ENDPOINTS = {
    "url": "--url",
    "api_url": "--api-url",
    "swf_url": "--swf-url",
    "store_path": "--store-path",
    "client_theme_path": "--client-theme-path",
}
PARAMETERS = (
    "movie_id",
    "user_id",
    "format",
    "resolution",
    "wide",
    "outro",
    *ENDPOINTS,
)
# Parameters of the GoExport V1 URL format (goexport://<service>?video_id=...).
V1_PARAMETERS = {"video_id", "aspect_ratio", "no_input", "use_outro", "service"}


class RequestError(ValueError):
    """A goexport:// URL was malformed or asked for something unsupported."""


@dataclass(frozen=True)
class RecordRequest:
    movie_id: str
    user_id: str | None = None
    format: str | None = None
    resolution: tuple[int, int] | None = None
    wide: bool | None = None
    outro: bool | None = None
    endpoints: tuple[tuple[str, str], ...] = ()

    action = "record"

    def output_path(self, directory: Path, timestamp: str) -> Path:
        """The output for this request: a fixed folder and a safe name."""
        return directory / f"{self.movie_id}-{timestamp}"

    def record_arguments(self, output: Path) -> list[str]:
        """``record`` arguments; every value uses ``--option=value`` form."""
        arguments = [f"--movie-id={self.movie_id}", f"--output={output}"]
        if self.user_id is not None:
            arguments.append(f"--user-id={self.user_id}")
        if self.format is not None:
            arguments.append(f"--format={self.format}")
        if self.resolution is not None:
            arguments.append(f"--resolution={self.resolution[0]}x{self.resolution[1]}")
        if self.wide is False:
            arguments.append("--no-wide")
        if self.outro is False:
            arguments.append("--no-outro")
        for name, value in self.endpoints:
            arguments.append(f"{ENDPOINTS[name]}={value}")
        return arguments

    def summary(self) -> list[tuple[str, str]]:
        rows = [("Action", "Record (screen recording)"), ("Movie ID", self.movie_id)]
        if self.user_id is not None:
            rows.append(("User ID", self.user_id))
        if self.format is not None:
            rows.append(("Format", self.format))
        if self.resolution is not None:
            rows.append(("Resolution", f"{self.resolution[0]}x{self.resolution[1]}"))
        if self.wide is not None:
            rows.append(("Widescreen", "yes" if self.wide else "no"))
        if self.outro is not None:
            rows.append(("Outro", "yes" if self.outro else "no"))
        labels = {
            "url": "Server URL",
            "api_url": "API URL",
            "swf_url": "SWF URL",
            "store_path": "Store path",
            "client_theme_path": "Theme path",
        }
        rows.extend((labels[name], value) for name, value in self.endpoints)
        return rows


def parse_request(raw: str) -> RecordRequest:
    """Validate a goexport:// URL and return the request it describes."""
    if len(raw) > MAX_URL_LENGTH:
        raise RequestError(f"The URL is longer than {MAX_URL_LENGTH} characters.")
    if any(ord(character) <= 0x20 or ord(character) == 0x7F for character in raw):
        raise RequestError("The URL contains spaces or control characters.")
    try:
        parts = urlsplit(raw)
    except ValueError as error:
        raise RequestError(f"The URL is malformed: {error}") from error
    if parts.scheme.lower() != SCHEME:
        raise RequestError(f"Expected a {SCHEME}:// URL.")
    if parts.fragment:
        raise RequestError("goexport:// URLs cannot contain a '#' fragment.")
    if parts.path not in ("", "/"):
        raise RequestError(f"Unexpected path in the URL: {parts.path!r}.")

    try:
        pairs = parse_qsl(
            parts.query,
            keep_blank_values=True,
            strict_parsing=bool(parts.query),
            max_num_fields=len(PARAMETERS) + len(V1_PARAMETERS),
        )
    except ValueError as error:
        raise RequestError(f"The URL's query string is malformed: {error}") from error
    values: dict[str, str] = {}
    for name, value in pairs:
        if name in values:
            raise RequestError(f"The parameter '{name}' is repeated.")
        values[name] = value

    action = parts.netloc.lower()
    if action not in ACTIONS:
        if V1_PARAMETERS & values.keys():
            raise RequestError(
                "This is a GoExport V1 URL (goexport://<service>?video_id=...). "
                "GoExport V2 does not accept V1 URLs; use "
                "goexport://record?movie_id=<id>&url=<server> instead."
            )
        if action == "export":
            raise RequestError(
                "Frame-by-frame export needs local asset folders and cannot be "
                "started from a URL. Use goexport://record?movie_id=<id>."
            )
        if not action:
            raise RequestError(
                "The URL does not name an action. Use goexport://record?movie_id=<id>."
            )
        raise RequestError(
            f"Unsupported action '{parts.netloc}'. Supported: {', '.join(ACTIONS)}."
        )

    unknown = sorted(values.keys() - set(PARAMETERS))
    if unknown:
        raise RequestError(
            "Unsupported parameter(s): "
            + ", ".join(unknown)
            + ". Supported: "
            + ", ".join(PARAMETERS)
            + "."
        )
    for name, value in values.items():
        if len(value) > MAX_VALUE_LENGTH:
            raise RequestError(f"The '{name}' value is too long.")
        if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
            raise RequestError(f"The '{name}' value contains control characters.")

    movie_id = values.get("movie_id")
    if not movie_id:
        raise RequestError("The 'movie_id' parameter is required.")
    _identifier("movie_id", movie_id)
    user_id = values.get("user_id")
    if user_id is not None:
        _identifier("user_id", user_id)

    video_format = values.get("format")
    if video_format is not None and video_format not in config.SUPPORTED_FORMATS:
        raise RequestError(
            f"Unsupported format '{video_format}'. Supported: "
            + ", ".join(sorted(config.SUPPORTED_FORMATS))
            + "."
        )

    return RecordRequest(
        movie_id=movie_id,
        user_id=user_id,
        format=video_format,
        resolution=_resolution(values.get("resolution")),
        wide=_boolean("wide", values.get("wide")),
        outro=_boolean("outro", values.get("outro")),
        endpoints=tuple(
            (name, _endpoint(name, values[name]))
            for name in ENDPOINTS
            if name in values
        ),
    )


def _identifier(name: str, value: str) -> None:
    if not IDENTIFIER.fullmatch(value):
        raise RequestError(
            f"'{name}' must be 1-128 letters, digits, '.', '_' or '-' and start "
            "with a letter or digit."
        )


def _resolution(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    match = RESOLUTION.fullmatch(value.lower())
    if match is None:
        raise RequestError("'resolution' must look like 1280x720.")
    width, height = int(match[1]), int(match[2])
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise RequestError(f"'resolution' cannot exceed {MAX_DIMENSION} pixels.")
    return width, height


def _boolean(name: str, value: str | None) -> bool | None:
    if value is None:
        return None
    try:
        return BOOLEANS[value.lower()]
    except KeyError:
        raise RequestError(
            f"'{name}' must be true or false (also accepted: 1, 0, yes, no)."
        ) from None


def _endpoint(name: str, value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError as error:
        raise RequestError(f"'{name}' is not a valid URL: {error}") from error
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise RequestError(f"'{name}' must be an http:// or https:// URL.")
    if " " in value:
        raise RequestError(f"'{name}' cannot contain spaces.")
    return value
