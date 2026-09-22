"""Capture backend selection for the live recording workflow."""

from goexport.services.recording_backends.base import CaptureArtifacts, CaptureResult
from goexport.services.recording_backends.obs import OBSBackend
from goexport.services.recording_backends.pyscap import PyScapBackend


def create_recording_backend(name: str, **kwargs):
    if name == "pyscap":
        return PyScapBackend(**kwargs)
    if name == "obs":
        return OBSBackend(**kwargs)
    raise ValueError(f"Unsupported capture backend: {name}")


__all__ = [
    "CaptureArtifacts",
    "CaptureResult",
    "OBSBackend",
    "PyScapBackend",
    "create_recording_backend",
]
