# What is this for?

> `goexport/app/README.md`

Jobs, state, orchestration

## the brain (most important)

This is where your platform lives.

```text
app/
├─ __init__.py
├─ jobs/
│  ├─ job.py
│  ├─ manager.py
│  └─ states.py
├─ progress/
│  ├─ tracker.py
│  └─ eta.py
├─ scheduler.py
└─ context.py
```

### This layer is responsible for

- managing jobs
- threading / async orchestration
- progress aggregation
- cancellation
- persistence (optional later)

### Job object (example)

```python
class Job:
    id
    exporter
    state
    progress
    started_at
```

This is what everything else talks to.

> Generated with OpenAI; may not be accurate with actual plans. (This will help us outline the project structure.)
