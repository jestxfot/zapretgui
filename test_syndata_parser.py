#!/usr/bin/env python3
"""
Test script for syndata/send/out-range parsing in txt_preset_parser.py
"""

from preset_zapret2.txt_preset_parser import (
    extract_syndata_from_args,
    extract_out_range_from_args,
    extract_send_from_args,
    parse_preset_content
)

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

def test_full_preset_parsing():
    """Test full preset with syndata/send/out-range"""
    print("=== Testing full preset parsing ===")

    preset_content = """# Preset: Test Preset
# ActivePreset: test_preset

--lua-init=@lua/zapret-lib.lua
--wf-tcp-out=443

--filter-tcp=443
--hostlist=youtube.txt
--lua-desync=multisplit:pos=1,midsld
--syndata=blob:tls_google,autottl:-2,autottl_min:3,autottl_max:20
--out-range=-n8
--send=repeats:2,ttl:0

--new

--filter-udp=443
--hostlist=discord.txt
--lua-desync=fake:blob=quic1
--out-range=-d100
"""

    from preset_zapret2.txt_preset_parser import parse_preset_content
    data = parse_preset_content(preset_content)

    print(f"Preset name: {data.name}")
    print(f"Active preset: {data.active_preset}")
    print(f"Categories: {len(data.categories)}")

    # Check first category (youtube tcp)
    block1 = data.categories[0]
    print(f"\nBlock 1: {block1.category}:{block1.protocol}")
    print(f"  syndata_dict: {block1.syndata_dict}")

    assert block1.category == 'youtube'
    assert block1.protocol == 'tcp'
    assert block1.syndata_dict is not None
    assert block1.syndata_dict['enabled'] == True
    assert block1.syndata_dict['blob'] == 'tls_google'
    assert block1.syndata_dict['out_range'] == 8
    assert block1.syndata_dict['out_range_mode'] == 'n'
    assert block1.syndata_dict['send_repeats'] == 2
    print("✓ Block 1 syndata parsed correctly\n")

    # Check second category (discord udp)
    block2 = data.categories[1]
    print(f"Block 2: {block2.category}:{block2.protocol}")
    print(f"  syndata_dict: {block2.syndata_dict}")

    assert block2.category == 'discord'
    assert block2.protocol == 'udp'
    assert block2.syndata_dict is not None
    assert block2.syndata_dict['out_range'] == 100
    assert block2.syndata_dict['out_range_mode'] == 'd'
    print("✓ Block 2 syndata parsed correctly\n")

if __name__ == "__main__":
    print("Starting syndata parser tests...\n")

    try:
        test_syndata_parsing()
        test_out_range_parsing()
        test_send_parsing()
        test_full_preset_parsing()

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
