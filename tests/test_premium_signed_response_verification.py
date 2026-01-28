import unittest
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

class PremiumSignedResponseVerificationTests(unittest.TestCase):
    def setUp(self):
        # Other tests may import a third-party `config` module and leave it in sys.modules.
        # Ensure `donater/donate.py` resolves THIS repo's `config` package.
        if "config" in sys.modules:
            del sys.modules["config"]
        import config as _repo_config
        sys.modules["config"] = _repo_config

        from donater import donate as donate_mod

        self.donate = donate_mod
        self.payload = {
            "v": 1,
            "type": "zapret_premium_status",
            "nonce": "test-nonce",
            "device_id": "device-123",
            "user_id": 42,
            "activated": True,
            "subscription_level": "zapretik",
            "expires_at": "2030-01-01T00:00:00",
            "days_remaining": 123,
            "issued_at": 1700000000,
            "valid_until": 1700003600,
            "message": "ok",
        }

        self.resp = {
            "success": True,
            "kid": "v1",
            "sig": "GBZLLd60Q0w-0ZCHrMtDCuuTVXBKJeBqFD1C4fYpSHZGo_cVl-SqrCOqahTEarW0Fc91XxLfe-ALn5YgeuxOAg",
            "signed": self.payload,
        }

    def test_valid_signature_ok(self):
        signed = self.donate._verify_signed_response(
            self.resp,
            expected_device_id="device-123",
            expected_nonce="test-nonce",
        )
        self.assertIsInstance(signed, dict)
        self.assertEqual(signed.get("device_id"), "device-123")
        self.assertTrue(signed.get("activated"))

    def test_wrong_device_id_rejected(self):
        signed = self.donate._verify_signed_response(
            self.resp,
            expected_device_id="device-999",
            expected_nonce="test-nonce",
        )
        self.assertIsNone(signed)

    def test_wrong_nonce_rejected(self):
        signed = self.donate._verify_signed_response(
            self.resp,
            expected_device_id="device-123",
            expected_nonce="other-nonce",
        )
        self.assertIsNone(signed)

    def test_modified_payload_rejected(self):
        tampered = dict(self.resp)
        tampered["signed"] = dict(self.payload)
        tampered["signed"]["activated"] = False

        signed = self.donate._verify_signed_response(
            tampered,
            expected_device_id="device-123",
            expected_nonce="test-nonce",
        )
        self.assertIsNone(signed)


if __name__ == "__main__":
    unittest.main()
