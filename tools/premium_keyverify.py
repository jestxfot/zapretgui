#!/usr/bin/env python3
import argparse
import base64
import json
import sys


def _fatal(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _b64_decode(s: str) -> bytes:
    s = (s or "").strip()
    if not s:
        return b""
    try:
        # Users often copy without '=' padding. Normalize to correct padding.
        s = s + ("=" * (-len(s) % 4))
        return base64.b64decode(s)
    except Exception as e:
        _fatal(f"invalid base64: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Ed25519 priv/pub base64 (raw 32 bytes) match.")
    parser.add_argument("--priv", required=True, help="priv_b64 (raw 32 bytes)")
    parser.add_argument("--pub", required=True, help="pub_b64 (raw 32 bytes)")
    args = parser.parse_args()

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
    except Exception as e:
        _fatal(f"cryptography not available ({e}). Install: python3 -m pip install cryptography")

    priv_raw = _b64_decode(args.priv)
    pub_raw = _b64_decode(args.pub)

    if len(priv_raw) != 32:
        _fatal(f"bad private key length: {len(priv_raw)} (expected 32)")
    if len(pub_raw) != 32:
        _fatal(f"bad public key length: {len(pub_raw)} (expected 32)")

    priv = Ed25519PrivateKey.from_private_bytes(priv_raw)
    pub = Ed25519PublicKey.from_public_bytes(pub_raw)

    derived_pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if derived_pub != pub_raw:
        _fatal("pub_b64 does not match the provided priv_b64")

    msg = json.dumps({"test": 1}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = priv.sign(msg)
    pub.verify(sig, msg)

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
