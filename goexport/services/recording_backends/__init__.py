"""Capture backend selection for the live recording workflow."""

from goexport.services.recording_backends.base import CaptureArtifacts, CaptureResult
from goexport.services.recording_backends.capturekit import CaptureKitBackend
from goexport.services.recording_backends.obs import OBSBackend

RECORDING_BACKENDS = ("capturekit", "obs")
PYSCAP_MIGRATION_MESSAGE = (
    "The 'pyscap' capture backend was removed: GoExport now records with "
    "CaptureKit. Use --capture-backend capturekit (the default), or set "
    'backend = "capturekit" under [recording] in config.toml.'
)


def create_recording_backend(name: str, **kwargs):
    if name == "capturekit":
        return CaptureKitBackend(**kwargs)
    if name == "obs":
        return OBSBackend(**kwargs)
    if name == "pyscap":
        raise ValueError(PYSCAP_MIGRATION_MESSAGE)
    raise ValueError(f"Unsupported capture backend: {name}")


__all__ = [
    "PYSCAP_MIGRATION_MESSAGE",
    "RECORDING_BACKENDS",
    "CaptureArtifacts",
    "CaptureKitBackend",
    "CaptureResult",
    "OBSBackend",
    "create_recording_backend",
]
