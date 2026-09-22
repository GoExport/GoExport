import importlib
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goexport import config
from goexport.configuration.loader import ConfigurationError, load_overrides


class ConfigurationTests(unittest.TestCase):
    def tearDown(self):
        importlib.reload(config)

    def test_missing_config_keeps_builtin_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            overrides = load_overrides(
                Path(directory) / "missing.toml",
                config.BASE_DIR,
                config.SUPPORTED_FORMATS,
            )
        self.assertEqual(overrides, {})
        self.assertEqual(config.WIDTH, 1280)
        self.assertEqual(config.URL, "http://localhost:4343/")

    def test_partial_config_only_changes_specified_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                "[video]\nwidth = 1920\n\n[wrapper]\nurl = 'http://example/'\n"
            )
            original_height = config.HEIGHT
            overrides = load_overrides(path, config.BASE_DIR, config.SUPPORTED_FORMATS)

        self.assertEqual(overrides["WIDTH"], 1920)
        self.assertNotIn("HEIGHT", overrides)
        self.assertEqual(original_height, config.HEIGHT)
        self.assertEqual(overrides["URL"], "http://example/")

    def test_relative_and_absolute_paths_are_resolved_correctly(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            absolute = base_dir / "absolute-ffmpeg"
            path = base_dir / "config.toml"
            path.write_text(
                f"[paths]\nchrome = 'bin/custom-chrome'\nffmpeg = {str(absolute)!r}\n"
            )
            overrides = load_overrides(path, base_dir, config.SUPPORTED_FORMATS)

        self.assertEqual(overrides["CHROME_PATH"], base_dir / "bin/custom-chrome")
        self.assertEqual(overrides["FFMPEG_PATH"], absolute)

    def test_malformed_toml_identifies_configuration_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[video\n")
            with self.assertRaisesRegex(ConfigurationError, re.escape(str(path))):
                load_overrides(path, config.BASE_DIR, config.SUPPORTED_FORMATS)

    def test_invalid_value_types_are_rejected(self):
        invalid_configs = (
            "[video]\nfps = 'potato'\n",
            "[video]\nwidth = false\n",
            "[wrapper]\nurl = 123\n",
            "[video]\nformat = 'avi'\n",
            "[flash]\nplugin_version = ''\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, contents in enumerate(invalid_configs):
                path = Path(directory) / f"invalid-{index}.toml"
                path.write_text(contents)
                with (
                    self.subTest(contents=contents),
                    self.assertRaises(ConfigurationError),
                ):
                    load_overrides(path, config.BASE_DIR, config.SUPPORTED_FORMATS)

    def test_cli_argument_overrides_config_default(self):
        import goexport.cli as cli

        with patch.object(config, "OUTPUT_FORMAT", "mkv"):
            parser = cli.build_parser()
            with tempfile.TemporaryDirectory() as directory:
                args = parser.parse_args(
                    ["export", "-f", "mov", "-ugc", directory, "-as", directory]
                )
        self.assertEqual(args.format, "mov")

    def test_replacement_table_is_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                "[replacements]\nowner_id = '{user_id}'\nsite = 'FlashThemes'\n"
            )
            overrides = load_overrides(path, config.BASE_DIR, config.SUPPORTED_FORMATS)

        self.assertEqual(
            overrides["PLACEHOLDER_REPLACEMENTS"],
            {"owner_id": "{user_id}", "site": "FlashThemes"},
        )

    def test_obs_configuration_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                "[recording]\nbackend = 'obs'\n\n"
                "[obs]\nhost = '127.0.0.1'\nport = 4455\n"
                "profile = 'GoExport'\nscene_collection = 'GoExport'\n"
            )
            overrides = load_overrides(path, config.BASE_DIR, config.SUPPORTED_FORMATS)
        self.assertEqual(overrides["RECORDING_BACKEND"], "obs")
        self.assertEqual(overrides["OBS_PORT"], 4455)

    def test_invalid_obs_configuration_is_rejected(self):
        invalid_configs = (
            "[recording]\nbackend = 'other'\n",
            "[obs]\nport = 0\n",
            "[obs]\nport = 65536\n",
            "[obs]\nprofile = ''\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, contents in enumerate(invalid_configs):
                path = Path(directory) / f"obs-invalid-{index}.toml"
                path.write_text(contents)
                with (
                    self.subTest(contents=contents),
                    self.assertRaises(ConfigurationError),
                ):
                    load_overrides(path, config.BASE_DIR, config.SUPPORTED_FORMATS)


if __name__ == "__main__":
    unittest.main()
