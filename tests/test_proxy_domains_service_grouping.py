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


if __name__ == "__main__":
    unittest.main()

