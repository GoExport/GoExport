---
name: goexport-media-pipeline
description: Safely modify GoExport recording, browser and Flash automation, timestamp alignment, frame export, audio mixing, or FFmpeg output.
---

# GoExport media pipeline

Read the repository README and affected services/tests. Keep screen recording
and frame-by-frame export as separate workflows.

`capture.py` converts PyScap timestamps to integer nanoseconds; do not compare
them with Python clocks. `VideoSelector` selects the nearest capture for each
CFR slot, keeps the first distance tie, and repeats the previous frame for
missing slots. Audio alignment uses each buffer's sample rate and byte size,
not video FPS. Preserve these rules and add focused tests for timing changes.

PyScap imports stay lazy. Windows and macOS capture one uniquely titled browser
window. Linux forces PyScap's X11 backend and captures the current display root;
do not reintroduce Linux window enumeration. Preserve browser screen/viewport
checks, explicit native permission checks, and cleanup: `BrowserService.close()`
must release its display even if Chromium shutdown fails.

The HTML template signals player start/stop. Its movie-ID playback and
layout-dependent Flash settings keyboard automation need real-browser testing
before modification. The template does not consume `MOVIE_XML` or `USER_ID`.

`Renderer` must always close its encoder. `_PipeEncoder` keeps stderr in a
temporary file, handles partial stdin writes, and reports FFmpeg failure output.
`FFmpegMuxer` deletes intermediates only after a successful mux. Missing
recording audio is represented by `None` and must be muxed as silent audio into
the requested container; never rename MKV bytes to MP4 or MOV. Outro rendering
writes a temporary replacement and expects the outro to contain audio.

Recording intermediates live beside its chosen output and remain after failure
for diagnosis. Frame export keeps its current fixed working-directory file
names, so concurrent export is unsupported.

Run `python -m unittest discover -s tests -v`. FFmpeg integration tests use
temporary files and verify decoded video/audio, containers, silent muxing, and
outro replacement; they skip without configured FFmpeg. Full playback also
requires a running Wrapper/asset server, legacy Flash runtime, and native
capture support. Report those constraints rather than claiming exact marker
alignment or cancellation of a blocked native capture read.
