#!/usr/bin/env python3
"""
Simple test for syndata/send/out-range parsing functions.
Tests only the parsing functions without importing full modules.
"""

import re
from typing import Dict

def extract_syndata_from_args(args: str) -> Dict:
    """Extracts syndata parameters from --syndata=blob:...,autottl:..."""
    match = re.search(r'--syndata=([^\s\n]+)', args)
    if not match:
        return {}

    syndata_str = match.group(1)
    parts = syndata_str.split(',')

    result = {'enabled': True}

    for part in parts:
        if ':' not in part:
            continue
        key, value = part.split(':', 1)

        if key == 'blob':
            result['blob'] = value
        elif key == 'tls_mod':
            result['tls_mod'] = value
        elif key == 'autottl':
            result['autottl_delta'] = int(value)
        elif key == 'autottl_min':
            result['autottl_min'] = int(value)
        elif key == 'autottl_max':
            result['autottl_max'] = int(value)
        elif key == 'tcp_flags_unset':
            result['tcp_flags_unset'] = value

    return result


def extract_out_range_from_args(args: str) -> Dict:
    """Extracts --out-range=-n8 or --out-range=-d100"""
    match = re.search(r'--out-range=-([nd])(\d+)', args)
    if not match:
        return {}

    mode = match.group(1)
    value = int(match.group(2))

    return {
        'out_range': value,
        'out_range_mode': mode
    }


def extract_send_from_args(args: str) -> Dict:
    """Extracts send parameters from --send=repeats:2,ttl:0"""
    match = re.search(r'--send=([^\s\n]+)', args)
    if not match:
        return {}

    send_str = match.group(1)
    parts = send_str.split(',')

    result = {'send_enabled': True}

    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            if key == 'repeats':
                result['send_repeats'] = int(value)
            elif key == 'ttl':
                result['send_ip_ttl'] = int(value)
            elif key == 'ttl6':
                result['send_ip6_ttl'] = int(value)
            elif key == 'ip_id':
                result['send_ip_id'] = value
        elif part == 'badsum:true':
            result['send_badsum'] = True

    return result


def test_syndata_parsing():
    """Test syndata parameter parsing"""
    print("=== Testing syndata parsing ===")

    # Test 1: Full syndata string
    args1 = "--syndata=blob:tls_google,tls_mod:none,autottl:-2,autottl_min:3,autottl_max:20"
    result1 = extract_syndata_from_args(args1)
    print(f"Test 1 (full syndata): {result1}")
    assert result1['enabled'] == True
    assert result1['blob'] == 'tls_google'
    assert result1['autottl_delta'] == -2
    assert result1['autottl_min'] == 3
    assert result1['autottl_max'] == 20
    print("✓ Test 1 passed\n")

    # Test 2: Minimal syndata
    args2 = "--syndata=blob:tls_google"
    result2 = extract_syndata_from_args(args2)
    print(f"Test 2 (minimal syndata): {result2}")
    assert result2['enabled'] == True
    assert result2['blob'] == 'tls_google'
    print("✓ Test 2 passed\n")

    # Test 3: No syndata
    args3 = "--lua-desync=split:pos=1"
    result3 = extract_syndata_from_args(args3)
    print(f"Test 3 (no syndata): {result3}")
    assert result3 == {}
    print("✓ Test 3 passed\n")

def test_out_range_parsing():
    """Test out-range parameter parsing"""
    print("=== Testing out-range parsing ===")

    # Test 1: -n8 (packets)
    args1 = "--out-range=-n8"
    result1 = extract_out_range_from_args(args1)
    print(f"Test 1 (-n8): {result1}")
    assert result1['out_range'] == 8
    assert result1['out_range_mode'] == 'n'
    print("✓ Test 1 passed\n")

    # Test 2: -d100 (delay)
    args2 = "--out-range=-d100"
    result2 = extract_out_range_from_args(args2)
    print(f"Test 2 (-d100): {result2}")
    assert result2['out_range'] == 100
    assert result2['out_range_mode'] == 'd'
    print("✓ Test 2 passed\n")

    # Test 3: -n12 (explicit mode)
    args3 = "--out-range=-n12"
    result3 = extract_out_range_from_args(args3)
    print(f"Test 3 (-n12): {result3}")
    assert result3['out_range'] == 12
    assert result3['out_range_mode'] == 'n'
    print("✓ Test 3 passed\n")

def test_send_parsing():
    """Test send parameter parsing"""
    print("=== Testing send parsing ===")

    # Test 1: Full send string
    args1 = "--send=repeats:2,ttl:0,ip_id:random"
    result1 = extract_send_from_args(args1)
    print(f"Test 1 (full send): {result1}")
    assert result1['send_enabled'] == True
    assert result1['send_repeats'] == 2
    assert result1['send_ip_ttl'] == 0
    assert result1['send_ip_id'] == 'random'
    print("✓ Test 1 passed\n")

    # Test 2: Minimal send
    args2 = "--send=repeats:1"
    result2 = extract_send_from_args(args2)
    print(f"Test 2 (minimal send): {result2}")
    assert result2['send_enabled'] == True
    assert result2['send_repeats'] == 1
    print("✓ Test 2 passed\n")

    # Test 3: No send
    args3 = "--lua-desync=split:pos=1"
    result3 = extract_send_from_args(args3)
    print(f"Test 3 (no send): {result3}")
    assert result3 == {}
    print("✓ Test 3 passed\n")

def test_combined_parsing():
    """Test combining all three parsers"""
    print("=== Testing combined parsing ===")

    block_args = """--filter-tcp=443
--hostlist=youtube.txt
--lua-desync=multisplit:pos=1,midsld
--syndata=blob:tls_google,autottl:-2,autottl_min:3,autottl_max:20
--out-range=-n8
--send=repeats:2,ttl:0"""

    syndata_dict = {}
    syndata_dict.update(extract_syndata_from_args(block_args))
    syndata_dict.update(extract_out_range_from_args(block_args))
    syndata_dict.update(extract_send_from_args(block_args))

    print(f"Combined result: {syndata_dict}")

    assert syndata_dict['enabled'] == True
    assert syndata_dict['blob'] == 'tls_google'
    assert syndata_dict['autottl_delta'] == -2
    assert syndata_dict['out_range'] == 8
    assert syndata_dict['out_range_mode'] == 'n'
    assert syndata_dict['send_enabled'] == True
    assert syndata_dict['send_repeats'] == 2
    assert syndata_dict['send_ip_ttl'] == 0

    print("✓ Combined parsing passed\n")

if __name__ == "__main__":
    print("Starting syndata parser tests...\n")

    try:
        test_syndata_parsing()
        test_out_range_parsing()
        test_send_parsing()
        test_combined_parsing()

        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
