import unittest
import sys
from pathlib import Path
import base64
import json


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
        # Generate an ephemeral keypair for this test and patch the trusted keys map.
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key()

        pub_raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.kid = "test"
        self.donate.TRUSTED_PUBLIC_KEYS_B64 = {self.kid: base64.b64encode(pub_raw).decode("ascii")}

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

        msg = json.dumps(self.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig = priv.sign(msg)
        sig_b64url = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")

        self.resp = {
            "success": True,
            "kid": self.kid,
            "sig": sig_b64url,
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
