#!/usr/bin/env python3
"""Test script for preset_defaults functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that new functions can be imported."""
    print("Testing imports...")
    try:
        from preset_zapret2 import ensure_default_preset_exists, restore_default_preset
        from preset_zapret2.preset_defaults import DEFAULT_PRESET_CONTENT
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_constant_content():
    """Test that DEFAULT_PRESET_CONTENT has correct structure."""
    print("\nTesting DEFAULT_PRESET_CONTENT...")
    try:
        from preset_zapret2.preset_defaults import DEFAULT_PRESET_CONTENT

        # Check that it's not empty
        assert len(DEFAULT_PRESET_CONTENT) > 0, "Content is empty"
        print(f"  - Length: {len(DEFAULT_PRESET_CONTENT)} chars")

        # Check for key markers
        assert "# Preset: Default" in DEFAULT_PRESET_CONTENT
        assert "# Builtin: true" in DEFAULT_PRESET_CONTENT
        assert "--lua-init=@lua/zapret-lib.lua" in DEFAULT_PRESET_CONTENT
        assert "# Category: youtube" in DEFAULT_PRESET_CONTENT
        assert "# Category: discord" in DEFAULT_PRESET_CONTENT
        assert "# Category: discord_voice" in DEFAULT_PRESET_CONTENT
        print("  - Contains all expected markers")

        print("✅ DEFAULT_PRESET_CONTENT is valid")
        return True
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def test_function_signatures():
    """Test that functions have correct signatures."""
    print("\nTesting function signatures...")
    try:
        from preset_zapret2 import ensure_default_preset_exists, restore_default_preset

        # Check that functions are callable
        assert callable(ensure_default_preset_exists)
        assert callable(restore_default_preset)
        print("  - Both functions are callable")

        # Check docstrings
        assert ensure_default_preset_exists.__doc__ is not None
        assert restore_default_preset.__doc__ is not None
        print("  - Both functions have docstrings")

        print("✅ Function signatures are valid")
        return True
    except Exception as e:
        print(f"❌ Signature check failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing preset_defaults implementation")
    print("=" * 60)

    results = []
    results.append(test_imports())
    results.append(test_constant_content())
    results.append(test_function_signatures())

    print("\n" + "=" * 60)
    if all(results):
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
