import unittest

from blockcheck.targets import get_default_stun_targets


class BlockcheckStunDefaultsTests(unittest.TestCase):
    def test_default_stun_targets_include_telegram_hosts(self):
        targets = get_default_stun_targets()
        values = {str(item.get("value", "")) for item in targets}

        self.assertIn("STUN:stun.telegram.org:3478", values)
        self.assertIn("STUN:stun.voip.telegram.org:3478", values)


if __name__ == "__main__":
    unittest.main()
