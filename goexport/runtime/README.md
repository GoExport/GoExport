# What is this for?

> `goexport/runtime/README.md`

Environment + dependency handling

## system reality checks

This is where you deal with the ugly real world.

```text
runtime/
├─ __init__.py
├─ deps.py           # ffmpeg, chromium, dotnet detection
├─ paths.py          # app data directories
├─ doctor.py         # validation logic
└─ bootstrap.py      # optional downloads
```

This layer:

- detects missing deps
- never performs exports
- never blocks the app logic

Think of it as the OS adapter.

> Generated with OpenAI; may not be accurate with actual plans. (This will help us outline the project structure.)
