# GoExport

GoExport 2.0 exports GoAnimate movies through a Flash-enabled Chromium browser.
It has two CLI commands and no GUI:

- `record` captures playback and audio with CaptureKit by default, or with an
  optional OBS Studio backend, then muxes the video and optionally
  appends an outro.
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

The dependency installer verifies each managed component and repairs only missing or
incomplete Chromium, ChromeDriver, Pepper Flash, and FFmpeg installations. Downloads
are staged and verified before a managed destination is replaced.
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

### Optional OBS recording backend

OBS Studio can provide an alternative window/audio capture path on macOS 13+,
Windows, and Linux/X11. Install and start OBS, enable its WebSocket
server, and install the pinned Python dependency from `requirements.txt`. Put
the WebSocket password in `GOEXPORT_OBS_PASSWORD`, then run:

```sh
GOEXPORT_OBS_PASSWORD='your-password' python main.py record \
  -id MOVIE_ID --capture-backend obs -out final_output --no-outro
```

PowerShell uses `$env:GOEXPORT_OBS_PASSWORD = 'your-password'`. On Linux, OBS
and GoExport must share an X11 `DISPLAY`; unattended Wayland window selection is
not currently supported. The backend creates and reuses a persistent `GoExport`
OBS profile and scene collection, switches back to the user's prior resources
after recording, and never automatically deletes them. OBS itself is not
bundled or launched. Use `--obs-force-profile` to explicitly allow GoExport to
reuse and reconfigure an existing unmarked profile and scene collection. OBS
records its temporary MKV directly beside the requested output, and GoExport
removes that MKV after successful post-processing.

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

Commands that need GoExport-managed runtime components verify them before starting.
Use `-y` or `--yes` to approve any required installation or repair without a prompt;
non-interactive callers must use this option. Explicit custom runtime paths are never
replaced by the managed installer. `doctor`, `--help`, and `--version` remain
non-mutating.

### JSON output

Place `--json` before the command to reserve stdout for newline-delimited JSON:

```sh
python main.py --json -y record -id MOVIE_ID -out final_output --no-outro
python main.py --json -y export -id MOVIE_ID -xml movie.xml -ugc /path/to/ugc -as /path/to/theme/assets
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

Browser verification emits
`{"event":"verification_required","reason":"cloudflare","provider":"cloudflare","interaction":"manual","message":"...","presentation":"window","timeout":300}`.
`provider` is `cloudflare` or `anubis` (`reason` repeats it for older
consumers). `interaction` is `automatic` while the browser completes an Anubis
check by itself (`presentation` is then `null`) and `manual` when the user must
act: `presentation` is `window` when the Chromium window itself is shown and
`vnc` when the Linux verification viewer is shown. An automatic check that needs
help is followed by a second, `manual` event. Verification ends with either
`{"event":"verification_complete","provider":"anubis"}` or
`{"event":"verification_failed","message":"...","reason":"timeout","provider":"anubis"}`
followed by the command's `error` event; failure reasons include `timeout`,
`cancelled`, `unsupported`, `blocked`, `repeated` and `failed`. Events never contain VNC ports or credentials. While
verification is pending, a controlling process may write
`{"command":"cancel"}` and a newline to GoExport's stdin to cancel cleanly; the
command exits with code 130.

### Cloudflare verification

When the Wrapper page shows a Cloudflare challenge (detected by the
`cf-mitigated: challenge` header, the "Just a moment..." page, or Cloudflare's
challenge-page elements), GoExport pauses before Flash setup, DOM injection and
recording, and lets you complete the check yourself in its existing browser
session; cookies, profile and WebDriver are kept, and no second browser starts.

- Windows, and Linux with `--capture-backend obs`, bring the existing Chromium
  window to the front, then restore its minimized state and position.
- Linux with GoExport's private Xvfb display opens the bundled TigerVNC viewer
  on your desktop, connected through the bundled `x11vnc` to that display on
  localhost with a single-use password. Both close when verification ends.

The export resumes automatically. Use `--verification-timeout SECONDS` (default
300, `0` waits indefinitely) or `--no-interactive-verification` to fail
immediately instead; both are also available as `[verification]` settings in
`config.toml`. GoExport never solves, bypasses or spoofs verification.

### Anubis verification

Sites such as FlashThemes are protected by
[Anubis](https://github.com/TecharoHQ/anubis), whose "Making sure you're not a
bot!" page runs a proof-of-work calculation in the browser. GoExport recognizes
it by Anubis' challenge data and its `/.within.website/x/cmd/anubis/` scripts
(never by a title or a mention of Anubis alone), lets the existing Chromium
session complete the calculation unattended, waits for the real page to load,
and continues; nothing is shown and the session's Anubis cookie is kept for the
rest of the export.

The browser is only shown, as for Cloudflare, when the check stops making
progress for 20 seconds or has not finished after
`--automatic-verification-timeout SECONDS` (default 60; `automatic_timeout` in
`[verification]`). With `--no-interactive-verification` such a check fails
instead. GoExport stops at once, with the page's own message, when Anubis
reports that the browser cannot run its check, shows an error, or denies
access, and stops after three successive challenges whose passes Anubis did not
accept, rather than retrying indefinitely.

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
- `services/recorder.py` coordinates playback, the stop watcher, capture, and
  output cleanup. `services/recording_backends/capturekit.py` binds the owned
  browser window and lets CaptureKit synchronize video and audio.
- `services/challenge.py` detects Cloudflare and Anubis challenges, and
  `services/verification.py` pauses export preparation while the user completes
  one in the existing session. `services/window_presenter.py` raises the
  Chromium window (Windows); `services/vnc.py` shows the Linux Xvfb display
  through the bundled VNC tools that `scripts/bundle_linux_vnc.py` packages.
- `services/renderer.py` encodes frame-by-frame screenshots.
  `timeline_builder.py`, `asset_resolver.py`, and `audio.py` load movie sounds,
  resolve UGC/theme files, and send the timeline to the audio encoder.
- `services/ffmpeg.py` owns encoding commands, pipe/process diagnostics, muxing,
  and outro concatenation. `models/audio_clip.py` describes timeline clips;
  the `Timeline` model remains available, although export currently uses a list.
- `goexport/dependencies/` defines, verifies, and selectively installs managed runtime files.
- `scripts/download_dependencies.py` is the developer/build wrapper around that shared dependency manager.
  `GoExport.spec` bundles CaptureKit's platform modules; the release workflow
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

Windows and Linux select the owned Chromium window by its unique recording title
and retain its native handle. CaptureKit crops the physical-pixel viewport and
records Chromium process audio without enabling a microphone. Linux passes
GoExport's private Xvfb display explicitly; only that owned display may be used
for the controlled monitor fallback when XComposite capture is unavailable.
Wayland-only systems and macOS are unsupported by CaptureKit; use OBS on macOS.

CaptureKit owns frame pacing and audio/video synchronization. GoExport starts it
paused, resumes immediately before `player.play()`, and stops after the template's
playback-stop event. Native capture behavior still requires platform testing;
the opt-in native tests are disabled unless explicitly requested.

FlashThemes' Anubis check (the `fast` SHA-256 proof-of-work, difficulty 4)
completes in about a second in GoExport's Chromium 87: Anubis' scripts use only
features Chromium 87 supports, and that algorithm needs no WebAssembly. Sites
that configure Anubis' WebAssembly algorithms (`argon2id`, `hashx`, `sha256`)
fall back to Anubis' non-SIMD builds in Chromium 87 and were not tested; if
Anubis cannot run there, GoExport reports the page's error as a Chromium 87
limitation. High difficulties can take minutes, and such checks run until the
verification timeout.

Cloudflare can refuse or endlessly repeat challenges for GoExport's Chromium 87,
which Selenium controls and which cannot be updated without losing Flash; GoExport
reports this as unsupported or as a timeout rather than working around it. Only
the Wrapper page itself is checked: a challenge on a separate SWF or asset host
appears as a Flash loading failure. A challenge that replaces the player after
recording or rendering started stops the export with a clear error instead of
recording the challenge. Linux verification needs a graphical X11 or XWayland
desktop; on a headless server it fails with an explanation. Xvfb itself is still
a system requirement on Linux. The bundled VNC tools come from Ubuntu 22.04 and
need glibc 2.35 or newer, as does the rest of the Linux release; set
`GOEXPORT_VNC_INTEGRATION=1` or `GOEXPORT_BROWSER_TESTS=1` to run the opt-in
VNC and Chromium verification tests.

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
