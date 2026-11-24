"""System components that GoExport can install, repair, and remove.

Each component owns its platform-specific code and reports a
:class:`ComponentStatus`. The runtime dependencies in ``goexport.dependencies``
(Chromium, ChromeDriver, Pepper Flash and FFmpeg) are bootstrapped by the
export commands and are not managed here.
"""

from goexport.components.models import (
    ComponentError,
    ComponentState,
    ComponentStatus,
)
from goexport.components.protocol import OperationResult, ProtocolComponent

COMPONENT_IDS = ("protocol",)


def get_component(component_id: str) -> ProtocolComponent:
    if component_id == "protocol":
        return ProtocolComponent()
    raise KeyError(component_id)


__all__ = [
    "COMPONENT_IDS",
    "ComponentError",
    "ComponentState",
    "ComponentStatus",
    "OperationResult",
    "ProtocolComponent",
    "get_component",
]
