# GoExport Protocol Handler Setup

This guide explains how to register the `goexport://` protocol handler on Windows, Linux, and macOS, enabling one-click video exports from browsers and other applications.

## Table of Contents

- [Overview](#overview)
- [Windows Setup](#windows-setup)
- [Linux Setup](#linux-setup)
- [macOS Setup](#macos-setup)
- [Testing the Protocol](#testing-the-protocol)
- [Troubleshooting](#troubleshooting)

## Overview

The `goexport://` protocol allows external applications to launch GoExport with pre-configured parameters. This is useful for:

- Browser extensions
- Web applications
- Desktop integrations
- Quick-launch shortcuts

**Protocol URL Format:**

```
goexport://local?video_id=123&resolution=1080p&aspect_ratio=16:9&no_input=true
```

See [PARAMETERS.md](PARAMETERS.md) for full protocol syntax documentation.

---

## Windows Setup

### Method 1: Registry Script (Recommended)

#### Step 1: Create Registry File

Create a file named `register_goexport_protocol.reg` with the following content:

```reg
Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\goexport]
@="URL:GoExport Protocol"
"URL Protocol"=""

[HKEY_CLASSES_ROOT\goexport\DefaultIcon]
@="C:\\Program Files\\GoExport\\GoExport.exe,1"

[HKEY_CLASSES_ROOT\goexport\shell]

[HKEY_CLASSES_ROOT\goexport\shell\open]

[HKEY_CLASSES_ROOT\goexport\shell\open\command]
@="\"C:\\Program Files\\GoExport\\GoExport.exe\" --protocol \"%1\""
```

**Important:** Replace `C:\\Program Files\\GoExport\\GoExport.exe` with your actual GoExport installation path.

#### Step 2: Run Registry File

1. Right-click the `.reg` file
2. Select "Merge" or "Open"
3. Click "Yes" to confirm UAC prompt
4. Click "OK" when complete

#### Step 3: Verify Installation

Open Command Prompt and run:

```cmd
reg query HKEY_CLASSES_ROOT\goexport
```

You should see the registered protocol information.

### Method 2: PowerShell Script

Create a PowerShell script `Register-GoExportProtocol.ps1`:

```powershell
# Register-GoExportProtocol.ps1
# Run as Administrator

$goexportPath = "C:\Program Files\GoExport\GoExport.exe"

# Verify GoExport exists
if (-not (Test-Path $goexportPath)) {
    Write-Error "GoExport not found at: $goexportPath"
    Write-Host "Please update the path in this script."
    exit 1
}

# Create protocol registry keys
$protocolKey = "HKCR:\goexport"

New-Item -Path "HKCR:\goexport" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\goexport" -Name "(Default)" -Value "URL:GoExport Protocol"
Set-ItemProperty -Path "HKCR:\goexport" -Name "URL Protocol" -Value ""

New-Item -Path "HKCR:\goexport\DefaultIcon" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\goexport\DefaultIcon" -Name "(Default)" -Value "$goexportPath,1"

New-Item -Path "HKCR:\goexport\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\goexport\shell\open\command" -Name "(Default)" -Value "`"$goexportPath`" --protocol `"%1`""

Write-Host "GoExport protocol registered successfully!" -ForegroundColor Green
Write-Host "Test with: start goexport://local?video_id=test" -ForegroundColor Cyan
```

Run as Administrator:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\Register-GoExportProtocol.ps1
```

### Method 3: Manual Registry Edit

1. Press `Win + R`, type `regedit`, press Enter
2. Navigate to `HKEY_CLASSES_ROOT`
3. Right-click → New → Key → Name it `goexport`
4. Set default value to `URL:GoExport Protocol`
5. Create new String Value: `URL Protocol` (leave value empty)
6. Create key structure: `goexport\shell\open\command`
7. Set command default value to:
   ```
   "C:\Program Files\GoExport\GoExport.exe" --protocol "%1"
   ```

### Uninstalling (Windows)

Create `unregister_goexport_protocol.reg`:

```reg
Windows Registry Editor Version 5.00

[-HKEY_CLASSES_ROOT\goexport]
```

Or use PowerShell:

```powershell
Remove-Item -Path "HKCR:\goexport" -Recurse -Force
```

---

## Linux Setup

### Method 1: Desktop Entry File (Recommended)

#### Step 1: Create Desktop Entry

Create file `~/.local/share/applications/goexport-protocol.desktop`:

```desktop
[Desktop Entry]
Type=Application
Name=GoExport Protocol Handler
Exec=/opt/GoExport/GoExport --protocol %u
StartupNotify=false
MimeType=x-scheme-handler/goexport;
NoDisplay=true
Terminal=false
```

**Important:** Replace `/opt/GoExport/GoExport` with your actual GoExport installation path.

#### Step 2: Update Desktop Database

```bash
update-desktop-database ~/.local/share/applications/
```

#### Step 3: Register MIME Type

```bash
xdg-mime default goexport-protocol.desktop x-scheme-handler/goexport
```

#### Step 4: Verify Registration

```bash
xdg-mime query default x-scheme-handler/goexport
```

Should output: `goexport-protocol.desktop`

### Method 2: System-Wide Installation (Requires Root)

For all users on the system:

```bash
sudo tee /usr/share/applications/goexport-protocol.desktop > /dev/null << 'EOF'
[Desktop Entry]
Type=Application
Name=GoExport Protocol Handler
Exec=/opt/GoExport/GoExport --protocol %u
StartupNotify=false
MimeType=x-scheme-handler/goexport;
NoDisplay=true
Terminal=false
EOF

sudo update-desktop-database /usr/share/applications/
sudo xdg-mime default goexport-protocol.desktop x-scheme-handler/goexport
```

### Method 3: Bash Script Installer

Create `install_goexport_protocol.sh`:

```bash
#!/bin/bash
# install_goexport_protocol.sh

GOEXPORT_PATH="/opt/GoExport/GoExport"
DESKTOP_FILE="$HOME/.local/share/applications/goexport-protocol.desktop"

# Check if GoExport exists
if [ ! -f "$GOEXPORT_PATH" ]; then
    echo "Error: GoExport not found at $GOEXPORT_PATH"
    echo "Please update GOEXPORT_PATH in this script."
    exit 1
fi

# Create desktop file
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=GoExport Protocol Handler
Exec=$GOEXPORT_PATH --protocol %u
StartupNotify=false
MimeType=x-scheme-handler/goexport;
NoDisplay=true
Terminal=false
EOF

# Update desktop database
update-desktop-database "$HOME/.local/share/applications/"

# Register MIME type
xdg-mime default goexport-protocol.desktop x-scheme-handler/goexport

echo "✓ GoExport protocol registered successfully!"
echo "Test with: xdg-open 'goexport://local?video_id=test'"
```

Make executable and run:

```bash
chmod +x install_goexport_protocol.sh
./install_goexport_protocol.sh
```

### Adding GoExport to PATH (Linux)

To run GoExport from anywhere in the terminal:

#### Method 1: Symbolic Link

```bash
sudo ln -s /opt/GoExport/GoExport /usr/local/bin/goexport
```

Test:

```bash
goexport --version
```

#### Method 2: Update PATH in Shell Profile

For Bash (`~/.bashrc`):

```bash
echo 'export PATH="/opt/GoExport:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

For Zsh (`~/.zshrc`):

```bash
echo 'export PATH="/opt/GoExport:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

For Fish (`~/.config/fish/config.fish`):

```bash
echo 'set -gx PATH /opt/GoExport $PATH' >> ~/.config/fish/config.fish
source ~/.config/fish/config.fish
```

#### Method 3: System-Wide PATH (Requires Root)

```bash
sudo tee /etc/profile.d/goexport.sh > /dev/null << 'EOF'
export PATH="/opt/GoExport:$PATH"
EOF

# Reload profile
source /etc/profile
```

### Uninstalling (Linux)

```bash
# Remove desktop file
rm ~/.local/share/applications/goexport-protocol.desktop

# Update database
update-desktop-database ~/.local/share/applications/

# Remove MIME association
xdg-mime default "" x-scheme-handler/goexport

# Remove from PATH (if using symbolic link)
sudo rm /usr/local/bin/goexport
```

---

## macOS Setup

### Method 1: Info.plist Modification

If GoExport is packaged as a `.app` bundle:

#### Step 1: Edit Info.plist

Open `GoExport.app/Contents/Info.plist` and add:

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLName</key>
        <string>GoExport Protocol</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>goexport</string>
        </array>
    </dict>
</array>
```

#### Step 2: Rebuild Launch Services Database

```bash
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user
```

### Method 2: AppleScript Application

Create an AppleScript wrapper:

```applescript
on open location url_string
    do shell script "/Applications/GoExport.app/Contents/MacOS/GoExport --protocol " & quoted form of url_string & " &> /dev/null &"
end open location
```

Save as Application with "Stay open after run handler" enabled.

### Method 3: Shell Script with Launch Agent

Create `/usr/local/bin/goexport-protocol-handler`:

```bash
#!/bin/bash
/Applications/GoExport.app/Contents/MacOS/GoExport --protocol "$1"
```

Make executable:

```bash
chmod +x /usr/local/bin/goexport-protocol-handler
```

Create Launch Agent `~/Library/LaunchAgents/com.goexport.protocol.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.goexport.protocol</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/goexport-protocol-handler</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load the agent:

```bash
launchctl load ~/Library/LaunchAgents/com.goexport.protocol.plist
```

### Adding GoExport to PATH (macOS)

#### Method 1: Symbolic Link

```bash
sudo ln -s /Applications/GoExport.app/Contents/MacOS/GoExport /usr/local/bin/goexport
```

#### Method 2: Update PATH

For Bash/Zsh (`~/.zshrc` or `~/.bash_profile`):

```bash
echo 'export PATH="/Applications/GoExport.app/Contents/MacOS:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Uninstalling (macOS)

```bash
# Remove launch agent
launchctl unload ~/Library/LaunchAgents/com.goexport.protocol.plist
rm ~/Library/LaunchAgents/com.goexport.protocol.plist

# Remove handler script
rm /usr/local/bin/goexport-protocol-handler

# Rebuild launch services
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user
```

---

## Testing the Protocol

### Windows

**Command Prompt:**

```cmd
start goexport://local?video_id=test&resolution=720p
```

**PowerShell:**

```powershell
Start-Process "goexport://local?video_id=test&resolution=720p"
```

**Browser:**
Paste in address bar:

```
goexport://local?video_id=test&resolution=720p&no_input=true
```

### Linux

**Terminal:**

```bash
xdg-open 'goexport://local?video_id=test&resolution=720p'
```

**Browser:**
Navigate to:

```
goexport://local?video_id=test&resolution=720p&no_input=true
```

### macOS

**Terminal:**

```bash
open 'goexport://local?video_id=test&resolution=720p'
```

**Browser:**
Navigate to:

```
goexport://local?video_id=test&resolution=720p&no_input=true
```

### HTML Link Test

Create `test_protocol.html`:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>GoExport Protocol Test</title>
  </head>
  <body>
    <h1>GoExport Protocol Handler Test</h1>

    <h2>Test Links:</h2>

    <p>
      <a
        href="goexport://local?video_id=test123&resolution=720p&aspect_ratio=16:9"
      >
        Export Local Video (720p)
      </a>
    </p>

    <p>
      <a
        href="goexport://ft?video_id=abc&user_id=xyz&resolution=1080p&no_input=true"
      >
        Export FlashThemes (1080p, No Input)
      </a>
    </p>

    <p>
      <a
        href="goexport://local?video_id=demo&resolution=4k&aspect_ratio=16:9&use_outro=true"
      >
        Export with Outro (4K)
      </a>
    </p>

    <h2>JavaScript Test:</h2>
    <button
      onclick="window.location='goexport://local?video_id=js_test&resolution=1080p'"
    >
      Launch via JavaScript
    </button>
  </body>
</html>
```

Open in browser and click links to test protocol.

---

## Troubleshooting

### Windows

#### Problem: "Windows cannot find 'goexport://...'"

**Solution:**

- Verify registry keys exist: `reg query HKEY_CLASSES_ROOT\goexport`
- Check path in registry command value
- Restart browser after registration

#### Problem: Protocol launches but GoExport doesn't start

**Solution:**

- Verify GoExport.exe path is correct
- Check if path contains spaces (must be quoted)
- Run GoExport.exe manually to check for errors

#### Problem: UAC prompts every time

**Solution:**

- Run GoExport.exe as administrator once
- Add GoExport to Windows Defender exclusions
- Create compatibility shim to disable UAC prompt

### Linux

#### Problem: `xdg-mime query` returns nothing

**Solution:**

```bash
# Verify desktop file exists
ls ~/.local/share/applications/goexport-protocol.desktop

# Check desktop file syntax
desktop-file-validate ~/.local/share/applications/goexport-protocol.desktop

# Re-register
xdg-mime default goexport-protocol.desktop x-scheme-handler/goexport
```

#### Problem: Browser asks which application to use

**Solution:**

```bash
# Set default explicitly
xdg-settings set default-url-scheme-handler goexport goexport-protocol.desktop

# Update MIME cache
update-mime-database ~/.local/share/mime
```

#### Problem: Terminal not found error

**Solution:**
Edit desktop file and change:

```
Terminal=false
```

Or ensure GoExport can run headless with `--no-input`.

#### Problem: Permission denied when executing

**Solution:**

```bash
# Make GoExport executable
chmod +x /opt/GoExport/GoExport

# Verify
ls -l /opt/GoExport/GoExport
```

### macOS

#### Problem: "No application is configured to open goexport://"

**Solution:**

- Rebuild LaunchServices database
- Check Info.plist exists and is valid
- Verify app bundle is signed (may require Developer ID)

#### Problem: Gatekeeper blocks execution

**Solution:**

```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine /Applications/GoExport.app

# Or allow in System Preferences
# System Preferences → Security & Privacy → Allow GoExport
```

#### Problem: AppleScript handler doesn't respond

**Solution:**

- Ensure "Stay open after run handler" is enabled
- Check Console.app for errors
- Verify script has accessibility permissions

### All Platforms

#### Problem: Parameters not passed correctly

**Solution:**

- URL-encode special characters (spaces, colons, etc.)
- Quote the entire URL in shell commands
- Use [PARAMETERS.md](PARAMETERS.md) for correct syntax

#### Problem: Browser security warning

**Solution:**

- Some browsers require user confirmation for custom protocols
- Firefox: `about:config` → `network.protocol-handler.external.goexport` → `true`
- Chrome: Settings → Privacy and security → Site Settings → Permissions

#### Problem: Multiple GoExport instances launch

**Solution:**

- Ensure only one protocol handler is registered
- Check for duplicate registrations
- Implement single-instance check in GoExport code

---

## Security Considerations

### URL Injection Protection

The protocol handler passes user-controlled data to GoExport. Ensure:

1. **Input Validation**: GoExport validates all parameters
2. **No Shell Injection**: Parameters are parsed safely
3. **Path Restrictions**: No arbitrary file system access

### Trusted Sources Only

Only trigger protocol URLs from trusted sources:

- Official web interfaces
- Verified browser extensions
- Known applications

### Firewall Rules

If using OBS WebSocket with protocol URLs, ensure:

- OBS password is required
- WebSocket only accepts local connections
- Firewall blocks external OBS access

---

## Browser Integration Examples

### Chrome Extension Manifest v3

```json
{
  "name": "GoExport Helper",
  "version": "1.0",
  "manifest_version": 3,
  "permissions": ["tabs"],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_title": "Export with GoExport"
  }
}
```

**background.js:**

```javascript
chrome.action.onClicked.addListener((tab) => {
  const videoId = extractVideoId(tab.url);
  const protocolUrl = `goexport://local?video_id=${videoId}&resolution=1080p&no_input=true`;
  chrome.tabs.create({ url: protocolUrl });
});

function extractVideoId(url) {
  // Your video ID extraction logic
  return "extracted_id";
}
```

### Firefox Extension

Similar to Chrome, but use `browser` namespace instead of `chrome`.

### Bookmarklet

```javascript
javascript: (function () {
  var videoId = prompt("Enter Video ID:");
  if (videoId) {
    window.location =
      "goexport://local?video_id=" +
      encodeURIComponent(videoId) +
      "&resolution=1080p";
  }
})();
```

---

## See Also

- [PARAMETERS.md](PARAMETERS.md) - Complete parameter reference
- [CONFIGURATION.md](CONFIGURATION.md) - GoExport configuration guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting guide
- [README.md](../readme.md) - Main documentation
