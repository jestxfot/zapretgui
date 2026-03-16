import importlib
import unittest
from unittest.mock import patch


dns_core = importlib.import_module("dns.dns_core")


class DNSManagerDoHFlowTests(unittest.TestCase):
    def setUp(self):
        self.manager = dns_core.DNSManager()

    def test_set_custom_dns_ipv4_enables_doh_when_template_exists(self):
        with (
            patch.object(self.manager, "get_adapter_guid", return_value="{GUID}"),
            patch("dns.dns_core.set_dns_via_registry", return_value=True),
            patch("dns.dns_core.get_doh_template_for_dns", return_value="https://dns.google/dns-query"),
            patch("dns.dns_core.set_doh_for_adapter", return_value=True) as set_doh,
            patch("dns.dns_core.clear_doh_for_adapter") as clear_doh,
            patch("dns.dns_core.notify_dns_change", return_value=True),
        ):
            ok, msg = self.manager.set_custom_dns("Ethernet", "8.8.8.8", None, "IPv4")

        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        set_doh.assert_called_once_with("{GUID}", "8.8.8.8", enable=True)
        clear_doh.assert_not_called()

    def test_set_custom_dns_ipv4_clears_doh_when_template_missing(self):
        with (
            patch.object(self.manager, "get_adapter_guid", return_value="{GUID}"),
            patch("dns.dns_core.set_dns_via_registry", return_value=True),
            patch("dns.dns_core.get_doh_template_for_dns", return_value=None),
            patch("dns.dns_core.set_doh_for_adapter") as set_doh,
            patch("dns.dns_core.clear_doh_for_adapter", return_value=True) as clear_doh,
            patch("dns.dns_core.notify_dns_change", return_value=True),
        ):
            ok, msg = self.manager.set_custom_dns("Ethernet", "83.220.169.155", None, "IPv4")

        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        set_doh.assert_not_called()
        clear_doh.assert_called_once_with("{GUID}")

    def test_set_custom_dns_ipv6_does_not_touch_doh(self):
        with (
            patch.object(self.manager, "get_adapter_guid", return_value="{GUID}"),
            patch("dns.dns_core.set_dns_via_registry", return_value=True),
            patch("dns.dns_core.set_doh_for_adapter") as set_doh,
            patch("dns.dns_core.clear_doh_for_adapter") as clear_doh,
            patch("dns.dns_core.notify_dns_change", return_value=True),
        ):
            ok, msg = self.manager.set_custom_dns("Ethernet", "2001:4860:4860::8888", None, "IPv6")

        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        set_doh.assert_not_called()
        clear_doh.assert_not_called()

    def test_set_auto_dns_ipv4_clears_doh(self):
        with (
            patch.object(self.manager, "get_adapter_guid", return_value="{GUID}"),
            patch("dns.dns_core.set_dns_via_registry", return_value=True) as set_dns,
            patch("dns.dns_core.clear_doh_for_adapter", return_value=True) as clear_doh,
            patch("dns.dns_core.notify_dns_change", return_value=True),
        ):
            ok, msg = self.manager.set_auto_dns("Ethernet", "IPv4")

        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        set_dns.assert_called_once_with("{GUID}", [], False)
        clear_doh.assert_called_once_with("{GUID}")

    def test_set_auto_dns_ipv6_does_not_clear_doh(self):
        with (
            patch.object(self.manager, "get_adapter_guid", return_value="{GUID}"),
            patch("dns.dns_core.set_dns_via_registry", return_value=True) as set_dns,
            patch("dns.dns_core.clear_doh_for_adapter", return_value=True) as clear_doh,
            patch("dns.dns_core.notify_dns_change", return_value=True),
        ):
            ok, msg = self.manager.set_auto_dns("Ethernet", "IPv6")

        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        set_dns.assert_called_once_with("{GUID}", [], True)
        clear_doh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
