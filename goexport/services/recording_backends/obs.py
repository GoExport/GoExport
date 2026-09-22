"""OBS Studio capture backend using obsws-python and obs-websocket v5."""

from __future__ import annotations

import logging
import os
import platform
import time
import uuid
from pathlib import Path

from goexport import config
from goexport.services.recording_backends.base import CaptureArtifacts, CaptureResult

logger = logging.getLogger(__name__)

GOEXPORT_SCENE = "GoExport Recording"
GOEXPORT_VIDEO_INPUT = "GoExport Chromium Capture"
GOEXPORT_AUDIO_INPUT = "GoExport System Audio"
OWNERSHIP_SLOT = "goexport.recording_backend.v1"
REQUIRED_REQUESTS = {
    "GetVersion",
    "GetProfileList",
    "SetCurrentProfile",
    "CreateProfile",
    "GetSceneCollectionList",
    "SetCurrentSceneCollection",
    "CreateSceneCollection",
    "GetPersistentData",
    "SetPersistentData",
    "SetProfileParameter",
    "SetVideoSettings",
    "GetVideoSettings",
    "SetRecordDirectory",
    "GetInputKindList",
    "GetInputList",
    "CreateInput",
    "SetInputSettings",
    "RemoveInput",
    "GetInputPropertiesListPropertyItems",
    "GetSceneList",
    "CreateScene",
    "SetCurrentProgramScene",
    "GetSceneItemId",
    "SetSceneItemTransform",
    "GetRecordStatus",
    "StartRecord",
    "StopRecord",
}
RECORDING_FINALIZE_TIMEOUT_SECONDS = 10.0
RECORDING_FINALIZE_POLL_SECONDS = 0.1


def _value(item, name, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


class OBSBackend:
    def __init__(self, args, reporter, ffmpeg_path, window_title, client_factory=None):
        self.args = args
        self.reporter = reporter
        self.ffmpeg_path = ffmpeg_path
        self.window_title = window_title
        self.client_factory = client_factory
        self.client = None
        self.artifacts = None
        self.original_profile = None
        self.original_scene_collection = None
        self.recording_started = False
        self.result = None
        self.run_id = uuid.uuid4().hex

    def check_available(self, display=None):
        if config.SYSTEM not in {"Darwin", "Windows", "Linux"}:
            raise RuntimeError(
                f"The OBS capture backend does not support {config.SYSTEM}."
            )
        if config.SYSTEM == "Linux" and not display:
            raise RuntimeError(
                "The OBS backend requires an existing X11 DISPLAY on Linux so "
                "OBS and Chromium can see the same window."
            )
        if (
            config.SYSTEM == "Darwin"
            and platform.mac_ver()[0]
            and tuple(int(part) for part in platform.mac_ver()[0].split(".")[:2])
            < (13, 0)
        ):
            raise RuntimeError("OBS window audio capture requires macOS 13 or newer.")

    def _connect(self):
        if self.client_factory is None:
            # obsws-python 1.8 logs its password at INFO during construction.
            logging.getLogger("obsws_python").setLevel(logging.WARNING)
            logging.getLogger("obsws_python.baseclient").setLevel(logging.WARNING)
            import obsws_python

            self.client_factory = obsws_python.ReqClient
        password = os.environ.get("GOEXPORT_OBS_PASSWORD", "")
        try:
            self.client = self.client_factory(
                host=self.args.obs_host,
                port=self.args.obs_port,
                password=password,
                timeout=10,
            )
        except Exception as error:
            raise RuntimeError(
                f"Could not connect to OBS WebSocket at "
                f"{self.args.obs_host}:{self.args.obs_port}. Ensure OBS is running "
                "and WebSocket Server is enabled."
            ) from error

    def prepare(self, service, driver, artifacts: CaptureArtifacts):
        self.artifacts = artifacts
        artifacts.obs_directory.mkdir(parents=True, exist_ok=True)
        self._connect()
        try:
            self._check_protocol()
            self._select_owned_resources()
            self._configure_profile()
            self._configure_scene_and_source()
        except BaseException:
            self.close()
            raise

    def _check_protocol(self):
        version = self.client.get_version()
        available = set(version.available_requests)
        missing = sorted(REQUIRED_REQUESTS - available)
        if version.rpc_version < 1 or missing:
            detail = f" Missing requests: {', '.join(missing)}." if missing else ""
            raise RuntimeError("OBS WebSocket v5 is incompatible." + detail)

    def _select_owned_resources(self):
        profiles = self.client.get_profile_list()
        self.original_profile = profiles.current_profile_name
        profile_name = self.args.obs_profile
        existing_owned_profile = profile_name in profiles.profiles
        force_profile = getattr(self.args, "obs_force_profile", False)
        if existing_owned_profile:
            self.client.set_current_profile(profile_name)
            marker = self.client.get_persistent_data(
                "OBS_WEBSOCKET_DATA_REALM_PROFILE", OWNERSHIP_SLOT
            )
            expected_marker = {
                "owner": "GoExport",
                "version": 1,
                "sceneCollection": self.args.obs_scene_collection,
            }
            if marker.slot_value != expected_marker and not force_profile:
                raise RuntimeError(
                    f"OBS profile {profile_name!r} is not owned by GoExport. "
                    "Choose another --obs-profile name or pass --obs-force-profile "
                    "to reuse and reconfigure it."
                )
        else:
            self.client.create_profile(profile_name)
            expected_marker = {
                "owner": "GoExport",
                "version": 1,
                "sceneCollection": self.args.obs_scene_collection,
            }
        self.client.set_persistent_data(
            "OBS_WEBSOCKET_DATA_REALM_PROFILE",
            OWNERSHIP_SLOT,
            expected_marker,
        )

        collections = self.client.get_scene_collection_list()
        self.original_scene_collection = collections.current_scene_collection_name
        collection_name = self.args.obs_scene_collection
        if collection_name in collections.scene_collections:
            if not existing_owned_profile and not force_profile:
                raise RuntimeError(
                    f"OBS scene collection {collection_name!r} already exists and "
                    "cannot be proven to be owned by GoExport. Choose another "
                    "--obs-scene-collection name or pass --obs-force-profile."
                )
            self.client.set_current_scene_collection(collection_name)
        else:
            self.client.create_scene_collection(collection_name)

    def _configure_profile(self):
        width, height = self.args.resolution
        status = self.client.get_record_status()
        if status.output_active:
            raise RuntimeError(
                "OBS is already recording. Stop the active recording before using GoExport."
            )
        for name, value in (
            ("BaseCX", width),
            ("BaseCY", height),
            ("OutputCX", width),
            ("OutputCY", height),
            ("FPSCommon", config.FPS),
        ):
            self.client.set_profile_parameter("Video", name, str(value))
        self.client.set_video_settings(config.FPS, 1, width, height, width, height)
        settings = self.client.get_video_settings()
        actual = (
            settings.base_width,
            settings.base_height,
            settings.output_width,
            settings.output_height,
            settings.fps_numerator,
            settings.fps_denominator,
        )
        expected = (width, height, width, height, config.FPS, 1)
        if actual != expected:
            raise RuntimeError(
                f"OBS rejected GoExport video settings; expected {expected}, got {actual}."
            )
        self.client.set_record_directory(str(self.artifacts.obs_directory.resolve()))
        self.client.set_profile_parameter("Output", "Mode", "Simple")
        self.client.set_profile_parameter(
            "Output", "FilenameFormatting", f"goexport-{self.run_id}"
        )
        self.client.set_profile_parameter("SimpleOutput", "RecFormat2", "mkv")
        self.client.set_profile_parameter("SimpleOutput", "RecEncoder", "x264")
        # Never inherit global devices, especially a microphone, into this profile.
        for name in (
            "DesktopDevice1",
            "DesktopDevice2",
            "MicAuxDevice1",
            "MicAuxDevice2",
            "MicAuxDevice3",
            "MicAuxDevice4",
        ):
            self.client.set_profile_parameter("Audio", name, "disabled")

    def _configure_scene_and_source(self):
        scenes = self.client.get_scene_list()
        scene_names = {_value(scene, "sceneName") for scene in scenes.scenes}
        if GOEXPORT_SCENE not in scene_names:
            self.client.create_scene(GOEXPORT_SCENE)
        self.client.set_current_program_scene(GOEXPORT_SCENE)

        kinds = set(self.client.get_input_kind_list(True).input_kinds)
        input_kind, initial, audio_kind = self._source_strategy(kinds)
        inputs = self.client.get_input_list().inputs
        input_names = {_value(item, "inputName") for item in inputs}
        if GOEXPORT_VIDEO_INPUT not in input_names:
            self.client.create_input(
                GOEXPORT_SCENE,
                GOEXPORT_VIDEO_INPUT,
                input_kind,
                initial,
                True,
            )
        else:
            current = self.client.get_input_settings(GOEXPORT_VIDEO_INPUT)
            if current.input_kind != input_kind:
                self.client.remove_input(GOEXPORT_VIDEO_INPUT)
                self.client.create_input(
                    GOEXPORT_SCENE,
                    GOEXPORT_VIDEO_INPUT,
                    input_kind,
                    initial,
                    True,
                )
            else:
                self.client.set_input_settings(GOEXPORT_VIDEO_INPUT, initial, True)

        items = self.client.get_input_properties_list_property_items(
            GOEXPORT_VIDEO_INPUT, "window"
        ).property_items
        matches = [
            item
            for item in items
            if self.window_title in str(_value(item, "itemName", ""))
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Could not uniquely identify Chromium in OBS. Expected window title "
                f"{self.window_title!r}, found {len(matches)} matches."
            )
        window_id = _value(matches[0], "itemValue")
        self.client.set_input_settings(
            GOEXPORT_VIDEO_INPUT,
            {**initial, "window": window_id},
            True,
        )
        self._configure_audio_source(audio_kind, input_names)
        scene_item = self.client.get_scene_item_id(GOEXPORT_SCENE, GOEXPORT_VIDEO_INPUT)
        width, height = self.args.resolution
        self.client.set_scene_item_transform(
            GOEXPORT_SCENE,
            scene_item.scene_item_id,
            {
                "positionX": 0.0,
                "positionY": 0.0,
                "alignment": 5,
                "boundsType": "OBS_BOUNDS_STRETCH",
                "boundsAlignment": 0,
                "boundsWidth": float(width),
                "boundsHeight": float(height),
                "cropLeft": 0,
                "cropTop": 0,
                "cropRight": 0,
                "cropBottom": 0,
            },
        )

    def _source_strategy(self, kinds):
        if config.SYSTEM == "Darwin":
            if "screen_capture" not in kinds:
                raise RuntimeError(
                    "OBS macOS Screen Capture is unavailable. Update OBS and "
                    "grant Screen Recording permission."
                )
            return (
                "screen_capture",
                {
                    "type": 1,
                    "window": 0,
                    "show_cursor": False,
                    "show_empty_names": False,
                    "show_hidden_windows": True,
                },
                None,
            )
        if config.SYSTEM == "Windows":
            if "window_capture" not in kinds:
                raise RuntimeError("OBS Window Capture is unavailable on Windows.")
            return (
                "window_capture",
                {
                    "window": "",
                    "priority": 0,
                    "method": 0,
                    "cursor": False,
                    "client_area": True,
                    "capture_audio": True,
                },
                None,
            )
        if "xcomposite_input" not in kinds:
            raise RuntimeError(
                "OBS Xcomposite Window Capture is unavailable. The initial Linux "
                "OBS backend requires an X11 session; Wayland portal selection is "
                "not deterministic enough for unattended recording."
            )
        if "pulse_output_capture" not in kinds:
            raise RuntimeError(
                "OBS PulseAudio Output Capture is unavailable; GoExport cannot "
                "capture movie audio on this Linux OBS installation."
            )
        return (
            "xcomposite_input",
            {"window": 0, "show_cursor": False, "include_border": False},
            "pulse_output_capture",
        )

    def _configure_audio_source(self, audio_kind, existing_names):
        if audio_kind is None:
            if GOEXPORT_AUDIO_INPUT in existing_names:
                self.client.remove_input(GOEXPORT_AUDIO_INPUT)
            return
        settings = {}
        if GOEXPORT_AUDIO_INPUT not in existing_names:
            self.client.create_input(
                GOEXPORT_SCENE,
                GOEXPORT_AUDIO_INPUT,
                audio_kind,
                settings,
                True,
            )
        else:
            current = self.client.get_input_settings(GOEXPORT_AUDIO_INPUT)
            if current.input_kind != audio_kind:
                self.client.remove_input(GOEXPORT_AUDIO_INPUT)
                self.client.create_input(
                    GOEXPORT_SCENE,
                    GOEXPORT_AUDIO_INPUT,
                    audio_kind,
                    settings,
                    True,
                )

    def start(self):
        self.client.start_record()
        self.recording_started = True

    def capture_until_stopped(self, started, stopped, total_duration_ns):
        began = time.monotonic_ns()
        while not stopped.wait(0.1):
            status = self.client.get_record_status()
            if not status.output_active:
                raise RuntimeError("OBS stopped recording before playback finished.")
            elapsed = time.monotonic_ns() - began
            percent = min(100, int(elapsed * 100 / total_duration_ns))
            self.reporter.progress(5 + percent * 0.79, "recording")
        return self.stop()

    def stop(self):
        if not self.recording_started:
            return self.result
        response = self.client.stop_record()
        self.recording_started = False
        output_path = _value(response, "output_path")
        if not output_path:
            raise RuntimeError(
                "OBS stopped recording without reporting an output path."
            )
        path = Path(output_path).resolve()
        owned_root = self.artifacts.obs_directory.resolve()
        try:
            path.relative_to(owned_root)
        except ValueError as error:
            raise RuntimeError(
                f"OBS returned an output path outside GoExport's directory: {path}"
            ) from error
        self._wait_for_finalized_recording(path)
        self.result = CaptureResult(
            path, None, audio_is_muxed=True, owned_paths=(path,)
        )
        return self.result

    @staticmethod
    def _wait_for_finalized_recording(path):
        """Wait for the authoritative StopRecord path to become visible.

        OBS completes container finalization before replying to StopRecord. The
        bounded poll only covers delayed filesystem visibility after that reply;
        it does not attempt to predict OBS's filename or recording duration.
        """
        deadline = time.monotonic() + RECORDING_FINALIZE_TIMEOUT_SECONDS
        last_error = None
        while True:
            try:
                if path.is_file():
                    return
            except OSError as error:
                last_error = error
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                detail = f" Last filesystem error: {last_error}" if last_error else ""
                raise RuntimeError(
                    "OBS reported a completed recording, but the file did not "
                    f"become available within {RECORDING_FINALIZE_TIMEOUT_SECONDS:g} "
                    f"seconds: {path}.{detail}"
                )
            time.sleep(min(RECORDING_FINALIZE_POLL_SECONDS, remaining))

    def close(self):
        if self.client is None:
            return
        if self.recording_started:
            try:
                self.stop()
            except Exception:
                logger.warning(
                    "Could not stop OBS recording during cleanup", exc_info=True
                )
        if self.original_scene_collection:
            try:
                self.client.set_current_scene_collection(self.original_scene_collection)
            except Exception:
                logger.warning("Could not restore OBS scene collection", exc_info=True)
        if self.original_profile:
            try:
                self.client.set_current_profile(self.original_profile)
            except Exception:
                logger.warning("Could not restore OBS profile", exc_info=True)
        try:
            self.client.disconnect()
        except Exception:
            logger.debug("Could not disconnect from OBS", exc_info=True)
        self.client = None
