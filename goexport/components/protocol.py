"""The goexport:// URL protocol as a GoExport-managed component.

This module is the only place that decides what a registration's state is and
which changes are allowed. The CLI commands call it directly; the GUI reaches
it by running those commands with ``--json``.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from goexport.components.launcher import current_launcher
from goexport.components.models import (
    ComponentError,
    ComponentState,
    ComponentStatus,
    Registration,
)

COMPONENT_ID = "protocol"
COMPONENT_NAME = "GoExport URL Protocol"


class ProtocolBackend(Protocol):
    system: str
    scope: str

    def inspect(self) -> Registration: ...

    def install(self, launcher: tuple[str, ...]) -> None: ...

    def uninstall(self) -> None: ...


def default_backend(system: str | None = None) -> ProtocolBackend | None:
    """Return this operating system's backend, or None when unsupported."""
    system = system or platform.system()
    if system == "Windows":
        from goexport.components.platforms.windows import WindowsProtocolBackend

        return WindowsProtocolBackend()
    if system == "Linux":
        from goexport.components.platforms.linux import LinuxProtocolBackend

        return LinuxProtocolBackend()
    if system == "Darwin":
        from goexport.components.platforms.macos import MacOSProtocolBackend

        return MacOSProtocolBackend()
    return None


@dataclass(frozen=True)
class OperationResult:
    """The outcome of install or uninstall.

    ``action`` is ``installed``, ``repaired``, ``removed`` or ``unchanged``.
    """

    action: str
    message: str
    status: ComponentStatus


class ProtocolComponent:
    id = COMPONENT_ID
    name = COMPONENT_NAME

    def __init__(
        self,
        backend: ProtocolBackend | None = None,
        launcher: tuple[str, ...] | None = None,
        system: str | None = None,
    ):
        self.system = system or platform.system()
        self.backend = backend if backend is not None else default_backend(self.system)
        self._launcher = launcher

    @property
    def launcher(self) -> tuple[str, ...]:
        if self._launcher is None:
            self._launcher = current_launcher()
        return self._launcher

    def _status(self, state: ComponentState, detail: str, **fields) -> ComponentStatus:
        return ComponentStatus(
            id=self.id,
            name=self.name,
            state=state,
            system=self.backend.system if self.backend else self.system,
            scope=self.backend.scope if self.backend else "Not available",
            detail=detail,
            **fields,
        )

    def status(self) -> ComponentStatus:
        if self.backend is None:
            return self._status(
                ComponentState.UNSUPPORTED,
                f"GoExport cannot register URL protocols on {self.system}.",
            )
        try:
            launcher = self.launcher
        except ComponentError as error:
            return self._status(ComponentState.ERROR, str(error))
        try:
            registration = self.backend.inspect()
        except ComponentError as error:
            return self._status(ComponentState.ERROR, str(error), launcher=launcher)

        common = {
            "launcher": launcher,
            "location": registration.location,
            "notes": registration.notes,
        }
        if not registration.exists:
            return self._status(
                ComponentState.NOT_INSTALLED,
                "goexport:// links are not registered for this user.",
                **common,
            )
        if not registration.owned:
            return self._status(
                ComponentState.ERROR,
                "goexport:// is registered by another application "
                f"({registration.location}"
                + (f": {registration.command}" if registration.command else "")
                + "). GoExport will not change or remove it. If you no longer "
                "need that registration, remove it with that application or your "
                "system settings, then install GoExport's protocol again.",
                **common,
            )

        registered = registration.launcher
        owned_fields = {
            **common,
            "owned": True,
            "registered_launcher": registered,
            "current": registered == launcher,
        }
        missing = [part for part in registered if not Path(part).is_file()]
        if registered and missing:
            return self._status(
                ComponentState.STALE,
                "The registration points to a GoExport location that no longer "
                f"exists ({', '.join(missing)}). Repair it to use this copy of "
                "GoExport, or uninstall it.",
                problems=tuple(f"Missing: {part}" for part in missing),
                **owned_fields,
            )
        if registration.problems or not registration.handler_ok:
            return self._status(
                ComponentState.ERROR,
                "GoExport's registration is incomplete or was changed. Repair it "
                "to restore it, or uninstall it.",
                problems=registration.problems,
                **owned_fields,
            )
        if registered != launcher:
            return self._status(
                ComponentState.INSTALLED,
                "goexport:// links open another GoExport copy at "
                f"{' '.join(registered)}.",
                **owned_fields,
            )
        return self._status(
            ComponentState.INSTALLED,
            "goexport:// links open this copy of GoExport.",
            **owned_fields,
        )

    def plan_install(
        self, status: ComponentStatus, reinstall: bool = False
    ) -> str | None:
        """Return ``install`` or ``repair``, or None when nothing would change.

        Raises :class:`ComponentError` when installing is not allowed.
        """
        if status.state is ComponentState.UNSUPPORTED:
            raise ComponentError(status.detail)
        if status.state is ComponentState.ERROR and not status.owned:
            raise ComponentError(status.detail)
        if status.state is ComponentState.NOT_INSTALLED:
            return "install"
        if status.state is ComponentState.INSTALLED and not reinstall:
            if status.current:
                return None
            raise ComponentError(
                status.detail
                + " Run 'install protocol --reinstall' to open links with this "
                "copy instead."
            )
        return "repair"

    def plan_uninstall(self, status: ComponentStatus) -> bool:
        """Return True when there is a GoExport registration to remove."""
        if status.state is ComponentState.UNSUPPORTED:
            raise ComponentError(status.detail)
        if status.state is ComponentState.NOT_INSTALLED:
            return False
        if not status.owned and status.location is None:
            # The registration could not be read at all.
            raise ComponentError(status.detail)
        return status.owned

    def install(self, reinstall: bool = False) -> OperationResult:
        """Install, or repair, GoExport's registration for this copy."""
        before = self.status()
        if self.plan_install(before, reinstall) is None:
            return OperationResult(
                "unchanged", "The GoExport URL protocol is already installed.", before
            )
        assert self.backend is not None
        self.backend.install(self.launcher)
        after = self.status()
        if after.state is not ComponentState.INSTALLED or not after.current:
            problems = "; ".join((*after.problems, after.detail))
            raise ComponentError(
                f"The registration was written but could not be verified: {problems}"
            )
        if before.state is ComponentState.NOT_INSTALLED:
            return OperationResult(
                "installed", "The GoExport URL protocol was installed.", after
            )
        return OperationResult(
            "repaired", "The GoExport URL protocol was repaired.", after
        )

    def uninstall(self) -> OperationResult:
        """Remove GoExport's registration; never another application's."""
        before = self.status()
        if not self.plan_uninstall(before):
            if before.state is ComponentState.NOT_INSTALLED:
                return OperationResult(
                    "unchanged", "The GoExport URL protocol is not installed.", before
                )
            return OperationResult(
                "unchanged",
                "GoExport has no registration to remove. " + before.detail,
                before,
            )
        assert self.backend is not None
        self.backend.uninstall()
        after = self.status()
        if after.owned:
            raise ComponentError(
                "The registration could not be removed: " + after.detail
            )
        return OperationResult(
            "removed", "The GoExport URL protocol was uninstalled.", after
        )
