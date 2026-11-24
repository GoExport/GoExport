import unittest
from pathlib import Path

from goexport.url_request import RequestError, parse_request


class ValidRequestTests(unittest.TestCase):
    def test_minimal_record_request(self):
        request = parse_request("goexport://record?movie_id=m-123")
        self.assertEqual(request.movie_id, "m-123")
        self.assertEqual(
            request.record_arguments(Path("out")),
            ["--movie-id=m-123", "--output=out"],
        )

    def test_all_parameters_map_to_record_options(self):
        request = parse_request(
            "goexport://record/?movie_id=0Abc_d.e&user_id=42&format=mkv"
            "&resolution=1920X1080&wide=false&outro=no"
            "&url=https%3A%2F%2Fflashthemes.net%2F"
            "&api_url=http://localhost:4343/"
            "&swf_url=https://cdn.example/player.swf"
            "&store_path=https://cdn.example/store/%3Cstore%3E"
            "&client_theme_path=https://cdn.example/static/%3Cclient_theme%3E"
        )
        self.assertEqual(
            request.record_arguments(Path("exports/x")),
            [
                "--movie-id=0Abc_d.e",
                f"--output={Path('exports/x')}",
                "--user-id=42",
                "--format=mkv",
                "--resolution=1920x1080",
                "--no-wide",
                "--no-outro",
                "--url=https://flashthemes.net/",
                "--api-url=http://localhost:4343/",
                "--swf-url=https://cdn.example/player.swf",
                "--store-path=https://cdn.example/store/<store>",
                "--client-theme-path=https://cdn.example/static/<client_theme>",
            ],
        )

    def test_scheme_and_action_are_case_insensitive(self):
        self.assertEqual(parse_request("GoExport://Record?movie_id=1").movie_id, "1")

    def test_true_booleans_add_no_options(self):
        request = parse_request("goexport://record?movie_id=1&wide=1&outro=YES")
        self.assertTrue(request.wide)
        self.assertTrue(request.outro)
        self.assertEqual(len(request.record_arguments(Path("o"))), 2)

    def test_output_name_comes_from_validated_movie_id(self):
        request = parse_request("goexport://record?movie_id=abc")
        self.assertEqual(
            request.output_path(Path("exports"), "20260101-000000"),
            Path("exports") / "abc-20260101-000000",
        )


class InvalidRequestTests(unittest.TestCase):
    def assert_rejected(self, url: str, message: str) -> None:
        with self.assertRaisesRegex(RequestError, message):
            parse_request(url)

    def test_invalid_schemes(self):
        for url in (
            "https://record?movie_id=1",
            "goexports://record?movie_id=1",
            "record",
        ):
            with self.subTest(url=url):
                self.assert_rejected(url, "goexport://")

    def test_missing_and_unsupported_actions(self):
        self.assert_rejected("goexport://?movie_id=1", "does not name an action")
        self.assert_rejected("goexport://delete?movie_id=1", "Unsupported action")
        self.assert_rejected(
            "goexport://export?url=https://example.com", "Frame-by-frame"
        )
        self.assert_rejected("goexport://user@record?movie_id=1", "Unsupported action")
        self.assert_rejected("goexport://record:80?movie_id=1", "Unsupported action")

    def test_v1_urls_get_migration_guidance(self):
        for url in (
            "goexport://local?video_id=m-1&resolution=1080p",
            "goexport://?service=ft&video_id=1&no_input=true",
        ):
            with self.subTest(url=url):
                self.assert_rejected(url, "V1 URL")

    def test_missing_required_parameter(self):
        self.assert_rejected("goexport://record", "movie_id")
        self.assert_rejected("goexport://record?movie_id=", "movie_id")

    def test_unexpected_and_dangerous_parameters_are_rejected(self):
        for name in ("output", "chrome_path", "ffmpeg_path", "use_outro", "verbose"):
            with self.subTest(name=name):
                self.assert_rejected(
                    f"goexport://record?movie_id=1&{name}=x", "Unsupported parameter"
                )

    def test_repeated_parameters_are_rejected(self):
        self.assert_rejected("goexport://record?movie_id=1&movie_id=2", "repeated")

    def test_malformed_urls(self):
        self.assert_rejected("goexport://record?movie_id=1&&x", "malformed")
        self.assert_rejected("goexport://record?movie_id", "malformed")
        self.assert_rejected("goexport://record/extra?movie_id=1", "path")
        self.assert_rejected("goexport://record?movie_id=1#frag", "fragment")
        self.assert_rejected("goexport://record?movie_id=1 2", "spaces")
        self.assert_rejected("goexport://record?movie_id=" + "a" * 5000, "longer")
        self.assert_rejected("goexport://[::1?movie_id=1", "malformed")

    def test_identifiers_cannot_inject_options_or_paths(self):
        for value in (
            "-rf",
            "..%2F..%2Fetc",
            "a%2Fb",
            "a%20b",
            "%00",
            "a;b",
            "x" * 129,
        ):
            with self.subTest(value=value):
                with self.assertRaises(RequestError):
                    parse_request(f"goexport://record?movie_id={value}")

    def test_encoded_control_characters_are_rejected(self):
        self.assert_rejected(
            "goexport://record?movie_id=1&url=http://a/%0A--chrome-path", "control"
        )

    def test_endpoints_must_be_http_urls(self):
        for value in (
            "file:///etc/passwd",
            "javascript:alert(1)",
            "ftp://example.com/",
            "http://",
            "http://exa%20mple.com/",
            "--chrome-path=/bin/sh",
        ):
            with self.subTest(value=value):
                self.assert_rejected(f"goexport://record?movie_id=1&url={value}", "url")

    def test_format_resolution_and_booleans_are_validated(self):
        self.assert_rejected("goexport://record?movie_id=1&format=gif", "format")
        for value in ("720p", "0x720", "1280x", "99999x1", "-1x2"):
            with self.subTest(value=value):
                self.assert_rejected(
                    f"goexport://record?movie_id=1&resolution={value}", "resolution"
                )
        self.assert_rejected("goexport://record?movie_id=1&wide=maybe", "true or false")


if __name__ == "__main__":
    unittest.main()
