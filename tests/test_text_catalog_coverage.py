import re
import unittest
from pathlib import Path

from ui import text_catalog


TR_CATALOG_PATTERN = re.compile(r'tr_catalog\(\s*["\']([^"\']+)["\']')


class TextCatalogCoverageTests(unittest.TestCase):
    def test_all_ui_tr_catalog_keys_exist_in_text_catalog(self):
        known_keys = set(text_catalog.TEXTS.keys())
        missing: set[str] = set()

        ui_root = Path(__file__).resolve().parents[1] / "ui"
        for path in ui_root.rglob("*.py"):
            if path.name == "text_catalog.py":
                continue

            source = path.read_text(encoding="utf-8", errors="ignore")
            for match in TR_CATALOG_PATTERN.finditer(source):
                key = match.group(1)
                if key.startswith(("page.", "nav.", "sidebar.", "tab.", "common.")) and key not in known_keys:
                    missing.add(key)

        self.assertEqual(sorted(missing), [])

    def test_all_page_prefixes_are_covered_by_search_mapping(self):
        all_page_prefixes: set[str] = set()
        for key in text_catalog.TEXTS:
            if not key.startswith("page."):
                continue
            parts = key.split(".")
            if len(parts) < 3:
                continue
            all_page_prefixes.add(f"page.{parts[1]}.")

        covered_prefixes: set[str] = set()
        for prefixes in text_catalog._PAGE_SEARCH_PREFIXES.values():
            covered_prefixes.update(prefixes)

        self.assertEqual(sorted(all_page_prefixes - covered_prefixes), [])


if __name__ == "__main__":
    unittest.main()
