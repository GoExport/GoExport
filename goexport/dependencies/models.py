"""Data types used by GoExport's managed runtime dependency system."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DependencyStatus(Enum):
    INSTALLED = "installed"
    MISSING = "missing"
    BROKEN = "broken"


@dataclass(frozen=True)
class VerificationResult:
    status: DependencyStatus
    missing: tuple[Path, ...] = ()
    invalid: tuple[Path, ...] = ()


@dataclass(frozen=True)
class InstallContext:
    work_dir: Path
    progress: Callable[[str], None]


Installer = Callable[["Dependency", InstallContext], None]


@dataclass(frozen=True)
class Dependency:
    id: str
    name: str
    required_paths: tuple[Path, ...]
    install: Installer
    runtime_argument: str
    runtime_path: Path
    install_after: tuple[str, ...] = ()
    invalidates: tuple[str, ...] = ()
    repair_with: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def verify(self) -> VerificationResult:
        missing = tuple(path for path in self.required_paths if not path.exists())
        invalid = tuple(
            path for path in self.required_paths if path.exists() and not _usable(path)
        )
        if not missing and not invalid:
            return VerificationResult(DependencyStatus.INSTALLED)
        if len(missing) == len(self.required_paths) and not invalid:
            return VerificationResult(DependencyStatus.MISSING, missing=missing)
        return VerificationResult(
            DependencyStatus.BROKEN,
            missing=missing,
            invalid=invalid,
        )


def _usable(path: Path) -> bool:
    if path.is_file():
        return path.stat().st_size > 0
    if path.is_dir():
        try:
            next(path.iterdir())
        except StopIteration:
            return False
        return True
    return False
