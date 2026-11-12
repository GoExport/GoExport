# Anubis test fixtures

Local stand-ins for an Anubis-protected site, used by
`tests/test_verification_browser.py` to run Anubis' real challenge code in
GoExport's Chromium 87 without depending on a live website.

- `static/js/main.mjs`, `static/js/worker/sha256.mjs` and
  `static/locales/en.json` are unmodified copies of the files FlashThemes
  served on 2026-11-11 (Anubis `v1.28.3-0.20261106031446-f197f9a6235d+dirty`).
  Anubis is © Xe Iaso / Techaro and distributed under the MIT license, whose
  full notice is kept at the top of each JavaScript file.
- `challenge.html` and `error.html` follow the structure of the challenge and
  error pages that Anubis version served; the mock server fills in the
  challenge data.
- `site.html` stands in for the protected site after verification.
- `cloudflare_loader.html` imitates the hidden-iframe bot-management loader
  that Cloudflare's CDN injects into FlashThemes pages, so that it is covered
  by false-positive tests.
