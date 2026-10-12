# main.py - Entry point for the GoExport application.


def run() -> int:
    from goexport.cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(run())
