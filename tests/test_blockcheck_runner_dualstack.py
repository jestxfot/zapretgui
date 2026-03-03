import unittest
from unittest.mock import patch

from blockcheck.models import (
    SingleTestResult,
    TestStatus as ResultStatus,
    TestType as ResultType,
)
from blockcheck.runner import BlockcheckRunner


class BlockcheckRunnerDualStackTests(unittest.TestCase):
    def test_https_phase_runs_ipv4_and_ipv6_probes(self):
        runner = BlockcheckRunner(mode="dpi_only", parallel=1)
        targets = [{"name": "Example", "value": "https://example.com"}]

        def fake_test_https(host, port=443, timeout=10, tls_version=None, ip_family="auto"):
            test_type = ResultType.HTTP
            if tls_version == "1.2":
                test_type = ResultType.TLS_12
            elif tls_version == "1.3":
                test_type = ResultType.TLS_13

            return SingleTestResult(
                target_name=host,
                test_type=test_type,
                status=ResultStatus.OK,
                detail=f"ok {ip_family}",
                raw_data={"ip_family": ip_family},
            )

        with patch.object(
            BlockcheckRunner,
            "_resolve_host_ips",
            return_value=(
                ["93.184.216.34"],
                ["2606:2800:220:1:248:1893:25c8:1946"],
            ),
        ), patch("blockcheck.runner.test_https", side_effect=fake_test_https):
            results = runner._run_https_phase(targets)

        self.assertEqual(len(results), 1)
        tr = results[0]

        self.assertEqual(len(tr.tests), 6)
        families = {str(t.raw_data.get("ip_family")) for t in tr.tests}
        self.assertEqual(families, {"ipv4", "ipv6"})

        per_type_counts = {
            ResultType.HTTP: 0,
            ResultType.TLS_12: 0,
            ResultType.TLS_13: 0,
        }
        for test in tr.tests:
            per_type_counts[test.test_type] += 1

        self.assertEqual(per_type_counts[ResultType.HTTP], 2)
        self.assertEqual(per_type_counts[ResultType.TLS_12], 2)
        self.assertEqual(per_type_counts[ResultType.TLS_13], 2)


if __name__ == "__main__":
    unittest.main()
