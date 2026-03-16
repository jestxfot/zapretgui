import ast
import re
import unittest
from pathlib import Path


TARGET_CALLS = {
    "setText",
    "setPlaceholderText",
    "setToolTip",
    "setTitle",
    "setWindowTitle",
    "addItem",
    "setItemText",
    "setHorizontalHeaderLabels",
    "setVerticalHeaderLabels",
}

TARGET_CTORS = {
    "QLabel",
    "BodyLabel",
    "CaptionLabel",
    "TitleLabel",
    "SubtitleLabel",
    "PushButton",
    "PrimaryPushButton",
    "ActionButton",
    "PrimaryActionButton",
    "HyperlinkButton",
    "ToolButton",
    "LineEdit",
    "MessageBox",
}

ALLOWED_EXACT = {
    "",
    "n",
    "d",
    "✓",
    "✗",
    "✕",
    "●",
    "—",
    "0%",
    "100%",
    "8.8.8.8",
    "8.8.4.4",
}

ROUTE_KEY_RE = re.compile(r"^[a-z0-9_]+$")


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_allowed_literal(value: str) -> bool:
    stripped = value.strip()
    if stripped in ALLOWED_EXACT:
        return True
    if ROUTE_KEY_RE.fullmatch(stripped):
        return True
    if stripped.startswith(("fa5", "mdi.", "res/", ":/", "qrc:/", "#")):
        return True
    return False


class PagesUseCatalogStringsTests(unittest.TestCase):
    def test_pages_do_not_use_hardcoded_user_visible_literals(self):
        repo_root = Path(__file__).resolve().parents[1]
        pages_root = repo_root / "ui" / "pages"

        violations: list[str] = []

        for path in pages_root.rglob("*.py"):
            source = path.read_text(encoding="utf-8", errors="ignore")
            try:
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                name = _call_name(node.func)
                if not name or name in {"tr_catalog", "tr"}:
                    continue

                if name in TARGET_CALLS and node.args:
                    value = _string_literal(node.args[0])
                    if value is not None and not _is_allowed_literal(value):
                        violations.append(f"{path.as_posix()}:{node.lineno} {name} -> {value!r}")

                if name in TARGET_CTORS and node.args:
                    value = _string_literal(node.args[0])
                    if value is not None and not _is_allowed_literal(value):
                        violations.append(f"{path.as_posix()}:{node.lineno} {name} -> {value!r}")

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
