# GoExport

GoExport 2 exports GoAnimate and Wrapper: Offline movies to MP4, MOV, or MKV by playing them in a Flash-enabled Chromium 87 browser. It is a portable application: extract it anywhere and run it, with no installer or administrator rights.

A release contains two programs:

- **GoExport** (`GoExport.exe` / `GoExport`), the command-line tool that does all the work.
- **GoExport-GUI**, a desktop application that runs GoExport for you.

Full documentation lives in the **[GoExport Wiki](https://github.com/GoExport/GoExport/wiki)**.

## Quick start

1. Download `GoExport-windows-x64.zip` or `GoExport-linux-x64.tar.gz` from [Releases](https://github.com/GoExport/GoExport/releases) and extract the whole archive.
2. Start Wrapper: Offline or the compatible server you want to export from.
3. Check the setup:

   ```sh
   ./GoExport doctor          # Windows: .\GoExport.exe doctor
   ```

4. Open **GoExport-GUI**, pick a preset, enter the video ID, and select **Export Video**. Or use the CLI:

   ```sh
   ./GoExport record -id MOVIE_ID -out my_video
   ```

GoExport checks its bundled Chromium, ChromeDriver, Pepper Flash, and FFmpeg before each export and offers to repair missing ones.

See [Installation and Setup](https://github.com/GoExport/GoExport/wiki/Installation%E2%80%90and%E2%80%90Setup) for details, including running from source.

## Commands

| Command | Purpose |
| --- | --- |
| `record` | Export a movie by recording its playback (recommended). |
| `export` | Alpha frame-by-frame export with audio rebuilt from movie XML and local assets. |
| `doctor` | Check whether this computer is ready to run GoExport. |
| `status` | Show the status of GoExport system components. |
| `install protocol` / `uninstall protocol` | Register or remove the per-user `goexport://` URL protocol. |
| `handle-url` | Run a `goexport://` request (used by the URL protocol). |

Global options `--verbose`, `--json` (JSON Lines output for scripts) and `-y` (approve changes without prompting) go before the command. Every command and option is documented in the [CLI Reference](https://github.com/GoExport/GoExport/wiki/CLI%E2%80%90Reference).

## Documentation

| Topic | Page |
| --- | --- |
| Recording, OBS backend, outros | [Recording Guide](https://github.com/GoExport/GoExport/wiki/Recording%E2%80%90Guide) |
| The desktop application and its Components page | [GUI Guide](https://github.com/GoExport/GoExport/wiki/GUI%E2%80%90Guide) |
| `config.toml` settings and placeholders | [Configuration](https://github.com/GoExport/GoExport/wiki/Configuration) |
| GUI presets and the ID browser | [GUI Presets and Browser Picker](https://github.com/GoExport/GoExport/wiki/GUI%E2%80%90Presets%E2%80%90and%E2%80%90Browser%E2%80%90Picker) |
| Frame-by-frame export | [Frame-by-Frame Export](https://github.com/GoExport/GoExport/wiki/Frame%E2%80%90by%E2%80%90Frame%E2%80%90Export) |
| Cloudflare and Anubis challenges | [Browser Verification](https://github.com/GoExport/GoExport/wiki/Browser%E2%80%90Verification) |
| `goexport://` links for other applications | [URL Protocol](https://github.com/GoExport/GoExport/wiki/URL%E2%80%90Protocol) |
| JSON output, exit codes, integration | [Automation and JSON Output](https://github.com/GoExport/GoExport/wiki/Automation%E2%80%90and%E2%80%90JSON%E2%80%90Output) |
| Fixing problems | [Troubleshooting](https://github.com/GoExport/GoExport/wiki/Troubleshooting) |
| Code layout, tests, builds, releases | [Development and Releases](https://github.com/GoExport/GoExport/wiki/Development%E2%80%90and%E2%80%90Releases) |

## Platform support

| Platform | Status |
| --- | --- |
| Windows x64 | Supported; release build. |
| Linux x64 (X11/Xvfb, glibc 2.35+) | Supported; release build. Xvfb must be installed. Wayland-only sessions are not supported for recording. |
| macOS | Not currently supported; no release build. Running from source is experimental and needs the OBS backend. Help is welcome. |

Chromium 87 and its matching ChromeDriver are deliberately retained because newer Chromium releases removed PPAPI Flash.

## Development

Use Python 3.13. Clone with submodules (`gui` is the GUI, `docs` is the wiki):

```sh
git clone --recurse-submodules --branch 2.x https://github.com/GoExport/GoExport.git
cd GoExport
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/download_dependencies.py
python main.py doctor
```

Checks to run before a pull request:

```sh
python -m unittest discover -s tests -v
python -m ruff check goexport scripts tests main.py
python -m ruff format --check goexport scripts tests main.py
python -m mypy
python -m compileall -q goexport scripts tests main.py
python -m pip check
```

The code map, architecture notes, opt-in integration tests, and the release process are in [Development and Releases](https://github.com/GoExport/GoExport/wiki/Development%E2%80%90and%E2%80%90Releases).

## Roles

### Lead Developers
- Lexian-Droid

### Contributors
- Octanuary
    Assisted in the SWF side of things.
