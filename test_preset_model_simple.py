"""
Тест проверки исправлений в preset_model.py (без emoji для Windows)
"""

import sys
sys.path.insert(0, r"H:\Privacy\zapretgui")

from preset_zapret2.preset_model import CategoryConfig, SyndataSettings

def test_out_range_format():
    """Проверяем формат --out-range=-n8"""
    print("\n=== Test 1: --out-range format ===")

    syndata = SyndataSettings(
        enabled=True,
        out_range=8,
        out_range_mode="n"
    )

    cat = CategoryConfig(
        name="test",
        tcp_args="--lua-desync=fake",
        syndata=syndata
    )

    out_range_arg = cat._get_out_range_args()
    print(f"Generated argument: {out_range_arg}")

    expected = "--out-range=-n8"
    if out_range_arg == expected:
        print(f"[PASS] Format is correct: '{expected}'")
        return True
    else:
        print(f"[FAIL] Expected '{expected}', got '{out_range_arg}'")
        return False

def test_args_order():
    """Проверяем порядок аргументов: out-range -> send -> syndata -> strategy"""
    print("\n=== Test 2: Arguments order ===")

    syndata = SyndataSettings(
        enabled=True,
        blob="tls_google",
        out_range=8,
        out_range_mode="n",
        send_enabled=True,
        send_repeats=2
    )

    cat = CategoryConfig(
        name="test",
        tcp_args="--lua-desync=fake",
        syndata=syndata
    )

    full_args = cat.get_full_tcp_args()
    print(f"Full TCP arguments:\n{full_args}")

    parts = full_args.split()
    print(f"\nArguments order:")
    for i, part in enumerate(parts, 1):
        print(f"  {i}. {part}")

    # Check order
    checks = [
        (0, "--out-range=-n8", "out-range first"),
        (1, "--send=repeats:2", "send second"),
        (2, "--syndata=blob:tls_google", "syndata third"),
        (3, "--lua-desync=fake", "strategy last")
    ]

    success = True
    for idx, expected_prefix, description in checks:
        if idx >= len(parts):
            print(f"  [FAIL] Missing argument: {expected_prefix}")
            success = False
            continue

        actual = parts[idx]
        if actual.startswith(expected_prefix.split("=")[0]):
            print(f"  [PASS] Position {idx+1} correct ({description}): {actual}")
        else:
            print(f"  [FAIL] Position {idx+1} wrong: expected '{expected_prefix}', got '{actual}'")
            success = False

    return success

def test_udp_args_order():
    """Проверяем порядок UDP аргументов"""
    print("\n=== Test 3: UDP arguments order ===")

    syndata = SyndataSettings(
        enabled=True,
        blob="quic1",
        out_range=5,
        out_range_mode="d",
        send_enabled=True,
        send_repeats=3
    )

    cat = CategoryConfig(
        name="test",
        udp_args="--lua-desync=tamper:sld",
        syndata=syndata
    )

    full_args = cat.get_full_udp_args()
    print(f"Full UDP arguments:\n{full_args}")

    parts = full_args.split()
    print(f"\nArguments order:")
    for i, part in enumerate(parts, 1):
        print(f"  {i}. {part}")

    success = True

    # Check out-range is first
    if parts[0].startswith("--out-range=-d"):
        print(f"  [PASS] Out-range is first")
    else:
        print(f"  [FAIL] Out-range is NOT first")
        success = False

    # Check strategy is last
    if "--lua-desync=" in parts[-1]:
        print(f"  [PASS] Strategy is last")
    else:
        print(f"  [FAIL] Strategy is NOT last")
        success = False

    return success

if __name__ == "__main__":
    print("Testing preset_model.py fixes")
    print("=" * 60)

    results = []
    results.append(("Out-range format", test_out_range_format()))
    results.append(("TCP arguments order", test_args_order()))
    results.append(("UDP arguments order", test_udp_args_order()))

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {name}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed!")
        sys.exit(1)
