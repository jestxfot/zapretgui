# tests/test_strategy_inference.py
"""
Tests for strategy_id inference from args.

Run with: pytest tests/test_strategy_inference.py -v
"""

import pytest
from preset_zapret2.strategy_inference import normalize_args, infer_strategy_id_from_args


class TestNormalizeArgs:
    """Tests for normalize_args function"""

    def test_empty_args(self):
        """Empty args should return empty string"""
        assert normalize_args("") == ""
        assert normalize_args("   ") == ""
        assert normalize_args("\n\n") == ""

    def test_single_line(self):
        """Single line should be lowercased and stripped"""
        result = normalize_args("--lua-desync=multisplit:pos=1,midsld")
        assert result == "--lua-desync=multisplit:pos=1,midsld"

    def test_multiline(self):
        """Multiple lines should be sorted"""
        input_args = """--lua-desync=multisplit:pos=1,midsld
--lua-desync=disorder:pos=1"""
        result = normalize_args(input_args)
        # Should be sorted alphabetically
        assert result == "--lua-desync=disorder:pos=1\n--lua-desync=multisplit:pos=1,midsld"

    def test_whitespace_handling(self):
        """Should strip whitespace"""
        input_args = "  --lua-desync=fake  \n  --lua-desync=split  "
        result = normalize_args(input_args)
        assert result == "--lua-desync=fake\n--lua-desync=split"

    def test_empty_lines(self):
        """Should remove empty lines"""
        input_args = "--lua-desync=fake\n\n--lua-desync=split\n\n"
        result = normalize_args(input_args)
        assert result == "--lua-desync=fake\n--lua-desync=split"


class TestInferStrategyId:
    """Tests for infer_strategy_id_from_args function"""

    def test_empty_args(self):
        """Empty args should return 'none'"""
        result = infer_strategy_id_from_args("youtube", "", "tcp")
        assert result == "none"

    def test_unknown_category(self):
        """Unknown category should return 'none'"""
        result = infer_strategy_id_from_args("unknown_category_123", "--lua-desync=fake", "tcp")
        assert result == "none"

    def test_invalid_args(self):
        """Invalid args should return 'none' (no match)"""
        result = infer_strategy_id_from_args("youtube", "--unknown-arg=value", "tcp")
        assert result == "none"

    @pytest.mark.skip(reason="Requires strategies_registry to be loaded")
    def test_valid_inference(self):
        """Valid args should return correct strategy_id"""
        # This test requires actual strategies to be loaded
        # Skip in CI/CD, run manually on Windows with full app
        result = infer_strategy_id_from_args(
            "youtube",
            "--lua-desync=multisplit:pos=1,midsld",
            "tcp"
        )
        assert result != "none"
        assert "split" in result.lower()


class TestEdgeCases:
    """Tests for edge cases"""

    def test_case_insensitive(self):
        """Normalization should be case-insensitive"""
        args1 = "--lua-desync=FAKE"
        args2 = "--lua-desync=fake"
        assert normalize_args(args1) == normalize_args(args2)

    def test_order_independent(self):
        """Order of arguments should not matter"""
        args1 = "--lua-desync=fake\n--lua-desync=split"
        args2 = "--lua-desync=split\n--lua-desync=fake"
        assert normalize_args(args1) == normalize_args(args2)

    def test_multiline_with_newlines(self):
        """Should handle different newline styles"""
        args_unix = "--lua-desync=fake\n--lua-desync=split"
        args_windows = "--lua-desync=fake\r\n--lua-desync=split"
        # Both should normalize to same result
        result_unix = normalize_args(args_unix)
        result_windows = normalize_args(args_windows)
        assert result_unix == result_windows


if __name__ == "__main__":
    # Run basic tests without pytest
    print("Testing normalize_args...")
    assert normalize_args("") == ""
    assert normalize_args("--lua-desync=fake") == "--lua-desync=fake"
    print("✅ normalize_args tests passed")

    print("\nTesting infer_strategy_id_from_args...")
    assert infer_strategy_id_from_args("youtube", "", "tcp") == "none"
    assert infer_strategy_id_from_args("unknown_category", "--lua-desync=fake", "tcp") == "none"
    print("✅ infer_strategy_id_from_args tests passed")

    print("\n✅ All tests passed!")
