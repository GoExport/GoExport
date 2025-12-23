# What is this for?

> `goexport/interfaces/README.md`

CLI, API, GUI adapters

## how humans & machines talk to it

These are thin shells. No logic.

```text
interfaces/
├─ cli/
│  ├─ main.py
│  └─ commands.py
├─ api/
│  ├─ server.py
│  └─ routes.py
└─ gui/
   └─ launcher.py
```

### Important rule

Interfaces never call core directly.

They only call:

```python
JobManager.submit(...)
```

That’s it.

> Generated with OpenAI; may not be accurate with actual plans. (This will help us outline the project structure.)
