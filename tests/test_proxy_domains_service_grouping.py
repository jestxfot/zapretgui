import unittest

from hosts.proxy_domains import (
    _get_proxy_profile_indices,
    _infer_direct_profile_index,
    _parse_hosts_ini,
    _service_has_proxy_ips,
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
        self.assertIn("accounts.supercell.com", cat.services)
        self.assertNotIn("Supercell", cat.services)  # do not create empty service sections

        direct_idx = _infer_direct_profile_index(cat)
        self.assertEqual(direct_idx, 3)

        ips = cat.services["accounts.supercell.com"]["accounts.supercell.com"]
        self.assertEqual(ips[direct_idx], "144.31.14.104")
        self.assertFalse(_service_has_proxy_ips(cat, "accounts.supercell.com"))


if __name__ == "__main__":
    unittest.main()
