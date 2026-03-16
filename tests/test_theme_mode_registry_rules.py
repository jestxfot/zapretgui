import unittest
import importlib
from unittest.mock import patch

reg_mod = importlib.import_module("config.reg")


class WindowOpacityDefaultsTests(unittest.TestCase):
    def test_win11_default_opacity_is_zero_when_unset(self):
        with (
            patch("config.reg.reg", return_value=None),
            patch("config.reg._is_win11_plus", return_value=True),
        ):
            self.assertEqual(reg_mod.get_window_opacity(), 0)

    def test_win10_default_opacity_is_full_when_unset(self):
        with (
            patch("config.reg.reg", return_value=None),
            patch("config.reg._is_win11_plus", return_value=False),
        ):
            self.assertEqual(reg_mod.get_window_opacity(), 100)

    def test_invalid_opacity_value_falls_back_to_platform_default(self):
        with (
            patch("config.reg.reg", return_value="invalid"),
            patch("config.reg._is_win11_plus", return_value=True),
        ):
            self.assertEqual(reg_mod.get_window_opacity(), 0)


class DisplayModeCoercionTests(unittest.TestCase):
    def test_get_display_mode_forces_dark_when_amoled_preset_active(self):
        def fake_reg(subkey, name=None, value=reg_mod._UNSET, **_kwargs):
            if value is reg_mod._UNSET:
                if name == "DisplayMode":
                    return "light"
                if name == "BackgroundPreset":
                    return "amoled"
            return True

        with patch("config.reg.reg", side_effect=fake_reg):
            self.assertEqual(reg_mod.get_display_mode(), "dark")

    def test_set_display_mode_writes_dark_when_rkn_preset_active(self):
        writes = []

        def fake_reg(subkey, name=None, value=reg_mod._UNSET, **_kwargs):
            if value is reg_mod._UNSET:
                if name == "BackgroundPreset":
                    return "rkn_chan"
                return None
            writes.append((name, value))
            return True

        with patch("config.reg.reg", side_effect=fake_reg):
            ok = reg_mod.set_display_mode("system")

        self.assertTrue(ok)
        self.assertIn(("DisplayMode", "dark"), writes)

    def test_get_display_mode_self_heals_legacy_light_value(self):
        writes = []

        def fake_reg(subkey, name=None, value=reg_mod._UNSET, **_kwargs):
            if value is reg_mod._UNSET:
                if name == "DisplayMode":
                    return "light"
                if name == "BackgroundPreset":
                    return "amoled"
                return None
            writes.append((name, value))
            return True

        with patch("config.reg.reg", side_effect=fake_reg):
            mode = reg_mod.get_display_mode()

        self.assertEqual(mode, "dark")
        self.assertIn(("DisplayMode", "dark"), writes)


if __name__ == "__main__":
    unittest.main()
