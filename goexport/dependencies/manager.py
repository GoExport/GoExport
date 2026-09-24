"""Verification, repair planning, and bootstrap policy for runtime dependencies."""

from __future__ import annotations

import logging
import sys
import tempfile
from argparse import Namespace
from collections.abc import Iterable
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from goexport.dependencies.definitions import dependency_registry
from goexport.dependencies.models import (
    Dependency,
    DependencyStatus,
    InstallContext,
    VerificationResult,
)

logger = logging.getLogger(__name__)

ALL_DEPENDENCIES = ("chromium", "chromedriver", "pepper_flash", "ffmpeg")


class DependencyBootstrapError(RuntimeError):
    pass


class DependencyManager:
    def __init__(self, registry: dict[str, Dependency] | None = None):
        self.registry = registry or dependency_registry()

    def statuses(self, ids: Iterable[str]) -> dict[str, VerificationResult]:
        return {
            dependency_id: self.registry[dependency_id].verify()
            for dependency_id in ids
        }

    def managed_requirements(
        self, args: Namespace, ids: Iterable[str]
    ) -> tuple[str, ...]:
        managed: list[str] = []
        for dependency_id in ids:
            dependency = self.registry[dependency_id]
            selected_path = Path(getattr(args, dependency.runtime_argument))
            if selected_path == dependency.runtime_path:
                managed.append(dependency_id)
        return tuple(managed)

    def needed(self, ids: Iterable[str]) -> tuple[str, ...]:
        return tuple(
            dependency_id
            for dependency_id, result in self.statuses(ids).items()
            if result.status is not DependencyStatus.INSTALLED
        )

    def repair_plan(
        self, needed: Iterable[str], allowed: Iterable[str] | None = None
    ) -> tuple[str, ...]:
        selected = set(needed)
        allowed_ids = set(allowed or self.registry)
        for dependency_id in tuple(selected):
            repair_with = self.registry[dependency_id].repair_with
            if repair_with:
                selected.add(repair_with)
        changed = True
        while changed:
            changed = False
            for dependency_id in tuple(selected):
                for invalidated in self.registry[dependency_id].invalidates:
                    if invalidated in allowed_ids and invalidated not in selected:
                        selected.add(invalidated)
                        changed = True

        ordered: list[str] = []
        while selected:
            available = sorted(
                dependency_id
                for dependency_id in selected
                if not (set(self.registry[dependency_id].install_after) & selected)
            )
            if not available:
                raise RuntimeError(
                    "Managed dependency installation order contains a cycle."
                )
            ordered.extend(available)
            selected.difference_update(available)
        return tuple(ordered)

    def install(self, ids: Iterable[str], allowed: Iterable[str] | None = None) -> None:
        plan = self.repair_plan(ids, allowed)
        for dependency_id in plan:
            dependency = self.registry[dependency_id]
            logger.info("Installing %s...", dependency.name)
            with tempfile.TemporaryDirectory(
                prefix=f"goexport-{dependency.id}-"
            ) as temp:
                context = InstallContext(Path(temp), logger.info)
                dependency.install(dependency, context)
            result = dependency.verify()
            if result.status is not DependencyStatus.INSTALLED:
                detail = ", ".join(
                    str(path) for path in (*result.missing, *result.invalid)
                )
                raise DependencyBootstrapError(
                    f"{dependency.name} installation did not verify successfully: {detail}"
                )
            logger.info("%s installed successfully.", dependency.name)

    def bootstrap(self, args: Namespace, ids: Iterable[str]) -> None:
        managed = self.managed_requirements(args, ids)
        needed = self.needed(managed)
        if not needed:
            return
        names = [self.registry[dependency_id].name for dependency_id in needed]
        if not getattr(args, "yes", False):
            if getattr(args, "json", False) or not _interactive_terminal():
                joined = ", ".join(names)
                raise DependencyBootstrapError(
                    f"{joined} requires installation or repair, and GoExport cannot "
                    "prompt for approval. Re-run with -y or --yes."
                )
            console = Console()
            console.print(
                "GoExport needs to install or repair these runtime components:\n"
            )
            for name in names:
                console.print(f"  • {name}")
            console.print()
            if not Confirm.ask("Install them now?", default=False, console=console):
                raise DependencyBootstrapError(
                    "Runtime dependency installation declined."
                )
        self.install(needed, managed)

    def install_all(self) -> None:
        needed = self.needed(ALL_DEPENDENCIES)
        if needed:
            self.install(needed)


def _interactive_terminal() -> bool:
    return bool(sys.stdin.isatty() and sys.stdout.isatty())
