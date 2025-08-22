import helpers
import subprocess
import atexit
import signal
import time
import json
import socket
import base64
import threading
import struct
import hashlib
from modules.logger import logger


class OBSWebSocketClient:
    """Simple OBS WebSocket client implementation"""
    
    def __init__(self, host="localhost", port=4455, password=None):
        self.host = host
        self.port = port
        self.password = password
        self.connected = False
        self.request_id = 0
        self.sock = None
        
    def _create_websocket_key(self):
        """Create WebSocket key for handshake"""
        return base64.b64encode(b'obs-websocket-key-16').decode()
    
    def _create_accept_key(self, key):
        """Create WebSocket accept key for validation"""
        magic = "258EAFA5-E549-EFB8-96E4-C27C7F24D6E0"
        sha1 = hashlib.sha1((key + magic).encode()).digest()
        return base64.b64encode(sha1).decode()
    
    def _send_frame(self, data, opcode=1):
        """Send WebSocket frame"""
        if not self.sock:
            return False
            
        try:
            payload = data.encode() if isinstance(data, str) else data
            payload_len = len(payload)
            
            # Create frame header
            frame = bytearray()
            frame.append(0x80 | opcode)  # FIN + opcode
            
            if payload_len < 126:
                frame.append(payload_len)
            elif payload_len < 65536:
                frame.append(126)
                frame.extend(struct.pack('>H', payload_len))
            else:
                frame.append(127)
                frame.extend(struct.pack('>Q', payload_len))
            
            frame.extend(payload)
            self.sock.send(frame)
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket frame: {e}")
            return False
    
    def connect(self):
        """Connect to OBS WebSocket server"""
        try:
            # Create socket connection
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            
            # Create WebSocket handshake
            key = self._create_websocket_key()
            handshake = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"Sec-WebSocket-Protocol: obswebsocket.json\r\n"
                f"\r\n"
            )
            
            self.sock.send(handshake.encode())
            response = self.sock.recv(1024).decode()
            
            if "101 Switching Protocols" in response:
                self.connected = True
                logger.info("Connected to OBS WebSocket")
                return True
            else:
                logger.error(f"WebSocket handshake failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket: {e}")
            return False
    
    def send_request(self, request_type, request_data=None):
        """Send request to OBS"""
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
            
        self.request_id += 1
        message = {
            "op": 6,  # Request
            "d": {
                "requestType": request_type,
                "requestId": str(self.request_id),
                "requestData": request_data or {}
            }
        }
        
        logger.debug(f"Sending OBS request: {request_type}")
        return self._send_frame(json.dumps(message))
    
    def start_recording(self):
        """Start OBS recording"""
        return self.send_request("StartRecord")
    
    def stop_recording(self):
        """Stop OBS recording"""
        return self.send_request("StopRecord")
    
    def create_window_source(self, scene_name, source_name, window_title):
        """Create window capture source in OBS"""
        request_data = {
            "sceneName": scene_name,
            "sourceName": source_name,
            "sourceKind": "window_capture",
            "sourceSettings": {
                "window": window_title
            }
        }
        return self.send_request("CreateSource", request_data)
    
    def set_current_scene(self, scene_name):
        """Set the current scene in OBS"""
        request_data = {"sceneName": scene_name}
        return self.send_request("SetCurrentScene", request_data)
    
    def disconnect(self):
        """Disconnect from OBS"""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.connected = False
        logger.info("Disconnected from OBS WebSocket")


class OBSCapture:
    """OBS-based capture implementation to replace ScreenCaptureRecorder"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.startup_delay = None
        self.ended_delay = None
        self.obs_client = None
        self.obs_process = None
        self.recording_active = False
        
        atexit.register(self.cleanup)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.cleanup()
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)

    def cleanup(self):
        """Clean up OBS resources"""
        if self.recording_active:
            try:
                logger.info("Stopping OBS recording due to application exit")
                self.stop()
            except Exception as e:
                logger.error(f"Error stopping OBS recording: {e}")
        
        if self.obs_client:
            try:
                self.obs_client.disconnect()
            except Exception:
                pass

    def _find_chromium_window(self):
        """Find the Chromium window title for OBS window capture"""
        try:
            if helpers.os_is_windows():
                # Use Windows-specific method to find Chromium window
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'exe']):
                        try:
                            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                                # Found Chromium process, try to get window title
                                return f"[chrome.exe]: GoExport"
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except ImportError:
                    logger.warning("psutil not available, using default window title")
            
            # Fallback window title
            return "[chrome.exe]: GoExport"
        except Exception as e:
            logger.error(f"Error finding Chromium window: {e}")
            return "[chrome.exe]: GoExport"

    def _ensure_obs_running(self):
        """Ensure OBS Studio is running"""
        try:
            if helpers.os_is_windows():
                # Check if OBS is running
                try:
                    import psutil
                    obs_running = False
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if proc.info['name'] and 'obs' in proc.info['name'].lower():
                                obs_running = True
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    if not obs_running:
                        logger.warning("OBS Studio is not running. Please start OBS Studio manually.")
                        return False
                    return True
                except ImportError:
                    logger.warning("psutil not available, assuming OBS is running")
                    return True
            else:
                logger.error("OBS integration currently only supports Windows")
                return False
        except Exception as e:
            logger.error(f"Error checking OBS: {e}")
            return False

    def start(self, output: str, width: int, height: int):
        """Start OBS recording"""
        try:
            # Ensure OBS is running
            if not self._ensure_obs_running():
                logger.error("OBS Studio is not available")
                return False

            # Get OBS WebSocket configuration
            host = helpers.get_config("OBS_WEBSOCKET_HOST", "localhost")
            port = helpers.get_config("OBS_WEBSOCKET_PORT", 4455)
            password = helpers.get_config("OBS_WEBSOCKET_PASSWORD", None)

            # Connect to OBS WebSocket
            self.obs_client = OBSWebSocketClient(host, port, password)
            if not self.obs_client.connect():
                logger.error("Failed to connect to OBS WebSocket")
                return False

            # Find Chromium window for capture
            window_title = self._find_chromium_window()
            logger.info(f"Capturing window: {window_title}")

            # Setup OBS scene and source for window capture
            scene_name = "GoExport_Scene"
            source_name = "Chromium_Capture"
            
            # Set current scene
            self.obs_client.set_current_scene(scene_name)
            
            # Create window capture source
            self.obs_client.create_window_source(scene_name, source_name, window_title)

            # Start recording
            offset = helpers.get_timestamp("OBS starting")
            
            if not self.obs_client.start_recording():
                logger.error("Failed to start OBS recording")
                return False

            self.start_time = helpers.get_timestamp("OBS started")
            self.recording_active = True
            
            # Calculate startup delay
            self.startup_delay = self.start_time - offset
            
            logger.info("OBS recording started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting OBS recording: {e}")
            return False

    def stop(self):
        """Stop OBS recording"""
        try:
            if not self.recording_active:
                logger.warning("OBS recording is not active")
                return True

            offset = helpers.get_timestamp("OBS stopping")
            
            if self.obs_client and self.obs_client.connected:
                if not self.obs_client.stop_recording():
                    logger.error("Failed to stop OBS recording")
                    return False
            
            self.end_time = helpers.get_timestamp("OBS ended")
            self.ended_delay = self.end_time - offset
            self.recording_active = False
            
            # Disconnect from OBS
            if self.obs_client:
                self.obs_client.disconnect()
                
            logger.info("OBS recording stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping OBS recording: {e}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()