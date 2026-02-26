import tempfile
import unittest
from pathlib import Path

import hosts.proxy_domains as proxy_domains


class ProxyDomainsIPv6SectionsTests(unittest.TestCase):
    def setUp(self):
        proxy_domains.invalidate_hosts_catalog_cache()

    def tearDown(self):
        proxy_domains.invalidate_hosts_catalog_cache()

    def test_ipv6_meta_sections_are_ignored_as_services(self):
        text = "\n".join(
            [
                "[DNS]",
                "Main DNS",
                "Вкл. (активировать hosts)",
                "",
                "[__ipv6_status__]",
                "enabled = 1",
                "",
                "[__ipv6_dns_providers__]",
                "Popular / Cloudflare = 2606:4700:4700::1111, 2606:4700:4700::1001",
                "",
                "[Service]",
                "example.com",
                "1.1.1.1",
                "1.1.1.2",
                "",
            ]
        )

        catalog = proxy_domains._parse_hosts_ini(text)
        self.assertIn("Service", catalog.services)
        self.assertNotIn("__ipv6_status__", catalog.services)
        self.assertNotIn("__ipv6_dns_providers__", catalog.services)

    def test_ensure_ipv6_sections_updates_catalog_only_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "json" / "hosts.ini"
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(
                "\n".join(
                    [
                        "[DNS]",
                        "Main DNS",
                        "Вкл. (активировать hosts)",
                        "",
                        "[Service]",
                        "example.com",
                        "1.1.1.1",
                        "2.2.2.2",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            original_get_path = proxy_domains._get_catalog_hosts_ini_path
            original_check_ipv6 = proxy_domains._check_ipv6_connectivity
            original_collect_ipv6 = proxy_domains._collect_provider_ipv6_entries

            try:
                proxy_domains._get_catalog_hosts_ini_path = lambda: catalog_path  # type: ignore[assignment]
                proxy_domains._check_ipv6_connectivity = lambda: True  # type: ignore[assignment]
                proxy_domains._collect_provider_ipv6_entries = lambda: [  # type: ignore[assignment]
                    (
                        "Популярные / Cloudflare",
                        "2606:4700:4700::1111, 2606:4700:4700::1001",
                    )
                ]

                changed, ipv6_available = proxy_domains.ensure_ipv6_catalog_sections_if_available()
                self.assertTrue(ipv6_available)
                self.assertTrue(changed)

                first_text = catalog_path.read_text(encoding="utf-8")
                self.assertIn("[__ipv6_status__]", first_text)
                self.assertIn("[__ipv6_dns_providers__]", first_text)

                changed_again, ipv6_available_again = proxy_domains.ensure_ipv6_catalog_sections_if_available()
                self.assertTrue(ipv6_available_again)
                self.assertFalse(changed_again)
                second_text = catalog_path.read_text(encoding="utf-8")

                self.assertEqual(first_text, second_text)
            finally:
                proxy_domains._get_catalog_hosts_ini_path = original_get_path  # type: ignore[assignment]
                proxy_domains._check_ipv6_connectivity = original_check_ipv6  # type: ignore[assignment]
                proxy_domains._collect_provider_ipv6_entries = original_collect_ipv6  # type: ignore[assignment]

    def test_ensure_ipv6_sections_skips_when_ipv6_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "json" / "hosts.ini"
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            initial_text = "[DNS]\nMain DNS\n"
            catalog_path.write_text(initial_text, encoding="utf-8")

            original_get_path = proxy_domains._get_catalog_hosts_ini_path
            original_check_ipv6 = proxy_domains._check_ipv6_connectivity

            try:
                proxy_domains._get_catalog_hosts_ini_path = lambda: catalog_path  # type: ignore[assignment]
                proxy_domains._check_ipv6_connectivity = lambda: False  # type: ignore[assignment]

                changed, ipv6_available = proxy_domains.ensure_ipv6_catalog_sections_if_available()
                self.assertFalse(changed)
                self.assertFalse(ipv6_available)
                self.assertEqual(catalog_path.read_text(encoding="utf-8"), initial_text)
            finally:
                proxy_domains._get_catalog_hosts_ini_path = original_get_path  # type: ignore[assignment]
                proxy_domains._check_ipv6_connectivity = original_check_ipv6  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
