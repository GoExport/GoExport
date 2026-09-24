from __future__ import annotations

import io
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from goexport.cli import build_parser
from goexport.dependencies.manager import DependencyBootstrapError, DependencyManager
from goexport.dependencies.models import Dependency, DependencyStatus


class DependencyManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.install_calls: list[str] = []

    def _dependency(
        self,
        dependency_id: str,
        *,
        required_count: int = 1,
        invalidates: tuple[str, ...] = (),
        install_after: tuple[str, ...] = (),
    ) -> Dependency:
        paths = tuple(
            self.root / dependency_id / f"required-{index}"
            for index in range(required_count)
        )

        def install(dependency: Dependency, _context) -> None:
            self.install_calls.append(dependency.id)
            for path in dependency.required_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"installed")

        return Dependency(
            id=dependency_id,
            name=dependency_id.replace("_", " ").title(),
            required_paths=paths,
            install=install,
            runtime_argument=f"{dependency_id}_path",
            runtime_path=paths[0],
            invalidates=invalidates,
            install_after=install_after,
        )

    def _args(self, registry, **values) -> Namespace:
        defaults = {
            dependency.runtime_argument: dependency.runtime_path
            for dependency in registry.values()
        }
        defaults.update(yes=False, json=False)
        defaults.update(values)
        return Namespace(**defaults)

    def test_healthy_installation_does_not_install(self):
        dependency = self._dependency("ffmpeg")
        dependency.required_paths[0].parent.mkdir(parents=True)
        dependency.required_paths[0].write_bytes(b"healthy")
        manager = DependencyManager({"ffmpeg": dependency})

        manager.bootstrap(self._args(manager.registry), ("ffmpeg",))

        self.assertEqual(self.install_calls, [])

    def test_interactive_acceptance_installs_only_missing_dependency(self):
        chromium = self._dependency("chromium")
        ffmpeg = self._dependency("ffmpeg")
        chromium.required_paths[0].parent.mkdir(parents=True)
        chromium.required_paths[0].write_bytes(b"healthy")
        manager = DependencyManager({"chromium": chromium, "ffmpeg": ffmpeg})
        with (
            patch(
                "goexport.dependencies.manager._interactive_terminal", return_value=True
            ),
            patch("goexport.dependencies.manager.Confirm.ask", return_value=True),
        ):
            manager.bootstrap(self._args(manager.registry), ("chromium", "ffmpeg"))

        self.assertEqual(self.install_calls, ["ffmpeg"])

    def test_interactive_rejection_does_not_install(self):
        ffmpeg = self._dependency("ffmpeg")
        manager = DependencyManager({"ffmpeg": ffmpeg})
        with (
            patch(
                "goexport.dependencies.manager._interactive_terminal", return_value=True
            ),
            patch("goexport.dependencies.manager.Confirm.ask", return_value=False),
            self.assertRaisesRegex(DependencyBootstrapError, "declined"),
        ):
            manager.bootstrap(self._args(manager.registry), ("ffmpeg",))
        self.assertEqual(self.install_calls, [])

    def test_non_interactive_execution_fails_without_prompting(self):
        ffmpeg = self._dependency("ffmpeg")
        manager = DependencyManager({"ffmpeg": ffmpeg})
        with (
            patch(
                "goexport.dependencies.manager._interactive_terminal",
                return_value=False,
            ),
            patch("goexport.dependencies.manager.Confirm.ask") as confirm,
            self.assertRaisesRegex(DependencyBootstrapError, "--yes"),
        ):
            manager.bootstrap(self._args(manager.registry), ("ffmpeg",))
        confirm.assert_not_called()

    def test_yes_repairs_broken_installation(self):
        ffmpeg = self._dependency("ffmpeg", required_count=2)
        ffmpeg.required_paths[0].parent.mkdir(parents=True)
        ffmpeg.required_paths[0].write_bytes(b"partial")
        manager = DependencyManager({"ffmpeg": ffmpeg})
        self.assertEqual(ffmpeg.verify().status, DependencyStatus.BROKEN)

        manager.bootstrap(self._args(manager.registry, yes=True), ("ffmpeg",))

        self.assertEqual(self.install_calls, ["ffmpeg"])
        self.assertEqual(ffmpeg.verify().status, DependencyStatus.INSTALLED)

    def test_chromium_repair_only_reinstalls_managed_dependents(self):
        chromium = self._dependency(
            "chromium", invalidates=("chromedriver", "pepper_flash")
        )
        driver = self._dependency("chromedriver", install_after=("chromium",))
        flash = self._dependency("pepper_flash", install_after=("chromium",))
        manager = DependencyManager(
            {item.id: item for item in (chromium, driver, flash)}
        )
        args = self._args(
            manager.registry,
            yes=True,
            pepper_flash_path=self.root / "custom" / "flash.so",
        )

        manager.bootstrap(args, tuple(manager.registry))

        self.assertEqual(self.install_calls, ["chromium", "chromedriver"])

    def test_custom_runtime_override_is_not_managed(self):
        ffmpeg = self._dependency("ffmpeg")
        manager = DependencyManager({"ffmpeg": ffmpeg})
        custom = self.root / "custom-ffmpeg"
        custom.write_bytes(b"custom")

        manager.bootstrap(
            self._args(manager.registry, yes=True, ffmpeg_path=custom), ("ffmpeg",)
        )

        self.assertEqual(self.install_calls, [])

    def test_json_yes_writes_no_human_output(self):
        ffmpeg = self._dependency("ffmpeg")
        manager = DependencyManager({"ffmpeg": ffmpeg})
        output = io.StringIO()
        with redirect_stdout(output):
            manager.bootstrap(
                self._args(manager.registry, yes=True, json=True), ("ffmpeg",)
            )
        self.assertEqual(output.getvalue(), "")

    def test_missing_managed_defaults_survive_argument_parsing(self):
        args = build_parser().parse_args(["record", "-id", "movie"])
        self.assertIsInstance(args.ffmpeg_path, Path)


class DependencyCliBoundaryTests(unittest.TestCase):
    def test_help_and_version_do_not_construct_dependency_manager(self):
        for option in ("--help", "--version"):
            with (
                patch("goexport.cli.DependencyManager") as manager,
                self.assertRaises(SystemExit),
            ):
                build_parser().parse_args([option])
            manager.assert_not_called()

    def test_installer_script_delegates_to_shared_manager(self):
        from scripts import download_dependencies

        manager = Mock()
        with (
            patch.object(
                download_dependencies, "DependencyManager", return_value=manager
            ),
            patch.object(download_dependencies, "setup_logging"),
        ):
            self.assertEqual(download_dependencies.main(), 0)
        manager.install_all.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
