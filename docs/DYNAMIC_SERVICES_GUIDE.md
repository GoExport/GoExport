# Dynamic Services Loading Guide

## Overview

The UI now dynamically loads service options from `config.py`'s `AVAILABLE_SERVICES` dictionary, making it easy to add new services without modifying the UI files.

## What Changed

### 1. Main.ui (GUI Layout)

- **Before**: Had hardcoded radio buttons for "Wrapper Offline" and "FlashThemes"
- **After**: Empty layout container (`serviceButtonsLayout`) that gets populated at runtime

### 2. window.py (Python Logic)

Added three key components:

#### a. New Imports

```python
from PyQt6.QtWidgets import QRadioButton, QButtonGroup
```

#### b. New Instance Variables

```python
self.service_buttons = {}  # Dictionary mapping service_id -> QRadioButton
self.service_button_group = QButtonGroup(self)  # Groups buttons for mutual exclusivity
```

#### c. New Methods

**`setup_service_buttons()`**

- Reads `AVAILABLE_SERVICES` from config.py
- Creates a QRadioButton for each service
- Skips services without a "name" field
- Skips testing-only services (unless debug_required is True)
- First service is checked by default
- Connects each button to `on_service_changed()`

**`on_service_changed(service_id, checked)`**

- Called when user selects a different service
- Updates the controller with `set_lvm(service_id)`
- Saves selection to data.json

#### d. Updated Methods

**`reload_variables()`**

- Now dynamically finds and checks the saved service button
- Falls back to first available service if saved service doesn't exist

## How to Add a New Service

Simply add it to `config.py`'s `AVAILABLE_SERVICES` dictionary:

```python
AVAILABLE_SERVICES = {
    "local": { ... },
    "ft": { ... },
    "your_new_service": {
        "name": "Your Service Display Name",  # REQUIRED - Shows in UI
        "requires": {"movieId"},
        "domain": ["https://yourservice.com"],
        "player": ["https://yourservice.com/player"],
        "host": False,
        "hostable": False,
        "legacy": False,
        "testing": False,  # Set to True to hide from UI
        "debug_required": False,
        "window": "Your Service Window Title",
        "afterloadscripts": []
    }
}
```

The UI will automatically:

1. Create a radio button with the "name" field as the label
2. Handle selection and saving
3. Pass the service_id ("your_new_service") to the controller

## Service Dictionary Fields

| Field              | Required | Description                                                      |
| ------------------ | -------- | ---------------------------------------------------------------- |
| `name`             | **YES**  | Display name in the UI (e.g., "Wrapper: Offline")                |
| `testing`          | No       | If `True`, hides from UI unless `debug_required` is also `True`  |
| `requires`         | No       | Set of required parameters (e.g., `{"movieId", "movieOwnerId"}`) |
| `domain`           | No       | List of allowed domains for navigation                           |
| `player`           | No       | Player URL patterns                                              |
| `host`             | No       | Whether to start local server                                    |
| `hostable`         | No       | Whether service can be hosted locally                            |
| `legacy`           | No       | Use legacy editor mode                                           |
| `debug_required`   | No       | Show even if testing=True when debug enabled                     |
| `window`           | No       | Window title for capture                                         |
| `afterloadscripts` | No       | JavaScript to inject after page load                             |

## Testing

After adding a new service, simply restart the application. The new service will appear as a radio button option in the "Where is the video?" section.

## Benefits

✅ **No UI file editing needed** - Just update config.py
✅ **Automatic UI generation** - Radio buttons created at runtime
✅ **Easy maintenance** - Single source of truth in config.py
✅ **Backward compatible** - Existing services work without changes
✅ **Persistent selection** - User's choice saved to data.json
