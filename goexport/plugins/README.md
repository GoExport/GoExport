# What is this for?

> `goexport/plugins/README.md`

Optional export types

## future-proofing without pressure

You don’t need this yet, but planning it avoids rewrites.

```text
plugins/
├─ __init__.py
├─ registry.py
└─ goexport.py
```

- This lets you add:
- new export formats
- experimental features

Without touching core.

> Generated with OpenAI; may not be accurate with actual plans. (This will help us outline the project structure.)
