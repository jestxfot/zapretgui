import unittest

from ui.page_names import PageName
from ui.text_catalog import find_search_entries, get_nav_page_label


def _matched_pages(query: str, language: str = "ru") -> set[PageName]:
    matches = find_search_entries(query, language=language, max_results=50)
    return {match.entry.page_name for match in matches}


class GlobalSearchLocalizationTests(unittest.TestCase):
    def test_support_page_found_by_english_query_in_ru_ui(self):
        pages = _matched_pages("support channels", language="ru")
        self.assertIn(PageName.SUPPORT, pages)

    def test_servers_page_found_by_russian_query_in_en_ui(self):
        pages = _matched_pages("серверы обновлений", language="en")
        self.assertIn(PageName.SERVERS, pages)

    def test_custom_domains_page_found_by_catalog_subtitle_text(self):
        pages = _matched_pages("subdomains are handled automatically", language="ru")
        self.assertIn(PageName.CUSTOM_DOMAINS, pages)

    def test_netrogat_page_found_by_button_text(self):
        pages = _matched_pages("add missing", language="ru")
        self.assertIn(PageName.NETROGAT, pages)

    def test_nav_labels_for_non_sidebar_pages_are_localized(self):
        self.assertEqual(get_nav_page_label(PageName.SUPPORT, language="en"), "Support")
        self.assertEqual(get_nav_page_label(PageName.SERVERS, language="ru"), "Серверы")

    def test_support_page_ranked_first_for_support_query(self):
        matches = find_search_entries("support", language="ru", max_results=10)
        self.assertTrue(matches)
        self.assertEqual(matches[0].entry.page_name, PageName.SUPPORT)

    def test_youtube_query_prefers_about_page(self):
        matches = find_search_entries("youtube", language="ru", max_results=10)
        self.assertTrue(matches)
        self.assertEqual(matches[0].entry.page_name, PageName.ABOUT)
        self.assertEqual(matches[0].entry.tab_key, "help")

    def test_about_news_text_is_searchable(self):
        pages = _matched_pages("fediverse updates", language="ru")
        self.assertIn(PageName.ABOUT, pages)

    def test_forum_query_prefers_about_help_tab(self):
        matches = find_search_entries("forum", language="ru", max_results=10)
        self.assertTrue(matches)
        self.assertEqual(matches[0].entry.page_name, PageName.ABOUT)
        self.assertEqual(matches[0].entry.tab_key, "help")

    def test_udp_games_query_prefers_strategy_scan_tab(self):
        matches = find_search_entries("udp games", language="ru", max_results=10)
        self.assertTrue(matches)
        self.assertEqual(matches[0].entry.page_name, PageName.BLOCKCHECK)
        self.assertEqual(matches[0].entry.tab_key, "strategy_scan")

    def test_dns_spoofing_query_prefers_dns_tab(self):
        matches = find_search_entries("dns spoofing", language="ru", max_results=10)
        self.assertTrue(matches)
        self.assertEqual(matches[0].entry.page_name, PageName.BLOCKCHECK)
        self.assertEqual(matches[0].entry.tab_key, "dns_spoofing")

    def test_orchestra_whitelist_section_text_routes_to_whitelist_tab(self):
        matches = find_search_entries("system domains", language="ru", max_results=10)
        self.assertTrue(matches)
        self.assertEqual(matches[0].entry.page_name, PageName.ORCHESTRA_SETTINGS)
        self.assertEqual(matches[0].entry.tab_key, "whitelist")


if __name__ == "__main__":
    unittest.main()
