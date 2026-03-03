import unittest
from unittest.mock import patch

import hosts.hosts as hosts_module


class HostsApplyDirectIPv6Tests(unittest.TestCase):
    def test_apply_service_dns_selections_writes_ipv6_and_ipv4_rows(self):
        written_state: dict[str, str] = {"content": ""}

        def fake_read_hosts_file():
            return "127.0.0.1 localhost\n1.1.1.1 www.whatsapp.com\n"

        def fake_write_hosts_file(content: str):
            written_state["content"] = content
            return True

        rows = [
            ("www.whatsapp.com", "2a03:2880:f37a:120:face:b00c:0:167"),
            ("www.whatsapp.com", "57.144.245.32"),
            ("web.whatsapp.com", "2a03:2880:f36f:120:face:b00c:0:167"),
            ("web.whatsapp.com", "57.144.223.32"),
        ]

        with (
            patch.object(hosts_module.HostsManager, "check_and_remove_github_api", return_value=None),
            patch.object(hosts_module.HostsManager, "is_hosts_file_accessible", return_value=True),
            patch.object(
                hosts_module,
                "_get_all_managed_domains",
                return_value={"www.whatsapp.com", "web.whatsapp.com"},
            ),
            patch.object(hosts_module, "safe_read_hosts_file", side_effect=fake_read_hosts_file),
            patch.object(hosts_module, "safe_write_hosts_file", side_effect=fake_write_hosts_file),
            patch.object(hosts_module, "get_service_domain_ip_rows", return_value=rows),
        ):
            manager = hosts_module.HostsManager(status_callback=lambda _msg: None)
            ok = manager.apply_service_dns_selections(
                {"WhatsApp (работает обход если есть IPv6)": "Вкл. (активировать hosts)"}
            )

        self.assertTrue(ok)
        output = written_state["content"]

        self.assertNotIn("1.1.1.1 www.whatsapp.com", output)
        self.assertIn("2a03:2880:f37a:120:face:b00c:0:167 www.whatsapp.com", output)
        self.assertIn("57.144.245.32 www.whatsapp.com", output)
        self.assertIn("2a03:2880:f36f:120:face:b00c:0:167 web.whatsapp.com", output)
        self.assertIn("57.144.223.32 web.whatsapp.com", output)


if __name__ == "__main__":
    unittest.main()
