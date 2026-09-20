# GoExport

GoExport 2.0 exports GoAnimate movies through a Flash-enabled Chromium browser.
It has two CLI commands and no GUI:

- `record` captures playback and system audio with PyScap, then muxes the video
  and optionally appends an outro.
- `export` seeks each movie frame, encodes browser screenshots, builds an audio
  timeline from movie XML, and mixes locally resolved sound assets.

## Setup and usage

Use Python 3.13, as the release workflow does. Create a virtual environment and
install the Python dependencies:

```sh
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -r requirements.txt
python scripts/download_dependencies.py
python main.py doctor
python main.py --help
```

The dependency installer replaces the Chromium and FFmpeg directories in `bin/`.
Chromium 87 and its matching ChromeDriver are deliberately retained for PPAPI
Flash support. The FFmpeg download URLs use moving release endpoints; they are
not reproducibly pinned. `requirements.txt` retains the existing Python pins.

Start your Wrapper: Offline instance and asset server before exporting. Defaults
in `goexport/config.py` use localhost ports 4343 and 4664; the CLI can override
server URLs and player paths.

```sh
python main.py record -id MOVIE_ID -out final_output --no-outro
python main.py export -id MOVIE_ID -xml movie.xml -ugc /path/to/ugc -as /path/to/theme/assets
```

Both workflows accept additional Flashvars. New names are added and standard
names are overridden using last-value-wins behavior:

```sh
python main.py record -id MOVIE_ID --additional-flashvars "custom=1&movieId=override"
```

Player settings can contain named placeholders. The built-in `owner_id`
replacement resolves to the `--user-id` value, so a store path such as
`https://example/store/<store>?v={owner_id}` is resolved automatically. Add or
override replacements per invocation with repeatable `--replacement NAME=VALUE`
options, or persist them in `config.toml`:

```toml
[replacements]
owner_id = "{user_id}"
asset_owner = "users/{user_id}"
```

Run either command with `--help` for all options. MP4, MOV, and MKV are supported.
Recording defaults to 1280x720 at 24 fps and appends `resources/outro.mp4` unless
`--no-outro` is supplied. Its intermediate files are `<output>.video.mkv` and
`<output>.audio.wav`; failed captures retain available diagnostics. Recording
without captured audio muxes a silent audio track into the requested container.

Chromium, ChromeDriver, Pepper Flash, and FFmpeg paths can be changed with
`--chrome-path`, `--chromedriver-path`, `--flash-plugin-path`, and `--ffmpeg-path`.
The Flash version passed to Chromium can be changed with
`--flash-plugin-version`. These default to the existing platform-specific
configuration, paths are validated before the command starts, and the path
options are also honored by `doctor`.
Frame-by-frame export uses `output.mkv`, `audio.wav`, and `final_output.<format>`
in the working directory. These fixed names are unsuitable for concurrent runs.

### JSON output

Place `--json` before the command to reserve stdout for newline-delimited JSON:

```sh
python main.py --json record -id MOVIE_ID -out final_output --no-outro
python main.py --json export -id MOVIE_ID -xml movie.xml -ugc /path/to/ugc -as /path/to/theme/assets
python main.py --json doctor
```

Progress events use `{"event":"progress","progress":42.5,"stage":"recording"}`.
Successful video commands finish with
`{"event":"complete","progress":100,"output":"final_output.mp4"}`, while
failures use `{"event":"error","message":"...","code":1}`. A caller can consume
the live stream one event at a time:

```python
for line in process.stdout:
    event = json.loads(line)
    if "progress" in event:
        update_progress(event["progress"])
```

## Code map

- `main.py` calls `goexport/cli.py`, which parses once, sets up Rich logging, and
  dispatches the commands registered in `goexport/commands/__init__.py`.
- `commands/record.py` and `commands/export.py` define command-specific options.
  `helpers.py` contains shared player options, argument validators, and output
  path handling. `config.py` defines defaults and platform-specific runtime paths.
- `services/browser.py` manages Selenium, display sizing, Flash permission,
  template injection, and capture-target lookup. `close()` releases Chromium
  and the virtual display. `services/flash.py` waits for player readiness and
  the template's start/stop markers.
- `services/recorder.py` coordinates playback, the stop watcher, capture, audio
  alignment, and output cleanup. `services/capture.py` converts timestamps and
  chooses frames for a constant frame rate.
- `services/renderer.py` encodes frame-by-frame screenshots.
  `timeline_builder.py`, `asset_resolver.py`, and `audio.py` load movie sounds,
  resolve UGC/theme files, and send the timeline to the audio encoder.
- `services/ffmpeg.py` owns encoding commands, pipe/process diagnostics, muxing,
  and outro concatenation. `models/audio_clip.py` describes timeline clips;
  the `Timeline` model remains available, although export currently uses a list.
- `scripts/download_dependencies.py` installs external runtime files.
  `GoExport.spec` bundles Python code and PyScap libraries; the release workflow
  copies `bin/` and `resources/` alongside the executable separately.

## Development and verification

Prefer explicit control flow, descriptive names, four-space indentation, and
the existing command/service split. Keep platform branches visible. Share
genuinely repeated logic without adding service layers. Raise errors where they
occur; the CLI logs uncaught errors and returns 1, or 130 for cancellation.
Cleanup exceptions that are deliberately tolerated should include diagnostic
logging. Keep encoder stderr file-backed to avoid pipe deadlocks.

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python3 -m unittest tests.test_macos_capture_diagnostic -v
python -m ruff check goexport scripts tests main.py
python -m ruff format --check goexport scripts tests main.py
python -m mypy
python -m compileall -q goexport scripts tests main.py
python -m pip check
python -m PyInstaller GoExport.spec
```

Mypy checks annotated code and ignores missing third-party stubs; this is not
strict checking of every service method. FFmpeg integration tests run when the
configured bundled executable exists and otherwise report a skip. They use
temporary files, verify decoded frames/audio and container headers, and cover
silent export audio and outro concatenation. Failure tests cover browser,
capture, and encoder cleanup. Build output is ignored by Git.

## Platform behavior and remaining limits

Windows selects the browser capture target by its unique recording title. On
macOS, GoExport assigns a temporary unique title before fullscreen, remembers
the matching window ID, and resolves that ID again after fullscreen because
Chromium can expose a stale native title there. Linux explicitly uses PyScap's
X11 backend and the current display's root window rather than enumerating
windows. It tries to start an Xvfb display and logs a fallback to the current
display if startup fails. Linux therefore needs an available X11 display/Xvfb;
macOS may require screen-capture permission.

PyScap timestamps use integer nanoseconds within GoExport and are never compared
with Python wall clocks. The recorder discards dequeued frames until `play()`
returns, but queued frames can precede that call. Stop is bounded by the first
dequeued frame after the watcher observes the stop marker. Exact player-marker
alignment and cancellation of a blocked native capture read remain limitations.

The export command needs movie XML for local audio even though `--movie-xml` is
not marked required by argparse. The shared HTML template plays by movie ID;
it does not consume the supplied XML path or user ID. Flash settings automation
locates Chromium's Flash permission control through the settings page's Shadow
DOM. Outro concatenation expects an audio stream in the custom outro. These
workflows require an actual Wrapper instance and platform testing beyond
synthetic FFmpeg checks.

## Roles

### Lead Developers
- Lexian-Droid

### Contributors
- Octanuary
    Assisted in the SWF side of things.
