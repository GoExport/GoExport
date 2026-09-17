# main.py - Entry point for the GoExport application.

from goexport.services.capture import configure_backend


def run() -> int:
    configure_backend()
    from goexport.cli import main

    return main()

if __name__ == "__main__":
    raise SystemExit(run())
