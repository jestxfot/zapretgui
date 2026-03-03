import unittest
from unittest.mock import patch

from blockcheck.dns_integrity import check_dns_integrity


class DNSIntegrityStubHeuristicsTests(unittest.TestCase):
    def test_related_domains_on_same_ip_are_not_stub(self):
        domains = ["telegram.org", "web.telegram.org", "discord.com", "youtube.com"]
        udp_answers = {
            "telegram.org": ["149.154.167.99"],
            "web.telegram.org": ["149.154.167.99"],
            "discord.com": ["162.159.138.232"],
            "youtube.com": ["142.250.74.110"],
        }

        with patch(
            "blockcheck.dns_integrity._resolve_udp",
            side_effect=lambda domain, *_args, **_kwargs: udp_answers.get(domain, []),
        ), patch(
            "blockcheck.dns_integrity._resolve_doh",
            side_effect=lambda *_args, **_kwargs: [],
        ):
            results = check_dns_integrity(domains)

        by_domain = {r.domain: r for r in results}
        self.assertFalse(by_domain["telegram.org"].is_stub)
        self.assertFalse(by_domain["web.telegram.org"].is_stub)
        self.assertFalse(by_domain["telegram.org"].is_comparable)

    def test_same_ip_across_many_unrelated_domains_is_stub(self):
        domains = ["alpha.com", "beta.net", "gamma.org", "delta.io"]
        udp_answers = {
            "alpha.com": ["203.0.113.10"],
            "beta.net": ["203.0.113.10"],
            "gamma.org": ["203.0.113.10"],
            "delta.io": ["203.0.113.20"],
        }

        with patch(
            "blockcheck.dns_integrity._resolve_udp",
            side_effect=lambda domain, *_args, **_kwargs: udp_answers.get(domain, []),
        ), patch(
            "blockcheck.dns_integrity._resolve_doh",
            side_effect=lambda *_args, **_kwargs: [],
        ):
            results = check_dns_integrity(domains)

        by_domain = {r.domain: r for r in results}
        self.assertTrue(by_domain["alpha.com"].is_stub)
        self.assertTrue(by_domain["beta.net"].is_stub)
        self.assertTrue(by_domain["gamma.org"].is_stub)
        self.assertFalse(by_domain["delta.io"].is_stub)


if __name__ == "__main__":
    unittest.main()
