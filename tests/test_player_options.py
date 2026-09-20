import argparse
import unittest
from urllib.parse import parse_qsl

from goexport.player_options import (
    build_player_replacements,
    parse_flashvars,
    parse_replacement,
    resolve_placeholders,
)


class PlayerReplacementTests(unittest.TestCase):
    def test_flashthemes_owner_id_uses_runtime_user_id(self):
        value = resolve_placeholders(
            "https://example/store/<store>?v={owner_id}",
            {"user_id": "12345"},
            {"owner_id": "{user_id}"},
        )
        self.assertEqual(value, "https://example/store/<store>?v=12345")

    def test_cli_replacement_overrides_configured_entry(self):
        value = resolve_placeholders(
            "{owner_id}",
            {"user_id": "12345"},
            {"owner_id": "{user_id}"},
            {"owner_id": "custom"},
        )
        self.assertEqual(value, "custom")

    def test_unknown_and_circular_placeholders_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "No value.*missing"):
            resolve_placeholders("{missing}", {}, {})
        with self.assertRaisesRegex(ValueError, "Circular.*a -> b -> a"):
            resolve_placeholders("{a}", {}, {"a": "{b}", "b": "{a}"})

    def test_missing_user_id_only_fails_when_placeholder_is_used(self):
        self.assertEqual(
            resolve_placeholders("plain", {}, {"owner_id": "{user_id}"}),
            "plain",
        )
        with self.assertRaisesRegex(ValueError, "user_id"):
            resolve_placeholders("{owner_id}", {}, {"owner_id": "{user_id}"})

    def test_flashvars_add_and_override_standard_values(self):
        replacements = build_player_replacements(
            {
                "WINDOW_TITLE": "title",
                "PLAYER_WIDTH": 1280,
                "PLAYER_HEIGHT": 720,
                "PLAYER_SWF_URL": "player.swf",
                "IS_WIDE": "true",
                "API_SERVER": "https://example/api?a=1&b=2",
                "STORE_PATH": "https://example/<store>?v={owner_id}",
                "CLIENT_THEME_PATH": "themes/<client_theme>",
                "MOVIE_ID": "original",
            },
            {"movieId": "override", "custom": "hello world"},
            {"user_id": "42", "movie_id": "original"},
            {"owner_id": "{user_id}"},
        )
        encoded = replacements["FLASHVARS"].replace("&amp;", "&")
        flashvars = dict(parse_qsl(encoded, keep_blank_values=True))
        self.assertEqual(flashvars["movieId"], "override")
        self.assertEqual(flashvars["custom"], "hello world")
        self.assertEqual(flashvars["storePath"], "https://example/<store>?v=42")
        self.assertEqual(flashvars["apiserver"], "https://example/api?a=1&b=2")

    def test_cli_parsers_preserve_blank_values_and_validate_format(self):
        self.assertEqual(
            parse_flashvars("one=1&blank=&one=2"), {"one": "2", "blank": ""}
        )
        self.assertEqual(
            parse_replacement("owner_id={user_id}"), ("owner_id", "{user_id}")
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_flashvars("missing-value")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_replacement("bad name=value")


if __name__ == "__main__":
    unittest.main()
