"""``install``, ``uninstall`` and ``status`` for GoExport system components."""

from __future__ import annotations

import argparse
import logging

from rich.markup import escape

from goexport.components import COMPONENT_IDS, ComponentStatus, get_component
from goexport.helpers import require_confirmation
from goexport.reporting import Reporter, get_reporter

logger = logging.getLogger(__name__)

STATE_COLORS = {
    "installed": "green",
    "not_installed": "yellow",
    "stale": "yellow",
    "error": "red",
    "unsupported": "yellow",
}


def _add_component_parser(
    subparsers: argparse._SubParsersAction, help_text: str
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "protocol",
        help=help_text,
        description=help_text,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # SUPPRESS keeps a global -y given before the command (GoExport -y ...).
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Make the change without asking for confirmation.",
    )
    return parser


def register(subparsers: argparse._SubParsersAction) -> None:
    install = subparsers.add_parser(
        "install",
        help="Install or repair a GoExport system component.",
        description="Install or repair a GoExport system component.",
    )
    install_components = install.add_subparsers(
        dest="component", required=True, metavar="COMPONENT"
    )
    install_protocol = _add_component_parser(
        install_components,
        "Register goexport:// links for the current user so they open this "
        "copy of GoExport. Repairs a stale or damaged registration.",
    )
    install_protocol.add_argument(
        "--reinstall",
        action="store_true",
        help=(
            "Rewrite the registration even when it is valid, for example to "
            "point it at this copy of GoExport."
        ),
    )
    install_protocol.set_defaults(func=install_entry)

    uninstall = subparsers.add_parser(
        "uninstall",
        help="Remove a GoExport system component.",
        description="Remove a GoExport system component.",
    )
    uninstall_components = uninstall.add_subparsers(
        dest="component", required=True, metavar="COMPONENT"
    )
    uninstall_protocol = _add_component_parser(
        uninstall_components,
        "Remove GoExport's goexport:// registration for the current user. "
        "Registrations made by other applications are left unchanged.",
    )
    uninstall_protocol.set_defaults(func=uninstall_entry)

    status = subparsers.add_parser(
        "status",
        help="Show the status of GoExport system components.",
        description="Show the status of GoExport system components.",
    )
    status.add_argument(
        "component",
        nargs="?",
        choices=COMPONENT_IDS,
        help="Component to show (default: all components).",
    )
    status.set_defaults(func=status_entry)


def show_status(reporter: Reporter, status: ComponentStatus) -> None:
    """Write a component status for people; JSON output uses result events."""
    color = STATE_COLORS[status.state.value]

    def line(level: int, label: str, value: str) -> None:
        reporter.diagnostic(level, "  %s: %s", label, escape(value), logger=logger)

    reporter.diagnostic(
        logging.INFO,
        f"%s: [{color}]%s[/{color}]",
        escape(status.name),
        status.label,
        logger=logger,
    )
    reporter.diagnostic(logging.INFO, "  %s", escape(status.detail), logger=logger)
    line(logging.INFO, "System", status.system)
    line(logging.INFO, "Scope", status.scope)
    if status.location:
        line(logging.INFO, "Location", status.location)
    if status.launcher:
        line(logging.INFO, "This GoExport", " ".join(status.launcher))
    if status.registered_launcher and not status.current:
        line(logging.INFO, "Registered GoExport", " ".join(status.registered_launcher))
    for problem in status.problems:
        line(logging.WARNING, "Problem", problem)
    for note in status.notes:
        line(logging.INFO, "Note", note)


def status_entry(args: argparse.Namespace) -> int:
    reporter = get_reporter(args)
    component_ids = (args.component,) if args.component else COMPONENT_IDS
    statuses = [get_component(component_id).status() for component_id in component_ids]
    for status in statuses:
        show_status(reporter, status)
    reporter.result(
        command="status", components=[status.to_dict() for status in statuses]
    )
    return 0


def install_entry(args: argparse.Namespace) -> int:
    reporter = get_reporter(args)
    component = get_component(args.component)
    status = component.status()
    show_status(reporter, status)
    action = component.plan_install(status, reinstall=args.reinstall)
    if action is not None:
        require_confirmation(
            args,
            f"{action.capitalize()} the {component.name} for the current user?",
            [
                f"GoExport will {action} its goexport:// registration:",
                f"  Location: {status.location}",
                f"  Opens:    {' '.join(component.launcher)}",
            ],
        )
    result = component.install(reinstall=args.reinstall)
    reporter.diagnostic(logging.INFO, "%s", escape(result.message), logger=logger)
    reporter.result(
        command="install",
        component=component.id,
        action=result.action,
        message=result.message,
        status=result.status.to_dict(),
    )
    return 0


def uninstall_entry(args: argparse.Namespace) -> int:
    reporter = get_reporter(args)
    component = get_component(args.component)
    status = component.status()
    show_status(reporter, status)
    if component.plan_uninstall(status):
        require_confirmation(
            args,
            f"Remove the {component.name} for the current user?",
            [
                "GoExport will remove its goexport:// registration:",
                f"  Location: {status.location}",
            ],
        )
    result = component.uninstall()
    reporter.diagnostic(logging.INFO, "%s", escape(result.message), logger=logger)
    reporter.result(
        command="uninstall",
        component=component.id,
        action=result.action,
        message=result.message,
        status=result.status.to_dict(),
    )
    return 0
