import argparse

from commands import COMMANDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GoExport 2"
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="GoExport 2.0.0",
    )

    subparsers = parser.add_subparsers(
        required=True,
    )

    for command in COMMANDS:
        command.register(subparsers)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)