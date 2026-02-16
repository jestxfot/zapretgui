# ui/pages/my_categories_page.py
"""
Страница управления пользовательскими категориями (base_filter) для direct режимов.

Пользовательские категории хранятся вне папки установки:
  %APPDATA%/zapret/user_categories.txt

Требования:
- пользователь задаёт только: название категории + base_filter (строка аргументов);
- ключи создаются автоматически: user_category_N;
- файл user_categories.txt всегда перезаписывается "чистым" форматом (без старых полей);
- общий вертикальный скролл страницы (BasePage), без вложенных scroll areas.
"""

from __future__ import annotations

import os
import re
import shutil
import ipaddress
import subprocess
from pathlib import Path, PureWindowsPath
from typing import Callable, Optional

import qtawesome as qta
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from log import log
from ui.pages.base_page import BasePage
from ui.sidebar import ActionButton, SettingsCard
from ui.theme import get_theme_tokens, get_card_gradient_qss, get_tinted_surface_gradient_qss
from ui.widgets.line_edit_icons import set_line_edit_clear_button_icon


def _find_editor_command(file_path: str) -> tuple[list[str], str] | tuple[None, str]:
    """
    Returns (command, human_name) for opening a file in an editor.
    Priority: VSCode -> Notepad++ -> Notepad.
    """
    file_path = str(file_path)

    # VSCode: CLI (if installed on PATH)
    for exe in ("code", "code.cmd", "code.exe"):
        found = shutil.which(exe)
        if found:
            return ([found, "--reuse-window", file_path], "VSCode")

    # VSCode: typical install locations
    localapp = os.environ.get("LOCALAPPDATA") or ""
    prog = os.environ.get("ProgramFiles") or ""
    progx86 = os.environ.get("ProgramFiles(x86)") or ""
    vscode_candidates = [
        Path(localapp) / "Programs" / "Microsoft VS Code" / "Code.exe",
        Path(prog) / "Microsoft VS Code" / "Code.exe",
        Path(progx86) / "Microsoft VS Code" / "Code.exe",
    ]
    for p in vscode_candidates:
        try:
            if p and p.exists():
                return ([str(p), "--reuse-window", file_path], "VSCode")
        except Exception:
            continue

    # Notepad++: PATH or typical install locations
    for exe in ("notepad++", "notepad++.exe"):
        found = shutil.which(exe)
        if found:
            return ([found, file_path], "Notepad++")

    npp_candidates = [
        Path(prog) / "Notepad++" / "notepad++.exe",
        Path(progx86) / "Notepad++" / "notepad++.exe",
    ]
    for p in npp_candidates:
        try:
            if p and p.exists():
                return ([str(p), file_path], "Notepad++")
        except Exception:
            continue

    # Notepad: always present on Windows
    notepad = shutil.which("notepad.exe") or "notepad.exe"
    return ([notepad, file_path], "Notepad")


def _list_style() -> str:
    tokens = get_theme_tokens()
    return f"""
        QListWidget {{
            background: {tokens.surface_bg};
            border: 1px solid {tokens.divider};
            border-radius: 8px;
            padding: 6px;
            color: {tokens.fg};
        }}
        QListWidget::item {{ padding: 8px 10px; border-radius: 6px; }}
        QListWidget::item:selected {{ background: {tokens.accent_soft_bg}; color: {tokens.accent_hex}; }}
        QListWidget::item:hover {{ background: {tokens.surface_bg_hover}; }}
    """


def _input_style() -> str:
    tokens = get_theme_tokens()
    return f"""
        QLineEdit, QPlainTextEdit {{
            background-color: {tokens.surface_bg};
            color: {tokens.fg};
            border: 1px solid {tokens.surface_border};
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 12px;
        }}
        QPlainTextEdit {{
            font-family: 'Consolas', monospace;
            font-size: 11px;
        }}
        QLineEdit:hover, QPlainTextEdit:hover {{
            background-color: {tokens.surface_bg_hover};
            border: 1px solid {tokens.surface_border_hover};
        }}
        QLineEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {tokens.accent_hex};
        }}

        /* Error highlight: thin red-pastel border */
        QLineEdit[hasError="true"], QPlainTextEdit[hasError="true"] {{
            border: 1px solid rgba(255, 107, 107, 0.55);
            background-color: rgba(255, 107, 107, 0.08);
        }}
    """


def _error_banner_style() -> str:
    return """
        QLabel {
            background-color: rgba(255, 107, 107, 0.10);
            border: 1px solid rgba(255, 107, 107, 0.35);
            border-radius: 8px;
            padding: 10px 12px;
            color: #ff9c9c;
            font-size: 12px;
        }
    """


def _row_frame_style(*, is_dirty: bool) -> str:
    tokens = get_theme_tokens()
    if is_dirty:
        border = f"rgba({tokens.accent_rgb_str}, 0.35)"
        border_hover = f"rgba({tokens.accent_rgb_str}, 0.45)"
        bg = get_tinted_surface_gradient_qss(
            f"rgba({tokens.accent_rgb_str}, 0.10)",
            theme_name=tokens.theme_name,
        )
        bg_hover = get_tinted_surface_gradient_qss(
            f"rgba({tokens.accent_rgb_str}, 0.14)",
            theme_name=tokens.theme_name,
            hover=True,
        )
    else:
        border = tokens.divider
        border_hover = tokens.surface_border_hover
        bg = get_card_gradient_qss(tokens.theme_name)
        bg_hover = get_card_gradient_qss(tokens.theme_name, hover=True)

    return f"""
        QFrame {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        QFrame:hover {{
            background: {bg_hover};
            border: 1px solid {border_hover};
        }}
    """


def _format_category_details(cat: dict) -> str:
    if not cat:
        return ""

    preferred = [
        "key",
        "full_name",
        "description",
        "tooltip",
        "color",
        "default_strategy",
        "ports",
        "protocol",
        "order",
        "command_order",
        "needs_new_separator",
        "command_group",
        "icon_name",
        "icon_color",
        "base_filter",
        "base_filter_hostlist",
        "base_filter_ipset",
        "strategy_type",
        "strip_payload",
        "requires_all_ports",
    ]

    lines: list[str] = []
    for k in preferred:
        if k not in cat:
            continue
        v = cat.get(k)
        if v is None:
            continue
        if k in ("description", "tooltip"):
            vv = str(v).replace("\\n", "\n")
        else:
            vv = str(v)
        lines.append(f"{k} = {vv}")

    for k in sorted((cat or {}).keys(), key=lambda x: str(x).lower()):
        if k in preferred or k.startswith("_"):
            continue
        v = (cat or {}).get(k)
        if v is None:
            continue
        lines.append(f"{k} = {v}")

    return "\n".join(lines).strip() + "\n"


def _is_user_category_key(key: str) -> bool:
    return bool(re.fullmatch(r"user_category_\d+", str(key or "").strip()))


class _IconButton(QPushButton):
    def __init__(self, icon_name: str, *, tooltip: str, color: str | None = None, parent=None):
        super().__init__(parent)
        tokens = get_theme_tokens()
        self._icon_name = icon_name
        self._default_color = color or tokens.fg
        self.setIcon(qta.icon(icon_name, color=self._default_color))
        self.setIconSize(QSize(18, 18))
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self._apply_style("default")

    def setAccent(self, accent: bool) -> None:  # noqa: N802 (Qt-like)
        self._apply_style("accent" if accent else "default")

    def setDangerConfirm(self, pending: bool) -> None:  # noqa: N802 (Qt-like)
        if pending:
            self.setIcon(qta.icon(self._icon_name, color="white"))
            self._apply_style("danger")
        else:
            self.setIcon(qta.icon(self._icon_name, color=self._default_color))
            self._apply_style("default")

    def _apply_style(self, kind: str) -> None:
        tokens = get_theme_tokens()
        if kind == "accent":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tokens.accent_soft_bg};
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{ background-color: {tokens.accent_soft_bg_hover}; }}
                QPushButton:pressed {{ background-color: {tokens.accent_soft_bg_hover}; }}
                QPushButton:disabled {{ background-color: {tokens.surface_bg}; }}
            """)
            return

        if kind == "danger":
            tokens = get_theme_tokens()
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255, 107, 107, 0.75);
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{ background-color: rgba(255, 107, 107, 0.85); }}
                QPushButton:pressed {{ background-color: rgba(255, 107, 107, 0.92); }}
                QPushButton:disabled {{ background-color: {tokens.surface_bg}; }}
            """)
            return

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.toggle_off_bg};
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: {tokens.toggle_off_bg_hover}; }}
            QPushButton:pressed {{ background-color: {tokens.toggle_off_bg_hover}; }}
            QPushButton:disabled {{ background-color: {tokens.surface_bg}; }}
        """)


class UserCategoryRow(QFrame):
    def __init__(
        self,
        *,
        key: str,
        full_name: str,
        base_filter: str,
        on_save: Callable[[str, str, str, "UserCategoryRow"], None],
        on_delete: Callable[[str, "UserCategoryRow"], None],
        parent=None,
    ):
        super().__init__(parent)
        self._key = str(key or "").strip()
        self._dirty = False
        self._delete_confirm_pending = False

        self._on_save_cb = on_save
        self._on_delete_cb = on_delete

        self._delete_confirm_timer = QTimer(self)
        self._delete_confirm_timer.setSingleShot(True)
        self._delete_confirm_timer.timeout.connect(self._reset_delete_confirm)

        self._build_ui()
        self.set_data(full_name=full_name, base_filter=base_filter, mark_clean=True)

    def _build_ui(self) -> None:
        self.setStyleSheet(_row_frame_style(is_dirty=False))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 10, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.key_label = QLabel(self._key)
        self.key_label.setStyleSheet(f"color: {get_theme_tokens().fg_faint}; font-size: 11px;")
        self.key_label.setFixedWidth(140)
        top.addWidget(self.key_label, 0)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название категории")
        self.name_input.setStyleSheet(_input_style())
        self.name_input.setProperty("noDrag", True)
        self.name_input.textChanged.connect(self._mark_dirty)
        top.addWidget(self.name_input, 1)

        self.save_btn = _IconButton("mdi.content-save", tooltip="Сохранить")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save_clicked)
        top.addWidget(self.save_btn, 0)

        self.delete_btn = _IconButton("mdi.delete", tooltip="Удалить", color="#ff6b6b")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        top.addWidget(self.delete_btn, 0)

        layout.addLayout(top)

        self.base_input = QPlainTextEdit()
        self.base_input.setPlaceholderText(
            "base_filter (можно вставить в несколько строк — при сохранении будет приведено к одной)"
        )
        self.base_input.setFixedHeight(88)
        self.base_input.setStyleSheet(_input_style())
        self.base_input.setProperty("noDrag", True)
        self.base_input.textChanged.connect(self._mark_dirty)
        layout.addWidget(self.base_input, 0)

    def key(self) -> str:
        return self._key

    def set_data(self, *, full_name: str, base_filter: str, mark_clean: bool) -> None:
        self.name_input.blockSignals(True)
        self.base_input.blockSignals(True)
        self.name_input.setText(str(full_name or ""))
        self.base_input.setPlainText(str(base_filter or ""))
        self.name_input.blockSignals(False)
        self.base_input.blockSignals(False)
        if mark_clean:
            self._set_dirty(False)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = bool(dirty)
        self.save_btn.setEnabled(self._dirty)
        self.save_btn.setAccent(self._dirty)
        self.setStyleSheet(_row_frame_style(is_dirty=self._dirty))

    def _mark_dirty(self) -> None:
        self._set_dirty(True)
        self._clear_errors()

    def _apply_error_state(self, widget: QWidget, is_error: bool) -> None:
        try:
            widget.setProperty("hasError", bool(is_error))
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        except Exception:
            pass

    def _clear_errors(self) -> None:
        self._apply_error_state(self.name_input, False)
        self._apply_error_state(self.base_input, False)

    def set_error(self, *, message: str, widgets: list[QWidget]) -> None:
        for w in widgets:
            self._apply_error_state(w, True)
        try:
            self.setToolTip(message)
        except Exception:
            pass

    def _reset_delete_confirm(self) -> None:
        self._delete_confirm_pending = False
        self.delete_btn.setDangerConfirm(False)
        self.delete_btn.setToolTip("Удалить")

    def _on_save_clicked(self) -> None:
        self._on_save_cb(self._key, self.name_input.text(), self.base_input.toPlainText(), self)

    def _on_delete_clicked(self) -> None:
        if not self._delete_confirm_pending:
            self._delete_confirm_pending = True
            self.delete_btn.setDangerConfirm(True)
            self.delete_btn.setToolTip("Нажмите ещё раз, чтобы удалить")
            self._delete_confirm_timer.start(3500)
            return
        self._delete_confirm_pending = False
        self._delete_confirm_timer.stop()
        self.delete_btn.setDangerConfirm(False)
        self.delete_btn.setToolTip("Удалить")
        self._on_delete_cb(self._key, self)


class MyCategoriesPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            title="Мои категории",
            subtitle="Здесь Вы можете добавить свою категорию (hostlist или ipset) для direct режима Zapret 1 и Zapret 2. По умолчанию идёт выбор протокола --filter (TCP или UDP), далее идёт выбор --hostlist= (для доменов --hostlist-domains=) или --ipset= (для айпи --ipset-ip=), после чего txt файл (относительный путь) или список доменов/айпи.",
            parent=parent,
        )
        self.parent_app = parent
        self._user_categories_file_path: Path | None = None

        self._system_categories: dict[str, dict] = {}
        self._user_categories: dict[str, dict] = {}  # only user_category_N keys

        self._build_ui()

    # ============================= UI ======================================

    def _build_ui(self) -> None:
        from strategy_menu.user_categories_store import get_user_categories_file_path

        self._user_categories_file_path = get_user_categories_file_path()
        path = str(self._user_categories_file_path)

        info_row = QWidget()
        info_layout = QHBoxLayout(info_row)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        info = QLabel(f"Файл пользовательских категорий: {path}")
        info.setStyleSheet(f"color: {get_theme_tokens().fg_muted}; font-size: 12px;")
        info_layout.addWidget(info, 1)

        self._open_config_btn = ActionButton("Открыть в редакторе", "mdi.open-in-new", accent=False)
        self._open_config_btn.setToolTip("Открыть user_categories.txt (VSCode / Notepad++ / Notepad)")
        self._open_config_btn.clicked.connect(self._on_open_user_categories_file)
        info_layout.addWidget(self._open_config_btn, 0, alignment=Qt.AlignmentFlag.AlignRight)

        self.layout.addWidget(info_row)

        self._build_system_card()
        self._build_add_card()
        self._build_user_card()

        self.reload()

    def _on_open_user_categories_file(self) -> None:
        """Opens user_categories.txt in an external editor (prefers VSCode/Notepad++)."""
        try:
            from strategy_menu.user_categories_store import get_user_categories_file_path, save_user_categories

            path = self._user_categories_file_path or get_user_categories_file_path()
            self._user_categories_file_path = path

            try:
                if not path.exists():
                    ok, err = save_user_categories({})
                    if not ok:
                        QMessageBox.warning(self, "Не удалось создать файл", err or "Не удалось создать user_categories.txt")
                        return
            except Exception as e:
                QMessageBox.warning(self, "Не удалось создать файл", str(e))
                return

            cmd, editor_name = _find_editor_command(str(path))
            if not cmd:
                QMessageBox.warning(self, "Редактор не найден", "Не удалось определить редактор для открытия файла.")
                return

            try:
                subprocess.Popen(cmd)
                log(f"Открыт файл пользовательских категорий в {editor_name}: {path}", "DEBUG")
            except Exception as e:
                QMessageBox.warning(self, "Не удалось открыть файл", f"{editor_name}: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def _build_system_card(self) -> None:
        card = SettingsCard("Системные категории (read-only)")

        split = QHBoxLayout()
        split.setSpacing(12)

        self._system_list = QListWidget()
        self._system_list.setMinimumWidth(280)
        self._system_list.currentRowChanged.connect(self._on_system_selected)
        self._system_list.setStyleSheet(_list_style())
        split.addWidget(self._system_list, 0)

        right = QWidget()
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(10)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._copy_to_clip_btn = ActionButton("Копировать в буфер", "mdi.content-copy", accent=False)
        self._copy_to_clip_btn.clicked.connect(self._on_copy_system_to_clipboard)
        actions.addWidget(self._copy_to_clip_btn)
        actions.addStretch()
        right_v.addLayout(actions)

        self._system_details = QPlainTextEdit()
        self._system_details.setReadOnly(True)
        self._system_details.setStyleSheet(_input_style())
        self._system_details.setProperty("noDrag", True)
        right_v.addWidget(self._system_details, 1)

        split.addWidget(right, 1)
        card.add_layout(split)
        self.layout.addWidget(card)

    def _build_add_card(self) -> None:
        card = SettingsCard("Добавить категорию")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.add_name = QLineEdit()
        self.add_name.setPlaceholderText("Название категории")
        self.add_name.setStyleSheet(_input_style())
        self.add_name.setProperty("noDrag", True)
        top.addWidget(self.add_name, 1)

        self.add_btn = ActionButton("Добавить", "mdi.plus", accent=True)
        self.add_btn.clicked.connect(self._on_add_clicked)
        top.addWidget(self.add_btn, 0)

        layout.addLayout(top)

        self.add_base = QPlainTextEdit()
        self.add_base.setPlaceholderText("Впишите сюда командную строку фильтра, вот несколько примеров:\n--filter-tcp=80,443 --hostlist=my.txt\n--filter-tcp=443-50000 --hostlist-domains=rknass.com\n--filter-tcp=80,443 --ipset=iprkn.txt\n--filter-udp=443 --ipset-ip=1.2.3.4/16")
        self.add_base.setFixedHeight(96)
        self.add_base.setStyleSheet(_input_style())
        self.add_base.setProperty("noDrag", True)
        layout.addWidget(self.add_base)

        card.add_layout(layout)
        self.layout.addWidget(card)

    def _build_user_card(self) -> None:
        card = SettingsCard("Пользовательские категории")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self._error_banner = QLabel("")
        self._error_banner.setStyleSheet(_error_banner_style())
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по категориям...")
        self.search_input.setClearButtonEnabled(True)
        set_line_edit_clear_button_icon(self.search_input)
        self.search_input.textChanged.connect(self._apply_user_filter)
        self.search_input.setStyleSheet(_input_style())
        self.search_input.setProperty("noDrag", True)
        top_row.addWidget(self.search_input, 1)

        self.refresh_btn = ActionButton("Обновить", "mdi.refresh", accent=False)
        self.refresh_btn.clicked.connect(self.reload)
        top_row.addWidget(self.refresh_btn, 0)

        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {get_theme_tokens().fg_muted}; font-size: 12px;")
        self.count_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.count_label.setText("0")
        self.count_label.setFixedWidth(self.count_label.sizeHint().width())
        top_row.addWidget(self.count_label, 0)

        layout.addLayout(top_row)

        self.rows_host = QWidget()
        self.rows_host.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.rows_host)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(10)
        self.rows_layout.addStretch(1)
        layout.addWidget(self.rows_host)

        card.add_layout(layout)
        self.layout.addWidget(card)

    # ============================= Data ====================================

    def reload(self) -> None:
        try:
            from strategy_menu.strategy_loader import load_categories
            from strategy_menu.user_categories_store import load_user_categories

            all_cats = load_categories() or {}
            self._system_categories = {k: v for k, v in all_cats.items() if (v or {}).get("_source") == "builtin"}

            raw_user = load_user_categories() or {}
            self._user_categories = {k: v for k, v in raw_user.items() if _is_user_category_key(k)}
        except Exception as e:
            log(f"MyCategoriesPage reload failed: {e}", "ERROR")
            self._system_categories = {}
            self._user_categories = {}

        self._fill_system_list()
        self._rebuild_user_rows()

    def _fill_system_list(self) -> None:
        self._system_list.blockSignals(True)
        self._system_list.clear()

        sys_keys = sorted(self._system_categories.keys(), key=lambda x: x.lower())
        for key in sys_keys:
            cat = self._system_categories.get(key) or {}
            name = str(cat.get("full_name") or key)
            item = QListWidgetItem(f"{name}\n{key}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._system_list.addItem(item)

        self._system_list.blockSignals(False)
        self._system_details.setPlainText("")

    def _rebuild_user_rows(self) -> None:
        while self.rows_layout.count() > 1:
            item = self.rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        def _sort_key(k: str) -> tuple[int, str]:
            m = re.fullmatch(r"user_category_(\d+)", str(k or ""))
            if m:
                return int(m.group(1)), str(k)
            return 10**9, str(k)

        keys = sorted(self._user_categories.keys(), key=_sort_key)
        for key in keys:
            cat = self._user_categories.get(key) or {}
            row = UserCategoryRow(
                key=key,
                full_name=str(cat.get("full_name") or ""),
                base_filter=str(cat.get("base_filter") or ""),
                on_save=self._on_row_save_requested,
                on_delete=self._on_row_delete_requested,
                parent=self.rows_host,
            )
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)

        self._apply_user_filter(self.search_input.text())

    # ============================= Helpers =================================

    def _get_selected_system_key(self) -> Optional[str]:
        item = self._system_list.currentItem()
        if not item:
            return None
        key = item.data(Qt.ItemDataRole.UserRole)
        return str(key).strip() if key else None

    def _apply_error_state(self, widget: QWidget, is_error: bool) -> None:
        try:
            widget.setProperty("hasError", bool(is_error))
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        except Exception:
            pass

    def _clear_errors(self) -> None:
        self._error_banner.hide()
        for w in (self.add_name, self.add_base):
            self._apply_error_state(w, False)

    def _set_error(self, msg: str, *, widgets: list[QWidget] | None = None) -> None:
        self._error_banner.setText(msg)
        self._error_banner.show()
        for w in widgets or []:
            self._apply_error_state(w, True)
        try:
            self.ensureWidgetVisible(self._error_banner, xMargin=0, yMargin=24)
        except Exception:
            pass

    def _normalize_args_line(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        return " ".join(t.replace("\r\n", "\n").replace("\r", "\n").split())

    def _normalize_lists_paths_in_base_filter(self, base_filter: str) -> str:
        """
        Normalizes list file references to `lists/<filename>`.

        Examples:
        - `--ipset=ipset-warp.txt` -> `--ipset=lists/ipset-warp.txt`
        - `--ipset=xbox` -> `--ipset=lists/ipset-xbox.txt` (bare ipset names map to ipset-*.txt)
        - `--hostlist=234` -> `--hostlist=lists/234.txt`
        - `--hostlist=some/folder/youtube.txt` -> `--hostlist=lists/youtube.txt`
        - `--hostlist=lists/sub/youtube.txt` -> `--hostlist=lists/youtube.txt`

        If user already wrote exactly `lists/<filename>`, it stays unchanged.
        """
        base_filter = self._normalize_args_line(base_filter)
        if not base_filter:
            return ""

        tokens = base_filter.split()
        out: list[str] = []
        for token in tokens:
            key, sep, value = token.partition("=")
            key_l = key.strip().lower()
            if not sep:
                out.append(token)
                continue

            if key_l not in ("--hostlist", "--ipset", "--hostlist-exclude", "--ipset-exclude"):
                out.append(token)
                continue

            raw = (value or "").strip()
            if not raw:
                out.append(token)
                continue

            at_prefix = "@" if raw.startswith("@") else ""
            if at_prefix:
                raw = raw[1:]

            raw = raw.strip().strip('"').strip("'")
            if not raw:
                out.append(token)
                continue

            filename = PureWindowsPath(raw).name
            if not filename:
                out.append(token)
                continue

            # For hostlist we accept shorthand without ".txt".
            if key_l in ("--hostlist", "--hostlist-exclude"):
                if not PureWindowsPath(filename).suffix:
                    filename = f"{filename}.txt"

            # For user categories, ipset files are commonly stored as `ipset-<name>.txt`.
            # To reduce "silent crash" confusion, allow shorthand `--ipset=xbox` which maps to that filename.
            if key_l in ("--ipset", "--ipset-exclude"):
                suffix = PureWindowsPath(filename).suffix
                if not suffix:
                    if filename.lower().startswith("ipset-"):
                        filename = f"{filename}.txt"
                    else:
                        filename = f"ipset-{filename}.txt"

            normalized = f"lists/{filename}"
            raw_norm = PureWindowsPath(raw).as_posix()

            if raw_norm == normalized:
                out.append(f"{key}={at_prefix}{raw_norm}")
            else:
                out.append(f"{key}={at_prefix}{normalized}")

        return " ".join(out)

    @staticmethod
    def _is_valid_ports_spec(value: str) -> bool:
        """
        Validates a winws ports specification:
        - "*" OR
        - comma-separated list of ports and/or ranges: "80,443" / "80-443" / "80,443-5000"
        """
        v = str(value or "").strip()
        if not v:
            return False
        if v == "*":
            return True

        for part in v.split(","):
            p = part.strip()
            if not p:
                return False
            if "-" in p:
                a, b = p.split("-", 1)
                if not a.isdigit() or not b.isdigit():
                    return False
                start = int(a)
                end = int(b)
                if start < 1 or end < 1 or start > 65535 or end > 65535:
                    return False
                if start > end:
                    return False
            else:
                if not p.isdigit():
                    return False
                port = int(p)
                if port < 1 or port > 65535:
                    return False

        return True

    def _validate_base_filter(self, base_filter: str) -> tuple[bool, str]:
        """
        Validates that base_filter starts with:
          1) --filter-tcp=<ports> OR --filter-udp=<ports>
             where <ports> is: digits or digits,digits,...
          2) followed by a single space and then:
             --hostlist=... OR --ipset=... OR --hostlist-domains=... OR --ipset-ip=...
        """
        base_filter = self._normalize_args_line(base_filter)
        if not base_filter:
            return False, "base_filter пустой"

        tokens = base_filter.split()
        if any(t.strip() == "--new" for t in tokens):
            return False, "base_filter не должен содержать `--new`"

        if len(tokens) < 2:
            return (
                False,
                "Нужно минимум 2 аргумента: `--filter-tcp=...|--filter-udp=...` и затем "
                "`--hostlist=...|--ipset=...|--hostlist-domains=...|--ipset-ip=...`",
            )

        filter_token = tokens[0].strip()
        list_token = tokens[1].strip()

        m = re.fullmatch(r"--filter-(tcp|udp)=([^\s]+)", filter_token)
        ports_part = m.group(2) if m else ""
        if not m or not self._is_valid_ports_spec(ports_part):
            return (
                False,
                "Первый аргумент должен быть `--filter-tcp=443`, `--filter-tcp=80-443` или "
                "`--filter-udp=443,50000` (без пробелов).",
            )

        if not re.fullmatch(r"--(hostlist|ipset|hostlist-domains|ipset-ip)=[^\s]+", list_token):
            return (
                False,
                "Второй аргумент должен быть `--hostlist=...` / `--ipset=...` / `--hostlist-domains=...` / `--ipset-ip=...` (через пробел).",
            )

        # Reject empty values like --hostlist=
        list_key, _sep, list_value = list_token.partition("=")
        list_key_l = list_key.strip().lower()
        list_value = (list_value or "").strip()
        if not list_value:
            return False, "Во втором аргументе должно быть значение после `=`."

        if list_key_l == "--ipset-ip":
            # Expect an IP (v4/v6) or CIDR; allow comma-separated values.
            parts = [p.strip() for p in list_value.split(",") if p.strip()]
            if not parts:
                return False, "`--ipset-ip=` должен содержать IPv4/IPv6 или CIDR (например: `1.2.3.4/16`)."
            for p in parts:
                try:
                    if "/" in p:
                        ipaddress.ip_network(p, strict=False)
                    else:
                        ipaddress.ip_address(p)
                except Exception:
                    return False, f"Неверный IP/CIDR в `--ipset-ip`: `{p}`."

        if list_key_l == "--hostlist-domains":
            # Expect comma-separated domains (not a .txt file path).
            if ".txt" in list_value.lower() or "/" in list_value or "\\" in list_value:
                return False, "`--hostlist-domains=` принимает домены через запятую (не путь к .txt)."

            domains = [d.strip() for d in list_value.split(",") if d.strip()]
            if not domains:
                return False, "`--hostlist-domains=` должен содержать домены через запятую (например: `example.com,sub.example.com`)."

            # Very small, pragmatic validator: allow optional '*.' prefix and punycode.
            label_re = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
            for d in domains:
                dd = d
                if dd.startswith("*."):
                    dd = dd[2:]
                if dd.endswith("."):
                    dd = dd[:-1]
                if not dd or len(dd) > 253 or "." not in dd:
                    return False, f"Неверный домен в `--hostlist-domains`: `{d}`."
                labels = dd.split(".")
                if any(not label_re.fullmatch(lbl) for lbl in labels):
                    return False, f"Неверный домен в `--hostlist-domains`: `{d}`."

        return True, ""

    def _next_user_key(self) -> str:
        used = set(self._system_categories.keys()) | set(self._user_categories.keys())
        i = 1
        while True:
            key = f"user_category_{i}"
            if key not in used:
                return key
            i += 1

    def _save_clean_file(self) -> bool:
        """
        Перезаписывает user_categories.txt чистым форматом:
        только key/full_name/base_filter для user_category_N.
        """
        clean: dict[str, dict] = {}
        for key in sorted(self._user_categories.keys(), key=lambda k: str(k).lower()):
            cat = self._user_categories.get(key) or {}
            k = str(cat.get("key") or key).strip()
            if not _is_user_category_key(k):
                continue
            name = str(cat.get("full_name") or "").strip()
            base = self._normalize_lists_paths_in_base_filter(str(cat.get("base_filter") or ""))
            if not name or not base:
                continue
            clean[k] = {"key": k, "full_name": name, "base_filter": base}

        try:
            from strategy_menu.user_categories_store import save_user_categories

            ok, err = save_user_categories(clean)
            if not ok:
                self._set_error(err or "Не удалось сохранить файл")
                return False
        except Exception as e:
            self._set_error(str(e))
            return False

        self._on_categories_changed()
        return True

    def _normalize_filter_token_for_match(self, token: str) -> str:
        """
        Best-effort normalization to match how preset-zapret2.txt stores list paths.

        The preset file typically contains one arg per line, with list values
        normalized to `lists/...` when a bare filename is used.
        """
        raw = (token or "").strip()
        if not raw:
            return ""
        if not raw.startswith("--"):
            return ""

        key, sep, value = raw.partition("=")
        key_l = key.strip().lower()
        if not sep:
            return key.strip()

        value = value.strip().strip('"').strip("'")
        at_prefix = "@" if value.startswith("@") else ""
        if at_prefix:
            value = value[1:]

        if key_l in ("--hostlist", "--ipset", "--hostlist-exclude", "--ipset-exclude"):
            # User categories normalize list paths to `lists/<filename>`.
            filename = PureWindowsPath(value).name
            if filename:
                value = f"lists/{filename}"
            else:
                value = value.replace("\\", "/")
            return f"{key.strip()}={at_prefix}{value}"

        return f"{key.strip()}={at_prefix}{value}"

    def _remove_category_from_active_preset(self, category_key: str, base_filter: str) -> None:
        """
        Removes category blocks from active preset-zapret2.txt.

        This prevents stale `--filter-*` blocks from remaining after user deletes
        the category definition (which can lead to runtime errors).
        """
        category_key = str(category_key or "").strip()
        if not category_key:
            return

        # Prefer model-based removal (keeps other formatting/metadata stable).
        try:
            from preset_zapret2.preset_manager import PresetManager

            pm = PresetManager()
            preset = pm.get_active_preset()
            if preset and preset.remove_category(category_key):
                pm.sync_preset_to_active_file(preset)
                return
        except Exception:
            pass

        # Fallback: remove blocks by matching tokens against the base_filter we still have.
        try:
            from preset_zapret2.preset_storage import get_active_preset_path
            from preset_zapret2.txt_preset_parser import generate_preset_file, parse_preset_file

            preset_path = get_active_preset_path()
            if not preset_path.exists():
                return

            data = parse_preset_file(preset_path)

            # Build token set from the category's base_filter.
            base_tokens_raw = self._normalize_args_line(base_filter).split()
            base_tokens = {self._normalize_filter_token_for_match(t) for t in base_tokens_raw}
            base_tokens.discard("")

            kept = []
            removed_any = False
            for block in data.categories:
                if (block.category or "").strip() == category_key:
                    removed_any = True
                    continue

                block_lines = {self._normalize_filter_token_for_match(l.strip()) for l in (block.args or "").splitlines()}
                block_lines.discard("")
                if base_tokens and base_tokens.issubset(block_lines):
                    removed_any = True
                    continue

                kept.append(block)

            if not removed_any:
                return

            data.categories = kept
            generate_preset_file(data, preset_path, atomic=True)
        except Exception:
            pass

    def _remove_row_widget(self, row: UserCategoryRow) -> None:
        for i in range(self.rows_layout.count() - 1):
            w = self.rows_layout.itemAt(i).widget()
            if w is row:
                item = self.rows_layout.takeAt(i)
                if item.widget():
                    item.widget().deleteLater()
                break
        self._apply_user_filter(self.search_input.text())

    # ============================= Actions =================================

    def _apply_user_filter(self, text: str) -> None:
        q = str(text or "").strip().lower()
        total = 0
        visible = 0

        for i in range(self.rows_layout.count() - 1):
            w = self.rows_layout.itemAt(i).widget()
            if not isinstance(w, UserCategoryRow):
                continue
            total += 1
            if not q:
                w.setVisible(True)
                visible += 1
                continue
            name = (w.name_input.text() or "").strip().lower()
            key = (w.key() or "").strip().lower()
            ok = q in name or q in key
            w.setVisible(ok)
            if ok:
                visible += 1

        text_out = f"{visible}/{total}" if q else f"{total}"
        self.count_label.setText(text_out)
        try:
            self.count_label.setFixedWidth(self.count_label.sizeHint().width())
        except Exception:
            pass

    def _on_add_clicked(self) -> None:
        self._clear_errors()
        name = str(self.add_name.text() or "").strip()
        base = self._normalize_lists_paths_in_base_filter(self.add_base.toPlainText())

        bad_widgets: list[QWidget] = []
        if not name:
            bad_widgets.append(self.add_name)
        if not base:
            bad_widgets.append(self.add_base)
        if bad_widgets:
            self._set_error("Заполните название и base_filter", widgets=bad_widgets)
            return

        ok, err = self._validate_base_filter(base)
        if not ok:
            self._set_error(err, widgets=[self.add_base])
            return

        key = self._next_user_key()
        self._user_categories[key] = {"key": key, "full_name": name, "base_filter": base, "_source": "user"}

        if not self._save_clean_file():
            self._user_categories.pop(key, None)
            return

        row = UserCategoryRow(
            key=key,
            full_name=name,
            base_filter=base,
            on_save=self._on_row_save_requested,
            on_delete=self._on_row_delete_requested,
            parent=self.rows_host,
        )
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)

        self.add_name.setText("")
        self.add_base.setPlainText("")
        self.add_name.setFocus()
        self._apply_user_filter(self.search_input.text())

    def _on_row_save_requested(self, key: str, full_name: str, base_raw: str, row: UserCategoryRow) -> None:
        self._clear_errors()
        name = str(full_name or "").strip()
        base = self._normalize_lists_paths_in_base_filter(base_raw)

        bad: list[QWidget] = []
        if not name:
            bad.append(row.name_input)
        if not base:
            bad.append(row.base_input)
        if bad:
            self._set_error("Заполните название и base_filter", widgets=bad)
            row.set_error(message="Заполните название и base_filter", widgets=bad)
            return

        ok, err = self._validate_base_filter(base)
        if not ok:
            self._set_error(err, widgets=[row.base_input])
            row.set_error(message=err, widgets=[row.base_input])
            return

        self._user_categories[key] = {"key": key, "full_name": name, "base_filter": base, "_source": "user"}
        if not self._save_clean_file():
            return

        row.set_data(full_name=name, base_filter=base, mark_clean=True)

    def _on_row_delete_requested(self, key: str, row: UserCategoryRow) -> None:
        self._clear_errors()
        existing = self._user_categories.get(key) or {}
        # Remove from active preset-zapret2.txt before removing the category definition,
        # so parser/inference can still recognize the block by category key.
        self._remove_category_from_active_preset(key, str(existing.get("base_filter") or ""))

        self._user_categories.pop(key, None)
        if not self._save_clean_file():
            return
        self._remove_row_widget(row)

    def _on_system_selected(self, _row: int) -> None:
        key = self._get_selected_system_key()
        cat = self._system_categories.get(key or "") if key else None
        self._system_details.setPlainText(_format_category_details(cat or {}))

    def _on_copy_system_to_clipboard(self) -> None:
        text = str(self._system_details.toPlainText() or "").strip()
        if not text:
            return
        try:
            QApplication.clipboard().setText(text)
        except Exception:
            pass

    # ============================= Integration ==============================

    def _on_categories_changed(self) -> None:
        # Refresh caches used across the app.
        try:
            from strategy_menu.strategies_registry import reload_categories

            reload_categories()
        except Exception:
            pass
        try:
            from preset_zapret2.catalog import invalidate_categories_cache

            invalidate_categories_cache()
        except Exception:
            pass
        try:
            from preset_zapret2 import invalidate_category_inference_cache

            invalidate_category_inference_cache()
        except Exception:
            pass

        # Best-effort refresh of strategy pages so new categories appear without restart.
        try:
            mw = self.parent_app
            if mw:
                for attr in (
                    "zapret2_strategies_page",
                    "zapret2_orchestra_strategies_page",
                    "zapret1_strategies_page",
                ):
                    page = getattr(mw, attr, None)
                    if page and hasattr(page, "reload_for_mode_change"):
                        try:
                            page.reload_for_mode_change()
                        except Exception:
                            pass
        except Exception:
            pass
