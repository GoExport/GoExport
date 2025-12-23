# What is this for?

> `goexport/core/README.md`

Does the actual work (no UI, no API)

## the engine (sacred ground)

This is where actual exporting happens.

### Rules

- ❌ no printing
- ❌ no sleeping loops
- ❌ no CLI args
- ❌ no HTTP
- ❌ no global state
- ✅ pure logic + subprocess calls
- ✅ emits events

```text
core/
├─ __init__.py
├─ export/
│  ├─ __init__.py
│  ├─ base.py        # Abstract exporter
│  ├─ goexport.py    # Current GoExport logic
│  └─ ffmpeg.py
├─ chromium/
│  └─ launcher.py
└─ events.py         # Progress + state events
```

### Example: base exporter

```python
class Exporter:
    async def run(self, context):
        raise NotImplementedError
```

> Generated with OpenAI; may not be accurate with actual plans. (This will help us outline the project structure.)
