import unittest
from unittest.mock import patch

import autostart.autostart_direct_service as direct_service
import autostart.nssm_service as nssm_service


class DirectServiceRegistrySyncTests(unittest.TestCase):
    def _run_setup(self, *, create_ok: bool, start_ok: bool):
        registry_calls: list[tuple[bool, str | None]] = []

        with (
            patch("strategy_menu.get_strategy_launch_method", return_value="direct_zapret2"),
            patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=1, create=True),
            patch.object(direct_service.os.path, "exists", return_value=True),
            patch.object(direct_service.os, "makedirs", return_value=None),
            patch.object(nssm_service, "get_nssm_path", return_value=r"C:\\temp\\nssm.exe"),
            patch.object(nssm_service, "create_service_with_nssm", return_value=create_ok),
            patch.object(nssm_service, "start_service_with_nssm", return_value=start_ok),
            patch.object(
                direct_service,
                "set_autostart_enabled",
                side_effect=lambda enabled, method=None: registry_calls.append((enabled, method)),
            ),
        ):
            result = direct_service.setup_direct_service(
                winws_exe=r"C:\\temp\\winws2.exe",
                strategy_args=[r"@C:\\temp\\preset-zapret2.txt"],
                strategy_name="Пресет: Default",
            )

        return result, registry_calls

    def test_does_not_mark_registry_when_nssm_install_fails(self):
        ok, calls = self._run_setup(create_ok=False, start_ok=False)
        self.assertFalse(ok)
        self.assertEqual(calls, [])

    def test_does_not_mark_registry_when_service_start_fails(self):
        ok, calls = self._run_setup(create_ok=True, start_ok=False)
        self.assertFalse(ok)
        self.assertEqual(calls, [])

    def test_marks_registry_only_after_service_started(self):
        ok, calls = self._run_setup(create_ok=True, start_ok=True)
        self.assertTrue(ok)
        self.assertEqual(calls, [(True, "direct_service")])


if __name__ == "__main__":
    unittest.main()
