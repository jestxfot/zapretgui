import unittest
from unittest.mock import patch

from blockcheck.dpi_classifier import DPIClassifier
from blockcheck.models import (
    DPIClassification,
    SingleTestResult,
    TargetResult,
    TestStatus as ResultStatus,
    TestType as ResultType,
)
from blockcheck.runner import BlockcheckRunner


class BlockcheckClassifierDnsTests(unittest.TestCase):
    def test_dns_stub_is_classified_when_no_other_signal(self):
        target = TargetResult(name="Example", value="https://example.com")
        target.tests.append(
            SingleTestResult(
                target_name="Example",
                test_type=ResultType.DNS_UDP,
                status=ResultStatus.FAIL,
                error_code="STUB",
                detail="DNS stub",
            )
        )

        classification, _ = DPIClassifier.classify(target)
        self.assertEqual(classification, DPIClassification.DNS_FAKE)

    def test_dns_stub_does_not_override_tls_dpi_signal(self):
        target = TargetResult(name="Example", value="https://example.com")
        target.tests.extend(
            [
                SingleTestResult(
                    target_name="Example",
                    test_type=ResultType.DNS_UDP,
                    status=ResultStatus.FAIL,
                    error_code="STUB",
                    detail="DNS stub",
                ),
                SingleTestResult(
                    target_name="Example",
                    test_type=ResultType.TLS_13,
                    status=ResultStatus.FAIL,
                    error_code="TLS_RESET",
                    detail="RST during handshake",
                ),
            ]
        )

        classification, _ = DPIClassifier.classify(target)
        self.assertEqual(classification, DPIClassification.TLS_DPI)

    def test_tcp_only_errors_do_not_escalate_to_full_block(self):
        target = TargetResult(name="TCP 16-20KB", value="TCP:16-20KB")
        target.tests.append(
            SingleTestResult(
                target_name="CF-01",
                test_type=ResultType.TCP_16_20,
                status=ResultStatus.ERROR,
                error_code="TCP_ERR",
                detail="connection refused",
            )
        )

        classification, _ = DPIClassifier.classify(target)
        self.assertEqual(classification, DPIClassification.NONE)


class BlockcheckRunnerRegressionTests(unittest.TestCase):
    def test_tcp_phase_supports_targets_with_id_only(self):
        runner = BlockcheckRunner(mode="dpi_only", parallel=1)
        tcp_result = SingleTestResult(
            target_name="",
            test_type=ResultType.TCP_16_20,
            status=ResultStatus.OK,
            detail="ok",
        )

        with patch("blockcheck.runner.load_tcp_targets_with_source", return_value=([
            {"id": "CF-01", "provider": "Cloudflare", "url": "https://example.com/file.bin"}
        ], "file:test")), patch(
            "blockcheck.runner.select_tcp_targets",
            side_effect=lambda targets, max_count=12, per_provider_cap=2: targets,
        ), patch(
            "blockcheck.runner.probe_tcp_target_health",
            return_value=(True, "HTTP 200", 10.0),
        ), patch(
            "blockcheck.runner.check_tcp_16_20",
            return_value=tcp_result,
        ):
            results = runner._run_tcp_phase()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].target_name, "CF-01")
        self.assertEqual(results[0].raw_data.get("target_id"), "CF-01")
        self.assertEqual(results[0].raw_data.get("provider"), "Cloudflare")

    def test_isp_phase_uses_https_detection_when_http_is_clean(self):
        runner = BlockcheckRunner(mode="dpi_only", parallel=1)
        target = TargetResult(name="Example", value="https://example.com")

        http_clean = SingleTestResult(
            target_name="example.com",
            test_type=ResultType.ISP_PAGE,
            status=ResultStatus.OK,
            detail="No HTTP injection detected",
        )
        https_block_page = SingleTestResult(
            target_name="example.com",
            test_type=ResultType.ISP_PAGE,
            status=ResultStatus.FAIL,
            error_code="ISP_PAGE",
            detail="Redirected to ISP block page",
        )

        with patch("blockcheck.runner.check_http_injection", return_value=http_clean), patch(
            "blockcheck.runner.detect_isp_page",
            return_value=https_block_page,
        ):
            runner._run_isp_phase([target])

        self.assertEqual(len(target.tests), 1)
        self.assertEqual(target.tests[0].error_code, "ISP_PAGE")

    def test_ping_phase_skips_tcp_aggregate_target(self):
        runner = BlockcheckRunner(mode="full", parallel=1)
        tcp_target = TargetResult(name="TCP 16-20KB", value="TCP:16-20KB")

        with patch("blockcheck.runner.ping_host") as ping_host_mock:
            runner._run_ping_phase([tcp_target], [])

        ping_host_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
