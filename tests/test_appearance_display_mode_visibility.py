import unittest

from ui.pages.appearance_page import AppearancePage


class AppearanceDisplayModeVisibilityTests(unittest.TestCase):
    def test_display_mode_visible_for_standard_preset(self):
        self.assertTrue(AppearancePage._should_show_display_mode_for_preset("standard"))

    def test_display_mode_hidden_for_amoled_preset(self):
        self.assertFalse(AppearancePage._should_show_display_mode_for_preset("amoled"))

    def test_display_mode_hidden_for_rkn_preset(self):
        self.assertFalse(AppearancePage._should_show_display_mode_for_preset("rkn_chan"))


if __name__ == "__main__":
    unittest.main()
