# GoExport Linux Setup Guide

Complete guide for setting up GoExport on Linux, including dependencies, PATH configuration, and protocol handlers.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [PATH Configuration](#path-configuration)
- [Protocol Handler Setup](#protocol-handler-setup)
- [OBS Setup](#obs-setup)
- [GUI Troubleshooting](#gui-troubleshooting)
- [Distribution-Specific Notes](#distribution-specific-notes)

## System Requirements

**Minimum:**

- Linux kernel 4.15+
- 4GB RAM
- 5GB free disk space (includes dependencies)
- X11 or Wayland display server

**Recommended:**

- Linux kernel 5.0+
- 8GB RAM
- 20GB free disk space (for recordings)
- GPU with hardware video encoding support
- **OBS Studio with WebSocket plugin enabled** (for video capture)

**Supported Distributions:**

- Ubuntu 20.04+
- Debian 11+
- Fedora 35+
- Arch Linux (rolling)
- Linux Mint 20+
- Pop!\_OS 20.04+

## Installation

**Note:** Pre-built Linux binaries include all dependencies (FFmpeg, ungoogled-chromium with Flash, chromedriver). You do **not** need to install these separately.

### Method 1: Extract Pre-built Binary

The pre-built Linux portable tarball (`goexport_linux_portable_amd64.tar.gz`) contains:

- `GoExport` - Main executable (PyInstaller bundle)
- `dependencies/` - FFmpeg, ungoogled-chromium v87 with Flash Player PPAPI 34.0.0.137
- `assets/` - Outro videos and HTML templates
- `server/` - Local web server files
- `readme.md` and `LICENSE`

**All dependencies are bundled** - no separate installation of FFmpeg, Chrome, or Flash required.

```bash
# Download latest release
wget https://github.com/GoExport/GoExport/releases/latest/download/goexport_linux_portable_amd64.tar.gz

# Extract to /opt
sudo mkdir -p /opt/GoExport
sudo tar -xzf goexport_linux_portable_amd64.tar.gz -C /opt/GoExport

# Make executable
sudo chmod +x /opt/GoExport/GoExport

# Create symbolic link
sudo ln -s /opt/GoExport/GoExport /usr/local/bin/goexport

# Verify installation
goexport --version
```

### Method 2: Build from Source

**Note:** Building from source requires manually downloading dependencies (FFmpeg, ungoogled-chromium, Flash Player). The GitHub Actions workflow automates this - see `.github/workflows/release_and_build.yml` for exact commands.

```bash
# Install build dependencies
sudo apt install python3 python3-pip python3-venv git

# Clone repository
git clone https://github.com/GoExport/GoExport.git
cd GoExport

# Download dependencies (see workflow for URLs)
# FFmpeg: https://github.com/BtbN/FFmpeg-Builds/releases/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
# ungoogled-chromium: https://github.com/LordTwix/ungoogled-chromium-binaries/releases/download/87.0.4280.67-1.1/
# Flash Player: https://github.com/darktohka/clean-flash-builds/releases/download/v1.7/flash_player_patched_ppapi_linux.x86_64.tar.gz

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run from source
python main.py
```

### Method 3: AppImage (Not Available)

AppImage distribution is not currently available. Use Method 1 (pre-built binary) or Method 2 (build from source).

## Dependencies

### System Dependencies

#### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install required packages for pre-built binary
sudo apt install -y \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libnss3 \
    libglib2.0-0 \
    libfontconfig1 \
    libxrender1 \
    libdbus-1-3 \
    libgbm1 \
    libasound2

# For building from source, also install:
# sudo apt install python3 python3-pip python3-venv

# Install OBS Studio (recommended for video capture on Linux)
sudo apt install obs-studio
```

#### Fedora

```bash
# Install required packages for pre-built binary
sudo dnf install -y \
    qt6-qtbase \
    qt6-qtbase-gui \
    xcb-util-cursor \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    xcb-util-wm \
    nss \
    fontconfig \
    dbus-libs \
    mesa-libgbm \
    alsa-lib

# For building from source, also install:
# sudo dnf install python3 python3-pip

# Install OBS Studio (recommended for video capture on Linux)
sudo dnf install obs-studio
```

#### Arch Linux

```bash
# Install required packages for pre-built binary
sudo pacman -S --needed \
    qt6-base \
    xcb-util-cursor \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    xcb-util-wm \
    nss \
    fontconfig \
    dbus \
    mesa \
    alsa-lib

# For building from source, also install:
# sudo pacman -S python python-pip

# Install OBS Studio (recommended for video capture on Linux)
sudo pacman -S obs-studio
```

### Python Dependencies

**Only needed if building from source.** Pre-built binaries include all Python dependencies.

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install individually
pip install \
    PyQt6 \
    selenium \
    obs-websocket-py \
    requests \
    rich \
    psutil
```

### Bundled Dependencies

GoExport includes these dependencies in the `dependencies/` folder:

- **FFmpeg** - Video encoding/processing (from BtbN/FFmpeg-Builds)
- **ungoogled-chromium v87.0.4280.67-1.1** - Flash-enabled browser (includes chromedriver)
- **Flash Player PPAPI 34.0.0.137** - Patched Flash plugin (libpepflashplayer.so)

No additional installation needed for bundled dependencies. The pre-built portable archive includes everything required.

## PATH Configuration

To run GoExport from anywhere in the terminal, add it to your PATH.

### Method 1: Symbolic Link (Recommended)

```bash
# Create symlink in /usr/local/bin
sudo ln -s /opt/GoExport/GoExport /usr/local/bin/goexport

# Test
goexport --version
```

**Advantages:**

- Works immediately
- Available for all users
- Easy to remove/update

**Remove:**

```bash
sudo rm /usr/local/bin/goexport
```

### Method 2: Update PATH in Shell Profile

#### Bash (~/.bashrc)

```bash
# Add to ~/.bashrc
echo 'export PATH="/opt/GoExport:$PATH"' >> ~/.bashrc

# Reload
source ~/.bashrc

# Test
goexport --version
```

#### Zsh (~/.zshrc)

```bash
# Add to ~/.zshrc
echo 'export PATH="/opt/GoExport:$PATH"' >> ~/.zshrc

# Reload
source ~/.zshrc

# Test
goexport --version
```

#### Fish (~/.config/fish/config.fish)

```bash
# Add to Fish config
echo 'set -gx PATH /opt/GoExport $PATH' >> ~/.config/fish/config.fish

# Reload
source ~/.config/fish/config.fish

# Test
goexport --version
```

### Method 3: System-Wide PATH (All Users)

```bash
# Create profile script
sudo tee /etc/profile.d/goexport.sh > /dev/null << 'EOF'
export PATH="/opt/GoExport:$PATH"
EOF

# Make executable
sudo chmod +x /etc/profile.d/goexport.sh

# Reload (or logout/login)
source /etc/profile.d/goexport.sh

# Test
goexport --version
```

**Remove:**

```bash
sudo rm /etc/profile.d/goexport.sh
```

### Method 4: User-Local Binary Directory

```bash
# Create local bin directory
mkdir -p ~/.local/bin

# Add to PATH (if not already)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Create symlink
ln -s /opt/GoExport/GoExport ~/.local/bin/goexport

# Test
goexport --version
```

### Verify PATH Configuration

```bash
# Check if goexport is in PATH
which goexport

# Should output:
# /usr/local/bin/goexport
# or
# /opt/GoExport/GoExport
# or
# ~/.local/bin/goexport

# Test execution
goexport --version

# Should output version string, e.g.:
# GoExport v0.16.0
```

## Protocol Handler Setup

See [PROTOCOL_SETUP.md](PROTOCOL_SETUP.md#linux-setup) for complete protocol handler installation.

### Quick Setup

```bash
# Create desktop entry
mkdir -p ~/.local/share/applications

cat > ~/.local/share/applications/goexport-protocol.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=GoExport Protocol Handler
Exec=/opt/GoExport/GoExport --protocol %u
StartupNotify=false
MimeType=x-scheme-handler/goexport;
NoDisplay=true
Terminal=false
EOF

# Update desktop database
update-desktop-database ~/.local/share/applications/

# Register MIME type
xdg-mime default goexport-protocol.desktop x-scheme-handler/goexport

# Test
xdg-open 'goexport://local?video_id=test&resolution=720p'
```

**Note:** Adjust `/opt/GoExport/GoExport` to your actual installation path. If you extracted the portable tarball to a different location, update the path accordingly.

## OBS Setup

**OBS Studio is recommended for video capture on Linux.** Native screen-capture-recorder is Windows-only. While GoExport can run without OBS, you will need it configured to perform video exports.

### Install OBS Studio

#### Ubuntu/Debian

```bash
# Official PPA
sudo add-apt-repository ppa:obsproject/obs-studio
sudo apt update
sudo apt install obs-studio

# Or Flatpak
flatpak install flathub com.obsproject.Studio
```

#### Fedora

```bash
# RPM Fusion repositories
sudo dnf install obs-studio

# Or Flatpak
flatpak install flathub com.obsproject.Studio
```

#### Arch Linux

```bash
# Official repositories
sudo pacman -S obs-studio

# Or AUR for latest
yay -S obs-studio-git
```

### Configure OBS WebSocket

```bash
# Launch OBS
obs

# In OBS:
# 1. Go to Tools → WebSocket Server Settings
# 2. Check "Enable WebSocket server"
# 3. Note the port (default: 4455)
# 4. Set password (recommended)
# 5. Click OK
```

### Test OBS Connection

```bash
# Run GoExport with OBS settings
goexport --obs-websocket-address localhost \
         --obs-websocket-port 4455 \
         --obs-websocket-password "yourpassword"

# Or set in data.json
cat > data.json << 'EOF'
{
  "obs_websocket_address": "localhost",
  "obs_websocket_port": 4455,
  "obs_websocket_password": "yourpassword"
}
EOF
```

See [OBS.md](../OBS.md) and [CAPTURE_MODES.md](CAPTURE_MODES.md) for detailed OBS configuration.

## GUI Troubleshooting

### Issue: GUI Won't Load on X11/XOrg

**Symptoms:**

- GUI works on Wayland but not X11
- Error: "qt.qpa.plugin: Could not load the Qt platform plugin"
- Common on Linux Mint, VMware, older distributions

**Cause:** Missing Qt platform plugins for XCB (X11 backend)

**Solution:**

#### Ubuntu/Debian/Mint

```bash
sudo apt-get install -y \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    libxcb-cursor0
```

#### Fedora

```bash
sudo dnf install -y \
    xcb-util-cursor \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    xcb-util-wm \
    libxkbcommon-x11
```

#### Arch

```bash
sudo pacman -S --needed \
    xcb-util-cursor \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    xcb-util-wm \
    libxkbcommon-x11
```

### Issue: Wayland Session Issues

**If GUI works better on X11:**

```bash
# Force X11 session (Ubuntu/Debian)
sudo nano /etc/gdm3/custom.conf

# Uncomment this line:
WaylandEnable=false

# Restart display manager
sudo systemctl restart gdm3

# Or select "Ubuntu on Xorg" from login screen
```

### Issue: Missing Qt Platform Plugin

**Error:**

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
```

**Debug:**

```bash
# Check available plugins
ls /usr/lib/x86_64-linux-gnu/qt6/plugins/platforms/

# Should include:
# libqxcb.so

# If missing, reinstall Qt
sudo apt install --reinstall qt6-base-private-dev
```

**Set QT_DEBUG_PLUGINS for more info:**

```bash
export QT_DEBUG_PLUGINS=1
goexport
```

### Issue: Permission Denied

**Error:**

```
bash: /usr/local/bin/goexport: Permission denied
```

**Solution:**

```bash
# Make executable
sudo chmod +x /opt/GoExport/GoExport
chmod +x /usr/local/bin/goexport

# Or fix ownership
sudo chown $USER:$USER /opt/GoExport/GoExport
```

## Distribution-Specific Notes

### Ubuntu/Linux Mint

**Display Server:**

- Default: Wayland (Ubuntu 22.04+)
- Fallback: X11 (select at login)

**OBS Installation:**

```bash
sudo add-apt-repository ppa:obsproject/obs-studio
sudo apt update
sudo apt install obs-studio
```

**Common Issues:**

- Missing XCB libraries on Mint (see GUI Troubleshooting)
- AppArmor restrictions on `/opt` - use `sudo` for install

### Fedora/Red Hat

**Display Server:**

- Default: Wayland
- X11: Available as session option

**OBS Installation:**

```bash
# Enable RPM Fusion
sudo dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm

sudo dnf install obs-studio
```

**Common Issues:**

- SELinux may block execution from `/opt` - add exception or use `--permissive`

**SELinux Fix:**

```bash
# Temporarily permissive
sudo setenforce 0

# Or add exception
sudo semanage fcontext -a -t bin_t "/opt/GoExport/GoExport"
sudo restorecon -v /opt/GoExport/GoExport
```

### Arch Linux

**Display Server:**

- Varies by desktop environment
- KDE Plasma: Wayland default
- GNOME: Wayland default
- Xfce: X11 only

**OBS Installation:**

```bash
sudo pacman -S obs-studio

# Or latest from AUR
yay -S obs-studio-git
```

**Common Issues:**

- Rolling release may have Qt incompatibilities
- Use `obs-studio-git` for cutting-edge features

### Pop!\_OS

**Display Server:**

- Default: X11 (for NVIDIA compatibility)
- Wayland: Available on Intel/AMD

**OBS Installation:**

```bash
sudo apt install obs-studio
```

**Common Issues:**

- NVIDIA drivers may need configuration for OBS capture
- Use X11 session for best compatibility

## Performance Tips

### CPU/GPU Usage

```bash
# Monitor resource usage
htop

# Monitor GPU (NVIDIA)
nvidia-smi -l 1

# Monitor GPU (AMD)
radeontop

# Monitor GPU (Intel)
intel_gpu_top
```

### OBS Hardware Encoding

**NVIDIA (NVENC):**

```bash
# Verify NVENC support
ffmpeg -encoders | grep nvenc
```

**AMD (AMF/VAAPI):**

```bash
# Install VAAPI
sudo apt install vainfo
vainfo

# Install AMD drivers
sudo apt install mesa-va-drivers
```

**Intel (QuickSync):**

```bash
# Verify QuickSync
vainfo | grep -i "VA-API version"
```

### Disk I/O Optimization

```bash
# Use fast storage for output
# SSD recommended

# Mount tmpfs for temporary files (requires RAM)
sudo mount -t tmpfs -o size=4G tmpfs /tmp/goexport-temp

# Set output to tmpfs
goexport --output-dir /tmp/goexport-temp
```

## Uninstallation

```bash
# Remove binary
sudo rm /usr/local/bin/goexport

# Remove installation
sudo rm -rf /opt/GoExport

# Remove desktop entry
rm ~/.local/share/applications/goexport-protocol.desktop
update-desktop-database ~/.local/share/applications/

# Remove MIME association
xdg-mime default "" x-scheme-handler/goexport

# Remove PATH entries
# Edit ~/.bashrc, ~/.zshrc, etc. and remove GoExport lines

# Remove config
rm -rf ~/.config/GoExport
rm data.json
```

## See Also

- [PROTOCOL_SETUP.md](PROTOCOL_SETUP.md) - Protocol handler setup
- [OBS.md](../OBS.md) - OBS configuration
- [CAPTURE_MODES.md](CAPTURE_MODES.md) - Capture modes explained
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [README.md](../readme.md) - Main documentation
