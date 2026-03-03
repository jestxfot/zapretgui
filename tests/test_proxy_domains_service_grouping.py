import unittest
from unittest.mock import patch

from hosts.proxy_domains import (
    _get_proxy_profile_indices,
    _infer_direct_profile_index,
    _parse_hosts_ini,
    _service_has_proxy_ips,
    get_service_domain_ip_map,
    get_service_domain_ip_rows,
)


class ProxyDomainsServiceGroupingTests(unittest.TestCase):
    def test_proxy_detection_ignores_profile_renames(self):
        text = "\n".join(
            [
                "[DNS]",
                "Zapret DNS (82.22.36.11)",
                "XBOX DNS (45.155.204.190)",
                "Comss DNS (95.182.120.241)",
                "Вкл. (активировать hosts)",
                "",
                "[DirectOnly]",
                "direct.example",
                "-",
                "-",
                "-",
                "1.1.1.1",
                "",
                "[HasProxy]",
                "proxy.example",
                "82.22.36.11",
                "45.155.204.190",
                "95.182.120.241",
                "-",
                "",
            ]
        )

        cat = _parse_hosts_ini(text)
        self.assertEqual(_infer_direct_profile_index(cat), 3)
        self.assertEqual(_get_proxy_profile_indices(cat), [0, 1, 2])
        self.assertFalse(_service_has_proxy_ips(cat, "DirectOnly"))
        self.assertTrue(_service_has_proxy_ips(cat, "HasProxy"))

    def test_raw_hosts_lines_are_parsed_as_direct_only_domain_services(self):
        text = "\n".join(
            [
                "[DNS]",
                "Zapret DNS",
                "XBOX DNS",
                "Comss DNS",
                "Вкл. (активировать hosts)",
                "",
                "[Supercell]",
                "144.31.14.104 accounts.supercell.com",
                "185.246.223.127 game-assets.clashofclans.com",
                "",
            ]
        )

        cat = _parse_hosts_ini(text)
        self.assertIn("Supercell", cat.services)
        self.assertIn("accounts.supercell.com", cat.services["Supercell"])

        direct_idx = _infer_direct_profile_index(cat)
        self.assertEqual(direct_idx, 3)

        ips = cat.services["Supercell"]["accounts.supercell.com"]
        self.assertEqual(ips[direct_idx], "144.31.14.104")
        self.assertFalse(_service_has_proxy_ips(cat, "Supercell"))

    def test_raw_ipv6_hosts_lines_are_parsed_without_breaking_service(self):
        text = "\n".join(
            [
                "[DNS]",
                "Zapret DNS",
                "XBOX DNS",
                "Вкл. (активировать hosts)",
                "",
                "[WhatsApp]",
                "2a03:2880:f36f:120:face:b00c:0:167 www.whatsapp.com",
                "57.144.245.32 www.whatsapp.com",
                "2a03:2880:f213:c3:face:b00c:0:167 web.whatsapp.com",
                "57.144.223.32 web.whatsapp.com",
                "",
            ]
        )

        cat = _parse_hosts_ini(text)
        self.assertIn("WhatsApp", cat.services)
        domains = cat.services["WhatsApp"]
        self.assertIn("www.whatsapp.com", domains)
        self.assertIn("web.whatsapp.com", domains)
        self.assertTrue(all(" " not in domain for domain in domains.keys()))

        direct_idx = _infer_direct_profile_index(cat)
        self.assertEqual(direct_idx, 2)
        self.assertEqual(domains["www.whatsapp.com"][direct_idx], "57.144.245.32")
        self.assertFalse(_service_has_proxy_ips(cat, "WhatsApp"))

    def test_domain_ip_rows_preserve_multiple_ips_per_domain(self):
        text = "\n".join(
            [
                "[DNS]",
                "Zapret DNS",
                "Вкл. (активировать hosts)",
                "",
                "[WhatsApp]",
                "2a03:2880:f37a:120:face:b00c:0:167 www.whatsapp.com",
                "57.144.245.32 www.whatsapp.com",
                "2a03:2880:f36f:120:face:b00c:0:167 web.whatsapp.com",
                "57.144.223.32 web.whatsapp.com",
                "",
            ]
        )

        cat = _parse_hosts_ini(text)
        with patch("hosts.proxy_domains._load_catalog", return_value=cat):
            rows = get_service_domain_ip_rows("WhatsApp", "Вкл. (активировать hosts)")
            domain_map = get_service_domain_ip_map("WhatsApp", "Вкл. (активировать hosts)")

        self.assertEqual(
            rows,
            [
                ("www.whatsapp.com", "2a03:2880:f37a:120:face:b00c:0:167"),
                ("www.whatsapp.com", "57.144.245.32"),
                ("web.whatsapp.com", "2a03:2880:f36f:120:face:b00c:0:167"),
                ("web.whatsapp.com", "57.144.223.32"),
            ],
        )
        # Back-compat map API keeps one value per domain (last wins),
        # but row API preserves all entries.
        self.assertEqual(domain_map["www.whatsapp.com"], "57.144.245.32")

    def test_service_mode_sections_override_inferred_proxy_detection(self):
        text = "\n".join(
            [
                "[DNS]",
                "Proxy A",
                "Proxy B",
                "Вкл. (активировать hosts)",
                "",
                "[SERVICES_DIRECT]",
                "",
                "[ExplicitDirect]",
                "direct.example",
                "11.11.11.11",
                "22.22.22.22",
                "33.33.33.33",
                "",
                "[SERVICES_DNS]",
                "",
                "[ExplicitDns]",
                "dns.example",
                "11.11.11.11",
                "22.22.22.22",
                "33.33.33.33",
                "",
            ]
        )

        cat = _parse_hosts_ini(text)
        self.assertNotIn("SERVICES_DIRECT", cat.services)
        self.assertNotIn("SERVICES_DNS", cat.services)
        self.assertEqual(cat.service_modes.get("explicitdirect"), "direct")
        self.assertEqual(cat.service_modes.get("explicitdns"), "dns")

        self.assertFalse(_service_has_proxy_ips(cat, "ExplicitDirect"))
        self.assertTrue(_service_has_proxy_ips(cat, "ExplicitDns"))


if __name__ == "__main__":
    unittest.main()
