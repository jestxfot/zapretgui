#!/usr/bin/env python3
import argparse
import base64
import sys


def _fatal(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Ed25519 keys for Zapret Premium response signing.")
    parser.add_argument("--kid", default="v1", help="Key id (kid) to print for copy/paste (default: v1)")
    args = parser.parse_args()

    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
    except Exception as e:
        _fatal(f"cryptography not available ({e}). Install: python3 -m pip install cryptography")

    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()

    priv_raw = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    priv_b64 = base64.b64encode(priv_raw).decode("ascii")
    pub_b64 = base64.b64encode(pub_raw).decode("ascii")

    kid = str(args.kid)

    print(f"priv_b64={priv_b64}")
    print(f"pub_b64={pub_b64}")
    print()
    print("copy/paste server:")
    print(f"  SIGNING_KEYS_B64[\"{kid}\"] = \"{priv_b64}\"")
    print("copy/paste client:")
    print(f"  TRUSTED_PUBLIC_KEYS_B64[\"{kid}\"] = \"{pub_b64}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

