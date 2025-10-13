# Example: Adding a New Service to GoExport

## Step-by-Step Guide

### 1. Open `config.py`

### 2. Find the `AVAILABLE_SERVICES` dictionary (around line 65)

### 3. Add your new service entry

Here's a template with all possible fields:

```python
AVAILABLE_SERVICES = {
    "local": { ... },  # Existing services
    "ft": { ... },

    # ADD YOUR NEW SERVICE HERE:
    "my_new_service": {
        # REQUIRED - This text appears in the UI
        "name": "My Custom Video Service",

        # What parameters are needed? (optional)
        "requires": {
            "movieId",           # Video/Movie ID is required
            "movieOwnerId",      # Owner ID is required
        },

        # Allowed domains for browser navigation (optional)
        "domain": [
            "https://mycustomservice.com",
        ],

        # Player URL pattern (optional)
        # Use {movie_id}, {owner_id}, {width}, {height}, {wide} placeholders
        "player": [
            "https://mycustomservice.com/player",
            (
                "watch?video={movie_id}"
                "&owner={owner_id}"
                "&w={width}&h={height}"
                "&widescreen={wide}"
            ),
        ],

        # Should GoExport start a local web server? (optional, default: False)
        "host": False,

        # Can this service be hosted locally? (optional, default: False)
        "hostable": False,

        # Use legacy editor mode? (optional, default: False)
        "legacy": False,

        # Hide from UI unless in debug mode? (optional, default: False)
        "testing": False,

        # Show even when testing=True if debug is on? (optional, default: False)
        "debug_required": False,

        # Window title for OBS/capture to find (optional)
        "window": "My Service Player",

        # JavaScript to inject after page loads (optional)
        "afterloadscripts": [
            "console.log('Custom script loaded');",
            "document.title = 'My Custom Title';",
        ]
    },
}
```

### 4. Save `config.py`

### 5. Restart GoExport

Your new service will automatically appear in the "Where is the video?" section!

## Real-World Example

Let's say you want to add support for a fictional service called "VideoMaker Pro":

```python
"videomaker_pro": {
    "name": "VideoMaker Pro",
    "requires": {
        "movieId",
    },
    "domain": [
        "https://videomaker.pro",
    ],
    "player": [
        "https://videomaker.pro/embed",
        "player.php?id={movie_id}&w={width}&h={height}"
    ],
    "host": False,
    "hostable": False,
    "legacy": False,
    "testing": False,
    "debug_required": False,
    "window": "VideoMaker Pro Player",
    "afterloadscripts": [
        "document.getElementById('ads').remove();",
        "document.fullscreenEnabled = true;",
    ]
},
```

That's it! The service will appear in the UI with the label "VideoMaker Pro".

## Quick Reference

**Minimal Example** (only required field):

```python
"my_service": {
    "name": "My Service Name",
},
```

**With Required Parameters**:

```python
"my_service": {
    "name": "My Service Name",
    "requires": {"movieId", "movieOwnerId"},
},
```

**Hidden (Testing) Service**:

```python
"my_service": {
    "name": "Beta Service (Testing)",
    "testing": True,  # Won't show in UI
},
```

## Troubleshooting

**Service doesn't appear in UI?**

- Check that you have a `"name"` field
- Make sure `"testing"` is not set to `True`
- Verify JSON syntax is correct (commas, quotes, brackets)

**Want to test before showing to users?**

- Set `"testing": True` while developing
- Remove or set to `False` when ready to release

**Need to debug?**

- Set `"testing": True` and `"debug_required": True`
- Service will only show when debug mode is enabled
