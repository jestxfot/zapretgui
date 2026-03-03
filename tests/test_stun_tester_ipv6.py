import socket
import struct
import unittest
from unittest.mock import patch

from blockcheck.models import TestStatus as ResultStatus
from blockcheck.stun_tester import parse_stun_response, test_stun as run_stun_probe


def _build_ipv6_xor_mapped_response(transaction_id: bytes, ip: str, port: int) -> bytes:
    magic_cookie = 0x2112A442
    ip_bytes = socket.inet_pton(socket.AF_INET6, ip)
    xor_key = struct.pack(">I", magic_cookie) + transaction_id
    xored_ip = bytes(byte ^ xor_key[idx] for idx, byte in enumerate(ip_bytes))

    xor_port = port ^ (magic_cookie >> 16)
    attr_value = b"\x00\x02" + struct.pack(">H", xor_port) + xored_ip
    attr = struct.pack(">HH", 0x0020, len(attr_value)) + attr_value

    header = struct.pack(">HHI", 0x0101, len(attr), magic_cookie) + transaction_id
    return header + attr


class StunTesterIpv6Tests(unittest.TestCase):
    def test_parse_stun_response_supports_ipv6_xor_mapped_address(self):
        txid = bytes.fromhex("0102030405060708090a0b0c")
        response = _build_ipv6_xor_mapped_response(txid, "2001:db8::1234", 54321)

        parsed = parse_stun_response(response)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["family"], "IPv6")
        self.assertEqual(parsed["ip"], "2001:db8::1234")
        self.assertEqual(parsed["port"], 54321)

    def test_test_stun_can_probe_forced_ipv6_family(self):
        destination = ("2001:db8::10", 3478, 0, 0)

        class FakeSocket:
            def __init__(self, family: int, socktype: int, proto: int):
                self.family = family
                self.socktype = socktype
                self.proto = proto
                self._request = b""
                self._addr = destination

            def settimeout(self, _timeout: float) -> None:
                return

            def sendto(self, payload: bytes, addr: tuple) -> None:
                self._request = payload
                self._addr = addr

            def recvfrom(self, _size: int) -> tuple[bytes, tuple]:
                txid = self._request[8:20]
                response = _build_ipv6_xor_mapped_response(txid, "2001:db8::beef", 50000)
                return response, self._addr

            def close(self) -> None:
                return

        with patch(
            "blockcheck.stun_tester.socket.getaddrinfo",
            return_value=[
                (socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", destination),
            ],
        ), patch("blockcheck.stun_tester.socket.socket", side_effect=FakeSocket):
            result = run_stun_probe(
                host="stun.example.com",
                port=3478,
                timeout=4,
                retries=1,
                family=socket.AF_INET6,
            )

        self.assertEqual(result.status, ResultStatus.OK)
        self.assertEqual(result.raw_data.get("family"), "IPv6")
        self.assertEqual(result.raw_data.get("resolved_family"), "IPv6")


if __name__ == "__main__":
    unittest.main()
