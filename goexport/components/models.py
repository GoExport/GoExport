"""Status and error types shared by GoExport-managed system components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComponentState(Enum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    STALE = "stale"
    ERROR = "error"
    UNSUPPORTED = "unsupported"


STATE_LABELS = {
    ComponentState.INSTALLED: "Installed",
    ComponentState.NOT_INSTALLED: "Not installed",
    ComponentState.STALE: "Stale registration",
    ComponentState.ERROR: "Registration error",
    ComponentState.UNSUPPORTED: "Unsupported",
}


class ComponentError(RuntimeError):
    """An install, repair, or uninstall operation could not be completed."""


@dataclass(frozen=True)
class ComponentStatus:
    """What GoExport knows about one component on this computer.

    ``owned`` is True only when the registration carries GoExport's ownership
    marker; GoExport repairs and removes nothing else. ``current`` is True when
    the registration launches the GoExport copy that produced this status.
    """

    id: str
    name: str
    state: ComponentState
    system: str
    scope: str
    detail: str
    owned: bool = False
    current: bool = False
    location: str | None = None
    launcher: tuple[str, ...] = ()
    registered_launcher: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return STATE_LABELS[self.state]

    @property
    def valid(self) -> bool:
        return self.state is ComponentState.INSTALLED

    @property
    def actions(self) -> tuple[str, ...]:
        """Operations that can safely be offered for this status."""
        if self.state is ComponentState.NOT_INSTALLED:
            return ("install",)
        if self.state in (ComponentState.INSTALLED, ComponentState.STALE):
            return ("repair", "uninstall")
        if self.state is ComponentState.ERROR and self.owned:
            return ("repair", "uninstall")
        return ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "label": self.label,
            "valid": self.valid,
            "system": self.system,
            "scope": self.scope,
            "detail": self.detail,
            "owned": self.owned,
            "current": self.current,
            "location": self.location,
            "launcher": list(self.launcher),
            "registered_launcher": list(self.registered_launcher),
            "problems": list(self.problems),
            "notes": list(self.notes),
            "actions": list(self.actions),
        }


@dataclass(frozen=True)
class Registration:
    """A platform backend's raw view of the URL scheme registration.

    ``exists`` means something is registered for the scheme at the location
    GoExport manages; ``owned`` means it carries GoExport's marker.
    ``handler_ok`` is False when the operating system would not route the
    scheme to this registration (for example another default handler).
    """

    exists: bool
    location: str
    owned: bool = False
    launcher: tuple[str, ...] = ()
    command: str | None = None
    handler_ok: bool = True
    problems: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
