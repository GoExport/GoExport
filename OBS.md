# Using OBS with GoExport

This guide explains how to use OBS (Open Broadcaster Software) with GoExport for recording your videos.

## Setting OBS Parameters in GoExport

GoExport does not allow direct modification of its configuration files. Instead, you must provide OBS connection details and other parameters using command line arguments when launching GoExport.

For example, to set the OBS WebSocket address, port, and password, run GoExport from the command line like this:

```bash
goexport --obs-websocket-address=localhost --obs-websocket-port=4455 --obs-websocket-password=your_password --obs-fps=60
```

Replace the values as needed for your OBS setup. All supported command line options are listed in the documentation or by running:

```bash
goexport --help
```

This ensures GoExport uses your desired OBS settings for recording.

## Prerequisites

## How GoExport Integrates with OBS

GoExport uses the OBS WebSocket API to automate recording. The integration is handled by the `obs_capture.py` module. Here’s what happens:

1. **Connect to OBS WebSocket**
   - GoExport connects to OBS using the address, port, and password specified in your configuration or parameters.
2. **Prepare OBS for Recording**
   - GoExport creates a new OBS profile and scene.
   - Sets video settings (resolution, FPS) based on your export parameters.
   - Adds a window capture source for "GoExport Viewer".
   - Mutes desktop and microphone audio inputs to avoid unwanted sound.
3. **Start Recording**
   - GoExport starts the OBS recording automatically.
   - Waits for OBS to confirm recording has started.
4. **Stop Recording**
   - GoExport stops the OBS recording when your export is finished.
   - Waits for OBS to confirm recording has stopped.
5. **Cleanup**
   - Unmutes audio inputs and removes the created scene/profile.

## Step-by-Step Instructions

### 1. Configure OBS WebSocket

- Open OBS Studio.
- Go to `Tools > WebSocket Server Settings`.
- Enable the server and set a password (default port is 4455).
- Make sure the address, port, and password match your GoExport configuration.

### 2. Start GoExport

- Run GoExport as usual.
- When you start an export, GoExport will automatically connect to OBS and control the recording process.

### 3. Troubleshooting

- If GoExport cannot connect to OBS, check:
  - OBS is running
  - WebSocket server is enabled
  - Address, port, and password are correct
- Check the GoExport logs for connection errors.

### 4. Advanced Usage

- You can customize the window capture source and video settings in GoExport’s configuration files.
- The OBS integration is managed in `modules/obs_capture.py`.

## Example Configuration

If you want a more permanent solution, type this in your data.json:

```json
{
  "obs_websocket_address": "localhost",
  "obs_websocket_port": 4455,
  "obs_websocket_password": "password"
}
```

Again replacing the values as needed for your OBS setup.

## More Information

- For details on OBS automation, see the code in `modules/obs_capture.py`.
- For general GoExport usage, see the [README.md](README.md).

If you need help, join the [Discord server](https://discord.gg/ejwJYtQDrS).
