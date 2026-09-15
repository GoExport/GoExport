---
name: goexport-maintenance
description: Maintain GoExport CLI, configuration, dependencies, and packaging using the repository's established module boundaries. Use for GoExport cleanup or development outside media timing and encoding changes.
---

# GoExport maintenance

Read the repository README, configuration, dependency files, and Git status
before changing code. Preserve existing worktree changes.

- `main.py` calls `cli.main()`, which parses once and dispatches `export` and
  `record`. Preserve command flags, defaults, MP4/MOV/MKV support, and exit
  codes unless a confirmed bug needs a compatible fix.
- `helpers.py` owns shared player arguments and argument validators. Use
  `add_player_arguments()` for settings shared by both commands; leave
  command-specific options in their command module. `export.py` and `record.py`
  retain imported compatibility names.
- `config.py` defines paths relative to either the project root or frozen
  executable. Keep Windows, Linux, and macOS runtime paths explicit.
- Keep the existing command/service split. Prefer direct, readable sequencing
  over coordinator layers, broad exception suppression, or speculative helpers.
  Use module loggers; application diagnostics should go through logging.

`requirements.txt` is the existing pinned runtime/build set. Keep development
tools in `requirements-dev.txt`; do not regenerate runtime dependencies from a
development environment. Chromium 87 and its matching driver are intentionally
retained for PPAPI Flash. The installer replaces `bin/` directories, while the
release workflow copies `bin/` and `resources/` next to the packaged executable.
Use temporary build and work directories when testing `GoExport.spec`.

Run the relevant checks after changes:

```sh
python -m unittest discover -s tests -v
python -m ruff check goexport scripts tests main.py
python -m ruff format --check goexport scripts tests main.py
python -m mypy
python -m compileall -q goexport scripts tests main.py
python -m pip check
```

For packaging changes, build `GoExport.spec` and run the produced executable
with `--help`. That smoke test does not verify Flash playback or native capture.
Review the final diff and explicitly report checks that need a live service or
different platform.
