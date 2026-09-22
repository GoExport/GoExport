import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from goexport.services.recording_backends import create_recording_backend, obs
from goexport.services.recording_backends.base import CaptureArtifacts
from goexport.services.recording_backends.obs import (
    GOEXPORT_SCENE,
    OWNERSHIP_SLOT,
    REQUIRED_REQUESTS,
    OBSBackend,
)
from goexport.services.recording_backends.pyscap import PyScapBackend


def response(**kwargs):
    return SimpleNamespace(**kwargs)


class OBSBackendTests(unittest.TestCase):
    def setUp(self):
        self.system = patch.object(obs.config, "SYSTEM", "Darwin")
        self.system.start()
        self.addCleanup(self.system.stop)
        self.args = Namespace(
            resolution=(1280, 720),
            obs_host="127.0.0.1",
            obs_port=4455,
            obs_profile="GoExport",
            obs_scene_collection="GoExport",
        )
        self.client = Mock()
        self.client.get_version.return_value = response(
            rpc_version=1, available_requests=list(REQUIRED_REQUESTS)
        )
        self.client.get_profile_list.return_value = response(
            current_profile_name="User", profiles=["User"]
        )
        self.client.get_scene_collection_list.return_value = response(
            current_scene_collection_name="User Scenes",
            scene_collections=["User Scenes"],
        )
        self.client.get_record_status.return_value = response(output_active=False)
        self.client.get_video_settings.return_value = response(
            base_width=1280,
            base_height=720,
            output_width=1280,
            output_height=720,
            fps_numerator=24,
            fps_denominator=1,
        )
        self.client.get_scene_list.return_value = response(scenes=[])
        self.client.get_input_kind_list.return_value = response(
            input_kinds=["screen_capture"]
        )
        self.client.get_input_list.return_value = response(inputs=[])
        self.client.get_input_properties_list_property_items.return_value = response(
            property_items=[
                {"itemName": "GoExport Recorder test — Chromium", "itemValue": 42}
            ]
        )
        self.client.get_scene_item_id.return_value = response(scene_item_id=7)

    def backend(self):
        return OBSBackend(
            self.args,
            Mock(),
            Path("ffmpeg"),
            "GoExport Recorder test",
            client_factory=Mock(return_value=self.client),
        )

    def test_factory_keeps_pyscap_as_explicit_backend(self):
        backend = create_recording_backend(
            "pyscap",
            args=Namespace(),
            reporter=Mock(),
            ffmpeg_path=Path("ffmpeg"),
            window_title="title",
        )
        self.assertIsInstance(backend, PyScapBackend)

    def test_prepare_creates_persistent_resources_and_configures_video(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = self.backend()
            backend.prepare(
                Mock(),
                Mock(),
                CaptureArtifacts(root / "video.mkv", root / "audio.wav", root / "obs"),
            )

        self.client.create_profile.assert_called_once_with("GoExport")
        self.client.remove_profile.assert_not_called()
        self.client.create_scene_collection.assert_called_once_with("GoExport")
        self.client.set_persistent_data.assert_called_once_with(
            "OBS_WEBSOCKET_DATA_REALM_PROFILE",
            OWNERSHIP_SLOT,
            {
                "owner": "GoExport",
                "version": 1,
                "sceneCollection": "GoExport",
            },
        )
        self.client.set_video_settings.assert_called_once_with(
            24, 1, 1280, 720, 1280, 720
        )
        settings = self.client.set_input_settings.call_args.args[1]
        self.assertEqual(settings["window"], 42)
        self.assertFalse(settings["show_cursor"])
        self.client.set_current_program_scene.assert_called_once_with(GOEXPORT_SCENE)

    def test_existing_unmarked_profile_is_rejected_and_restored(self):
        self.client.get_profile_list.return_value = response(
            current_profile_name="User", profiles=["User", "GoExport"]
        )
        self.client.get_persistent_data.return_value = response(slot_value=None)
        backend = self.backend()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                backend.prepare(
                    Mock(),
                    Mock(),
                    CaptureArtifacts(root / "v", root / "a", root / "obs"),
                )
        self.client.remove_profile.assert_not_called()
        self.client.set_current_profile.assert_any_call("User")

    def test_unowned_scene_collection_collision_is_rejected(self):
        self.client.get_scene_collection_list.return_value = response(
            current_scene_collection_name="User Scenes",
            scene_collections=["User Scenes", "GoExport"],
        )
        backend = self.backend()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "cannot be proven"):
                backend.prepare(
                    Mock(),
                    Mock(),
                    CaptureArtifacts(root / "v", root / "a", root / "obs"),
                )
        self.client.set_current_scene_collection.assert_called_once_with("User Scenes")

    def test_stop_returns_exact_owned_recording(self):
        backend = self.backend()
        backend.client = self.client
        backend.recording_started = True
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owned = root / "owned"
            owned.mkdir()
            output = owned / f"goexport-{backend.run_id}.mkv"
            output.write_bytes(b"recording")
            backend.artifacts = CaptureArtifacts(root / "v", root / "a", owned)
            self.client.stop_record.return_value = response(output_path=str(output))
            result = backend.stop()
        self.assertEqual(result.video, output.resolve())
        self.assertTrue(result.audio_is_muxed)

    def test_close_restores_scene_collection_then_profile(self):
        backend = self.backend()
        backend.client = self.client
        backend.original_scene_collection = "User Scenes"
        backend.original_profile = "User"
        backend.close()
        calls = self.client.method_calls
        self.assertLess(
            calls.index(call.set_current_scene_collection("User Scenes")),
            calls.index(call.set_current_profile("User")),
        )
        self.client.disconnect.assert_called_once()

    def test_stop_rejects_output_outside_owned_directory(self):
        backend = self.backend()
        backend.client = self.client
        backend.recording_started = True
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend.artifacts = CaptureArtifacts(root / "v", root / "a", root / "owned")
            self.client.stop_record.return_value = response(
                output_path=str(root / "foreign.mkv")
            )
            with self.assertRaisesRegex(RuntimeError, "outside"):
                backend.stop()

    def test_connection_error_never_echoes_password(self):
        factory = Mock(side_effect=RuntimeError("connection failed"))
        backend = OBSBackend(
            self.args, Mock(), Path("ffmpeg"), "title", client_factory=factory
        )
        with patch.dict("os.environ", {"GOEXPORT_OBS_PASSWORD": "sentinel"}):
            with self.assertRaises(RuntimeError) as caught:
                backend._connect()
        self.assertNotIn("sentinel", str(caught.exception))
        self.assertEqual(factory.call_args.kwargs["password"], "sentinel")

    def test_windows_uses_window_capture_with_application_audio(self):
        backend = self.backend()
        with patch.object(obs.config, "SYSTEM", "Windows"):
            kind, settings, audio_kind = backend._source_strategy({"window_capture"})
        self.assertEqual(kind, "window_capture")
        self.assertTrue(settings["capture_audio"])
        self.assertFalse(settings["cursor"])
        self.assertIsNone(audio_kind)

    def test_linux_uses_xcomposite_and_pulseaudio(self):
        backend = self.backend()
        with patch.object(obs.config, "SYSTEM", "Linux"):
            kind, settings, audio_kind = backend._source_strategy(
                {"xcomposite_input", "pulse_output_capture"}
            )
        self.assertEqual(kind, "xcomposite_input")
        self.assertFalse(settings["show_cursor"])
        self.assertEqual(audio_kind, "pulse_output_capture")

    def test_linux_requires_shared_x11_display(self):
        backend = self.backend()
        with patch.object(obs.config, "SYSTEM", "Linux"):
            with self.assertRaisesRegex(RuntimeError, "X11 DISPLAY"):
                backend.check_available(None)


if __name__ == "__main__":
    unittest.main()
