# How threading fits cleanly

- `core/` → async subprocess streaming
- `app/` → asyncio loop + limited worker pool
- `interfaces/` → never block

The GUI can:

- subscribe to job updates
- poll via API
- receive events

Same backend.
