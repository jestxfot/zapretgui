import unittest
from unittest.mock import patch

from blockcheck.config import STUN_TIMEOUT
from blockcheck.models import SingleTestResult, TestStatus as ResultStatus, TestType as ResultType
from blockcheck.runner import BlockcheckRunner


class BlockcheckRunnerStunIpv6Tests(unittest.TestCase):
    def test_stun_phase_parses_bracketed_ipv6_target(self):
        runner = BlockcheckRunner(mode="full", parallel=1)
        stun_targets = [{"name": "IPv6 STUN", "value": "STUN:[2001:db8::10]:3478"}]

        fake_result = SingleTestResult(
            target_name="IPv6 STUN",
            test_type=ResultType.STUN,
            status=ResultStatus.OK,
            detail="ok",
        )

        with patch("blockcheck.runner.test_stun", return_value=fake_result) as stun_mock:
            results = runner._run_stun_phase(stun_targets)

        stun_mock.assert_called_once_with("2001:db8::10", 3478, timeout=STUN_TIMEOUT)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "IPv6 STUN")


if __name__ == "__main__":
    unittest.main()
