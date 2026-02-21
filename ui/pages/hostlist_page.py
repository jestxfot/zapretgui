# ui/pages/hostlist_page.py
"""Объединённая страница «Листы»: обзор hostlist / ipset + редакторы доменов и IP."""

import ipaddress
import os
import re
from typing import Optional
from urllib.parse import urlparse

import qtawesome as qta
from PyQt6.QtCore import QTimer, pyqtSignal

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

try:
    from qfluentwidgets import (
        BodyLabel, CaptionLabel, InfoBar, LineEdit, MessageBox, SegmentedWidget,
        StrongBodyLabel,
    )
    _HAS_FLUENT = True
except ImportError:
    SegmentedWidget = None
    InfoBar = None
    MessageBox = None
    from PyQt6.QtWidgets import QLineEdit as LineEdit  # type: ignore[assignment]
    BodyLabel = QLabel          # type: ignore[assignment,misc]
    CaptionLabel = QLabel       # type: ignore[assignment,misc]
    StrongBodyLabel = QLabel    # type: ignore[assignment,misc]
    _HAS_FLUENT = False

from .base_page import BasePage, ScrollBlockingPlainTextEdit
from .strategies_page_base import ResetActionButton
from ui.compat_widgets import SettingsCard, ActionButton, set_tooltip
from ui.theme import get_theme_tokens
from log import log


class HostlistPage(BasePage):
    """Страница «Листы»: обзор hostlist/ipset + редакторы пользовательских доменов и IP."""

    domains_changed = pyqtSignal()
    ipset_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            "Листы",
            "Управление hostlist и ipset списками для обхода блокировок",
            parent,
        )
        self._ui_built = False
        self._info_loaded_once = False
        self._domains_loaded = False
        self._ips_loaded = False
        self._accent_icon_lbls: list[tuple] = []

        # Autosave timers (created early so textChanged can reference them before panel is shown)
        self._domains_save_timer = QTimer()
        self._domains_save_timer.setSingleShot(True)
        self._domains_save_timer.timeout.connect(self._domains_auto_save)

        self._ips_save_timer = QTimer()
        self._ips_save_timer.setSingleShot(True)
        self._ips_save_timer.timeout.connect(self._ips_auto_save)

        self._excl_loaded = False
        self._excl_save_timer = QTimer()
        self._excl_save_timer.setSingleShot(True)
        self._excl_save_timer.timeout.connect(self._excl_auto_save)

        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(lambda _: self._apply_editor_styles())
        qconfig.themeColorChanged.connect(lambda _: self._apply_editor_styles())

    # ──────────────────────────────────────────────────────────────────────────
    # Qt event overrides
    # ──────────────────────────────────────────────────────────────────────────

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if event.spontaneous():
            return
        if not self._ui_built:
            self._build_ui()
            self._ui_built = True
        if not self._info_loaded_once:
            self._info_loaded_once = True
            QTimer.singleShot(0, self._load_info)


    # ──────────────────────────────────────────────────────────────────────────
    # Main UI builder
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Pivot tab selector
        if SegmentedWidget is not None:
            self.pivot = SegmentedWidget(self)
        else:
            self.pivot = None

        # Stacked panels
        self.stacked = QStackedWidget(self)
        self.stacked.setSizePolicy(
            self.stacked.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Expanding,
        )

        panel_hostlist = self._build_hostlist_panel()       # index 0
        panel_ipset = self._build_ipset_panel()             # index 1
        panel_domains = self._build_domains_panel()         # index 2
        panel_ips = self._build_ips_panel()                 # index 3
        panel_exclusions = self._build_exclusions_panel()   # index 4

        self.stacked.addWidget(panel_hostlist)
        self.stacked.addWidget(panel_ipset)
        self.stacked.addWidget(panel_domains)
        self.stacked.addWidget(panel_ips)
        self.stacked.addWidget(panel_exclusions)

        if self.pivot is not None:
            self.pivot.addItem("hostlist",   "Hostlist",    lambda: self._switch_tab(0))
            self.pivot.addItem("ipset",      "IPset",       lambda: self._switch_tab(1))
            self.pivot.addItem("domains",    "Мои домены",  lambda: self._switch_tab(2))
            self.pivot.addItem("ips",        "Мои IP",      lambda: self._switch_tab(3))
            self.pivot.addItem("exclusions", "Исключения",  lambda: self._switch_tab(4))
            self.pivot.setCurrentItem("hostlist")
            self.pivot.setItemFontSize(13)
            self.layout.addWidget(self.pivot)

        self.layout.addWidget(self.stacked)
        self._switch_tab(0)

    def _switch_tab(self, index: int):
        self.stacked.setCurrentIndex(index)
        if self.pivot is not None:
            keys = ["hostlist", "ipset", "domains", "ips", "exclusions"]
            if 0 <= index < len(keys):
                self.pivot.setCurrentItem(keys[index])
        # Lazy-load editors on first visit
        if index == 2 and not self._domains_loaded:
            self._domains_loaded = True
            QTimer.singleShot(0, self._load_domains)
        elif index == 3 and not self._ips_loaded:
            self._ips_loaded = True
            QTimer.singleShot(0, self._load_ips)
        elif index == 4 and not self._excl_loaded:
            self._excl_loaded = True
            QTimer.singleShot(0, self._load_exclusions)

    # ──────────────────────────────────────────────────────────────────────────
    # Panel builders
    # ──────────────────────────────────────────────────────────────────────────

    def _build_hostlist_panel(self) -> QWidget:
        tokens = get_theme_tokens()
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)

        desc_card = SettingsCard()
        desc = BodyLabel("Используется для обхода блокировок по доменам.")
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        lay.addWidget(desc_card)

        manage_card = SettingsCard("Управление")
        manage_card.add_widget(self._build_action_row(
            title="Открыть папку хостлистов",
            icon_name="fa5s.folder-open",
            button_text="Открыть",
            button_icon="fa5s.external-link-alt",
            callback=self._open_lists_folder,
        ))
        manage_card.add_widget(self._build_action_row(
            title="Перестроить хостлисты",
            icon_name="fa5s.sync-alt",
            button_text="Перестроить",
            button_icon="fa5s.sync-alt",
            callback=self._rebuild_hostlists,
            subtitle="Обновляет списки из встроенной базы",
        ))
        self.hostlist_info_label = CaptionLabel("Загрузка информации...")
        self.hostlist_info_label.setStyleSheet(f"color: {tokens.fg_muted};")
        self.hostlist_info_label.setWordWrap(True)
        manage_card.add_widget(self.hostlist_info_label)
        lay.addWidget(manage_card)

        lay.addStretch()
        return panel

    def _build_ipset_panel(self) -> QWidget:
        tokens = get_theme_tokens()
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)

        desc_card = SettingsCard()
        desc = BodyLabel("Используется для обхода блокировок по IP-адресам и подсетям.")
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        lay.addWidget(desc_card)

        manage_card = SettingsCard("Управление")
        manage_card.add_widget(self._build_action_row(
            title="Открыть папку IP-сетов",
            icon_name="fa5s.folder-open",
            button_text="Открыть",
            button_icon="fa5s.external-link-alt",
            callback=self._open_lists_folder,
        ))
        self.ipset_info_label = CaptionLabel("Загрузка информации...")
        self.ipset_info_label.setStyleSheet(f"color: {tokens.fg_muted};")
        self.ipset_info_label.setWordWrap(True)
        manage_card.add_widget(self.ipset_info_label)
        lay.addWidget(manage_card)

        lay.addStretch()
        return panel

    def _build_domains_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)

        desc_card = SettingsCard()
        desc = BodyLabel(
            "Редактируется файл other.user.txt (только ваши домены). "
            "Системная база хранится в other.base.txt, общий other.txt собирается автоматически. "
            "URL автоматически преобразуются в домены. Изменения сохраняются автоматически. "
            "Поддерживается Ctrl+Z."
        )
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        lay.addWidget(desc_card)

        add_card = SettingsCard("Добавить домен")
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._d_input = LineEdit()
        if hasattr(self._d_input, "setPlaceholderText"):
            self._d_input.setPlaceholderText("Введите домен или URL (например: example.com)")
        if hasattr(self._d_input, "returnPressed"):
            self._d_input.returnPressed.connect(self._domains_add)
        add_row.addWidget(self._d_input, 1)
        self._d_add_btn = ActionButton("Добавить", "fa5s.plus", accent=True)
        self._d_add_btn.setFixedHeight(38)
        self._d_add_btn.clicked.connect(self._domains_add)
        add_row.addWidget(self._d_add_btn)
        add_card.add_layout(add_row)
        lay.addWidget(add_card)

        actions_card = SettingsCard("Действия")
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        open_btn = ActionButton("Открыть файл", "fa5s.external-link-alt")
        open_btn.setFixedHeight(36)
        set_tooltip(open_btn, "Сохраняет изменения и открывает other.user.txt в проводнике")
        open_btn.clicked.connect(self._domains_open_file)
        actions_row.addWidget(open_btn)
        reset_btn = ResetActionButton("Сбросить файл", confirm_text="Подтвердить сброс")
        reset_btn.setFixedHeight(36)
        set_tooltip(reset_btn, "Очищает other.user.txt и пересобирает other.txt из системной базы")
        reset_btn.reset_confirmed.connect(self._domains_reset_file)
        actions_row.addWidget(reset_btn)
        clear_btn = ResetActionButton("Очистить всё", confirm_text="Подтвердить очистку")
        clear_btn.setFixedHeight(36)
        set_tooltip(clear_btn, "Удаляет только пользовательские домены")
        clear_btn.reset_confirmed.connect(self._domains_clear_all)
        actions_row.addWidget(clear_btn)
        actions_row.addStretch()
        actions_card.add_layout(actions_row)
        lay.addWidget(actions_card)

        editor_card = SettingsCard("other.user.txt (редактор)")
        editor_lay = QVBoxLayout()
        editor_lay.setSpacing(8)
        self._d_editor = ScrollBlockingPlainTextEdit()
        self._d_editor.setPlaceholderText(
            "Домены по одному на строку:\nexample.com\nsubdomain.site.org\n\nКомментарии начинаются с #"
        )
        self._d_editor.setMinimumHeight(350)
        self._d_editor.textChanged.connect(self._domains_on_text_changed)
        editor_lay.addWidget(self._d_editor)
        hint = CaptionLabel("💡 Изменения сохраняются автоматически через 500мс")
        editor_lay.addWidget(hint)
        editor_card.add_layout(editor_lay)
        lay.addWidget(editor_card)

        self._d_status = CaptionLabel()
        lay.addWidget(self._d_status)
        lay.addStretch()

        self._apply_editor_styles()
        return panel

    def _build_ips_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)

        desc_card = SettingsCard()
        desc = BodyLabel(
            "Добавляйте свои IP/подсети.\n"
            "• Одиночный IP: 1.2.3.4\n"
            "• Подсеть: 10.0.0.0/8\n"
            "Диапазоны (a-b) не поддерживаются. Изменения сохраняются автоматически. Поддерживается Ctrl+Z."
        )
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        lay.addWidget(desc_card)

        add_card = SettingsCard("Добавить IP/подсеть")
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._i_input = LineEdit()
        if hasattr(self._i_input, "setPlaceholderText"):
            self._i_input.setPlaceholderText("Например: 1.2.3.4 или 10.0.0.0/8")
        if hasattr(self._i_input, "returnPressed"):
            self._i_input.returnPressed.connect(self._ips_add)
        add_row.addWidget(self._i_input, 1)
        self._i_add_btn = ActionButton("Добавить", "fa5s.plus", accent=True)
        self._i_add_btn.setFixedHeight(38)
        self._i_add_btn.clicked.connect(self._ips_add)
        add_row.addWidget(self._i_add_btn)
        add_card.add_layout(add_row)
        lay.addWidget(add_card)

        actions_card = SettingsCard("Действия")
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        open_btn = ActionButton("Открыть файл", "fa5s.external-link-alt")
        open_btn.setFixedHeight(36)
        open_btn.clicked.connect(self._ips_open_file)
        actions_row.addWidget(open_btn)
        clear_btn = ActionButton("Очистить всё", "fa5s.trash-alt")
        clear_btn.setFixedHeight(36)
        clear_btn.clicked.connect(self._ips_clear_all)
        actions_row.addWidget(clear_btn)
        actions_row.addStretch()
        actions_card.add_layout(actions_row)
        lay.addWidget(actions_card)

        editor_card = SettingsCard("Мой IP-список (редактор)")
        editor_lay = QVBoxLayout()
        editor_lay.setSpacing(8)
        self._i_editor = ScrollBlockingPlainTextEdit()
        self._i_editor.setPlaceholderText(
            "IP/подсети по одному на строку:\n192.168.0.1\n10.0.0.0/8\n\nКомментарии начинаются с #"
        )
        self._i_editor.setMinimumHeight(350)
        self._i_editor.textChanged.connect(self._ips_on_text_changed)
        editor_lay.addWidget(self._i_editor)
        hint = CaptionLabel("💡 Изменения сохраняются автоматически через 500мс")
        editor_lay.addWidget(hint)
        self._i_error_label = CaptionLabel()
        self._i_error_label.setWordWrap(True)
        self._i_error_label.hide()
        editor_lay.addWidget(self._i_error_label)
        editor_card.add_layout(editor_lay)
        lay.addWidget(editor_card)

        self._i_status = CaptionLabel()
        lay.addWidget(self._i_status)
        lay.addStretch()

        self._apply_editor_styles()
        return panel

    # ──────────────────────────────────────────────────────────────────────────
    # Shared helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _build_action_row(
        self,
        *,
        title: str,
        icon_name: str,
        button_text: str,
        button_icon: str,
        callback,
        subtitle: str = "",
    ) -> QWidget:
        tokens = get_theme_tokens()
        row = QWidget()
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color=tokens.accent_hex).pixmap(18, 18))
        self._accent_icon_lbls.append((icon_lbl, icon_name))
        row_lay.addWidget(icon_lbl)

        if subtitle:
            text_lay = QVBoxLayout()
            text_lay.setSpacing(2)
            text_lay.addWidget(BodyLabel(title))
            sub = CaptionLabel(subtitle)
            sub.setStyleSheet(f"color: {tokens.fg_faint};")
            text_lay.addWidget(sub)
            row_lay.addLayout(text_lay, 1)
        else:
            row_lay.addWidget(BodyLabel(title), 1)

        btn = ActionButton(button_text, button_icon)
        btn.setFixedHeight(32)
        btn.clicked.connect(callback)
        row_lay.addWidget(btn)
        return row

    def _apply_editor_styles(self):
        tokens = get_theme_tokens()

        if hasattr(self, "_accent_icon_lbls"):
            for lbl, icon_name in self._accent_icon_lbls:
                try:
                    lbl.setPixmap(qta.icon(icon_name, color=tokens.accent_hex).pixmap(18, 18))
                except Exception:
                    pass

        style = (
            f"QPlainTextEdit {{"
            f"  background: {tokens.surface_bg};"
            f"  border: 1px solid {tokens.surface_border};"
            f"  border-radius: 8px;"
            f"  padding: 12px;"
            f"  color: {tokens.fg};"
            f"  font-family: Consolas, 'Courier New', monospace;"
            f"  font-size: 13px;"
            f"}}"
            f"QPlainTextEdit:hover {{"
            f"  background: {tokens.surface_bg_hover};"
            f"  border: 1px solid {tokens.surface_border_hover};"
            f"}}"
            f"QPlainTextEdit:focus {{"
            f"  border: 1px solid {tokens.accent_hex};"
            f"}}"
        )
        if hasattr(self, "_d_editor") and self._d_editor is not None:
            self._d_editor.setStyleSheet(style)
        if hasattr(self, "_i_editor") and self._i_editor is not None:
            self._i_editor.setStyleSheet(style)
        if hasattr(self, "_excl_editor") and self._excl_editor is not None:
            self._excl_editor.setStyleSheet(style)

    # ──────────────────────────────────────────────────────────────────────────
    # Hostlist / IPset folder info
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_ipset_file_name(file_name: str) -> bool:
        lower = (file_name or "").lower()
        return lower.startswith("ipset-") or "ipset" in lower or "subnet" in lower

    @staticmethod
    def _count_lines(folder: str, file_names: list, *, max_files: int, skip_comments: bool) -> int:
        total = 0
        for file_name in file_names[:max_files]:
            try:
                path = os.path.join(folder, file_name)
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    if skip_comments:
                        total += sum(1 for ln in fh if ln.strip() and not ln.startswith("#"))
                    else:
                        total += sum(1 for _ in fh)
            except Exception:
                continue
        return total

    def _open_lists_folder(self):
        try:
            from config import LISTS_FOLDER
            os.startfile(LISTS_FOLDER)
        except Exception as e:
            log(f"Ошибка открытия папки: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть папку:\n{e}", parent=self.window())

    def _rebuild_hostlists(self):
        try:
            from utils.hostlists_manager import startup_hostlists_check
            startup_hostlists_check()
            if InfoBar:
                InfoBar.success(title="Готово", content="Хостлисты обновлены", parent=self.window())
            self._load_info()
        except Exception as e:
            log(f"Ошибка перестроения: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось перестроить:\n{e}", parent=self.window())

    def _load_info(self):
        try:
            from config import LISTS_FOLDER
            if not os.path.exists(LISTS_FOLDER):
                self.hostlist_info_label.setText("Папка листов не найдена")
                self.ipset_info_label.setText("Папка листов не найдена")
                return
            txt_files = [f for f in os.listdir(LISTS_FOLDER) if f.endswith(".txt")]
            ipset_files = [f for f in txt_files if self._is_ipset_file_name(f)]
            hostlist_files = [f for f in txt_files if f not in ipset_files]
            hl_lines = self._count_lines(LISTS_FOLDER, hostlist_files, max_files=12, skip_comments=False)
            ip_lines = self._count_lines(LISTS_FOLDER, ipset_files, max_files=12, skip_comments=True)
            self.hostlist_info_label.setText(
                f"📁 Папка: {LISTS_FOLDER}\n"
                f"📄 Файлов: {len(hostlist_files)}\n"
                f"📝 Примерно строк: {hl_lines:,}"
            )
            self.ipset_info_label.setText(
                f"📁 Папка: {LISTS_FOLDER}\n"
                f"📄 IP-файлов: {len(ipset_files)}\n"
                f"🌐 Примерно IP/подсетей: {ip_lines:,}"
            )
        except Exception as e:
            self.hostlist_info_label.setText(f"Ошибка загрузки информации: {e}")
            self.ipset_info_label.setText(f"Ошибка загрузки информации: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Domains editor logic
    # ──────────────────────────────────────────────────────────────────────────

    def _load_domains(self):
        try:
            from config import OTHER_USER_PATH
            from utils.hostlists_manager import ensure_hostlists_exist
            ensure_hostlists_exist()
            domains: list[str] = []
            if os.path.exists(OTHER_USER_PATH):
                with open(OTHER_USER_PATH, "r", encoding="utf-8") as fh:
                    domains = [ln.strip() for ln in fh if ln.strip()]
            self._d_editor.blockSignals(True)
            self._d_editor.setPlainText("\n".join(domains))
            self._d_editor.blockSignals(False)
            self._domains_update_status()
            log(f"Загружено {len(domains)} строк из other.user.txt", "INFO")
        except Exception as e:
            log(f"Ошибка загрузки доменов: {e}", "ERROR")
            if hasattr(self, "_d_status"):
                self._d_status.setText(f"❌ Ошибка: {e}")

    def _domains_on_text_changed(self):
        self._domains_save_timer.start(500)
        self._domains_update_status()

    def _domains_auto_save(self):
        self._domains_save()
        if hasattr(self, "_d_status"):
            self._d_status.setText(self._d_status.text() + " • ✅ Сохранено")

    def _domains_save(self):
        try:
            from config import OTHER_USER_PATH
            os.makedirs(os.path.dirname(OTHER_USER_PATH), exist_ok=True)
            text = self._d_editor.toPlainText()
            domains: list[str] = []
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    domains.append(line)
                    continue
                domain = self._extract_domain(line)
                if domain and domain not in domains:
                    domains.append(domain)
            with open(OTHER_USER_PATH, "w", encoding="utf-8") as fh:
                fh.write("\n".join(domains) + ("\n" if domains else ""))
            try:
                from utils.hostlists_manager import rebuild_other_files
                rebuild_other_files()
            except Exception:
                pass
            log(f"Сохранено {len(domains)} строк в other.user.txt", "SUCCESS")
            self.domains_changed.emit()
        except Exception as e:
            log(f"Ошибка сохранения доменов: {e}", "ERROR")

    def _domains_update_status(self):
        if not hasattr(self, "_d_status") or not hasattr(self, "_d_editor"):
            return
        text = self._d_editor.toPlainText()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        self._d_status.setText(f"📊 Доменов: {len(lines)}")

    def _domains_add(self):
        text = self._d_input.text().strip() if hasattr(self._d_input, "text") else ""
        if not text:
            return
        domain = self._extract_domain(text)
        if not domain:
            if InfoBar:
                InfoBar.warning(
                    title="Ошибка",
                    content=f"Не удалось распознать домен:\n{text}\n\nВведите корректный домен (например: example.com)",
                    parent=self.window(),
                )
            return
        current = self._d_editor.toPlainText()
        existing = [ln.strip().lower() for ln in current.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        if domain.lower() in existing:
            if InfoBar:
                InfoBar.info(title="Информация", content=f"Домен уже добавлен:\n{domain}", parent=self.window())
            return
        if current and not current.endswith("\n"):
            current += "\n"
        self._d_editor.setPlainText(current + domain)
        if hasattr(self._d_input, "clear"):
            self._d_input.clear()

    def _domains_open_file(self):
        try:
            from config import OTHER_USER_PATH
            import subprocess
            from utils.hostlists_manager import ensure_hostlists_exist
            self._domains_save()
            ensure_hostlists_exist()
            if os.path.exists(OTHER_USER_PATH):
                subprocess.run(["explorer", "/select,", OTHER_USER_PATH])
            else:
                os.makedirs(os.path.dirname(OTHER_USER_PATH), exist_ok=True)
                subprocess.run(["explorer", os.path.dirname(OTHER_USER_PATH)])
        except Exception as e:
            log(f"Ошибка открытия файла: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть:\n{e}", parent=self.window())

    def _domains_reset_file(self):
        try:
            from utils.hostlists_manager import reset_other_file_from_template
            if reset_other_file_from_template():
                self._load_domains()
                if hasattr(self, "_d_status"):
                    self._d_status.setText(self._d_status.text() + " • ✅ Сброшено")
            else:
                if InfoBar:
                    InfoBar.warning(title="Ошибка", content="Не удалось сбросить my hostlist", parent=self.window())
        except Exception as e:
            log(f"Ошибка сброса hostlist: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось сбросить:\n{e}", parent=self.window())

    def _domains_clear_all(self):
        self._d_editor.setPlainText("")
        self._domains_save()

    @staticmethod
    def _extract_domain(text: str) -> Optional[str]:
        text = text.strip()
        marker = ""
        if text.startswith("^"):
            marker = "^"
            text = text[1:].strip()
            if not text:
                return None
        if text.startswith("."):
            text = text[1:]
        if "://" in text or text.startswith("www."):
            if not text.startswith(("http://", "https://")):
                text = "https://" + text
            try:
                parsed = urlparse(text)
                domain = parsed.netloc or parsed.path.split("/")[0]
                if domain.startswith("www."):
                    domain = domain[4:]
                domain = domain.split(":")[0].lower()
                if domain.startswith("."):
                    domain = domain[1:]
                return f"{marker}{domain}" if marker else domain
            except Exception:
                pass
        domain = text.split("/")[0].split(":")[0].lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain.startswith("."):
            domain = domain[1:]
        if re.match(r"^[a-z]{2,10}$", domain):
            return f"{marker}{domain}" if marker else domain
        if "." in domain and len(domain) > 3 and re.match(r"^[a-z0-9][a-z0-9\-\.]*[a-z0-9]$", domain):
            return f"{marker}{domain}" if marker else domain
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # IPs editor logic
    # ──────────────────────────────────────────────────────────────────────────

    def _load_ips(self):
        try:
            from utils.ipsets_manager import MY_IPSET_PATH
            entries: list[str] = []
            if os.path.exists(MY_IPSET_PATH):
                with open(MY_IPSET_PATH, "r", encoding="utf-8") as fh:
                    entries = [ln.strip() for ln in fh if ln.strip()]
            self._i_editor.blockSignals(True)
            self._i_editor.setPlainText("\n".join(entries))
            self._i_editor.blockSignals(False)
            self._ips_update_status()
            log(f"Загружено {len(entries)} строк из my-ipset.txt", "INFO")
        except Exception as e:
            log(f"Ошибка загрузки my-ipset.txt: {e}", "ERROR")
            if hasattr(self, "_i_status"):
                self._i_status.setText(f"❌ Ошибка: {e}")

    def _ips_on_text_changed(self):
        self._ips_save_timer.start(500)
        self._ips_update_status()

    def _ips_auto_save(self):
        self._ips_save()
        if hasattr(self, "_i_status"):
            self._i_status.setText(self._i_status.text() + " • ✅ Сохранено")

    def _ips_save(self):
        try:
            from utils.ipsets_manager import MY_IPSET_PATH
            os.makedirs(os.path.dirname(MY_IPSET_PATH), exist_ok=True)
            text = self._i_editor.toPlainText()
            entries: list[str] = []
            invalid: list[str] = []
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    entries.append(line)
                    continue
                for item in re.split(r"[\s,;]+", line):
                    item = item.strip()
                    if not item:
                        continue
                    norm = self._normalize_ip(item)
                    if norm:
                        if norm not in entries:
                            entries.append(norm)
                    else:
                        invalid.append(item)
            with open(MY_IPSET_PATH, "w", encoding="utf-8") as fh:
                fh.write("\n".join(entries) + ("\n" if entries else ""))
            # Show/hide error label
            if hasattr(self, "_i_error_label"):
                if invalid:
                    self._i_error_label.setText("❌ Неверный формат: " + ", ".join(invalid[:5]))
                    self._i_error_label.show()
                else:
                    self._i_error_label.hide()
            log(f"Сохранено {len(entries)} строк в my-ipset.txt", "SUCCESS")
            self.ipset_changed.emit()
        except Exception as e:
            log(f"Ошибка сохранения my-ipset.txt: {e}", "ERROR")

    def _ips_update_status(self):
        if not hasattr(self, "_i_status") or not hasattr(self, "_i_editor"):
            return
        text = self._i_editor.toPlainText()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        self._i_status.setText(f"📊 Записей: {len(lines)}")

    def _ips_add(self):
        text = self._i_input.text().strip() if hasattr(self._i_input, "text") else ""
        if not text:
            return
        norm = self._normalize_ip(text)
        if not norm:
            if InfoBar:
                InfoBar.warning(
                    title="Ошибка",
                    content="Не удалось распознать IP или подсеть.\nПримеры: 1.2.3.4 или 10.0.0.0/8",
                    parent=self.window(),
                )
            return
        current = self._i_editor.toPlainText()
        existing = [ln.strip().lower() for ln in current.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        if norm.lower() in existing:
            if InfoBar:
                InfoBar.info(title="Информация", content=f"Запись уже есть:\n{norm}", parent=self.window())
            return
        if current and not current.endswith("\n"):
            current += "\n"
        self._i_editor.setPlainText(current + norm)
        if hasattr(self._i_input, "clear"):
            self._i_input.clear()

    def _ips_open_file(self):
        try:
            from utils.ipsets_manager import MY_IPSET_PATH
            import subprocess
            self._ips_save()
            if os.path.exists(MY_IPSET_PATH):
                subprocess.run(["explorer", "/select,", MY_IPSET_PATH])
            else:
                os.makedirs(os.path.dirname(MY_IPSET_PATH), exist_ok=True)
                subprocess.run(["explorer", os.path.dirname(MY_IPSET_PATH)])
        except Exception as e:
            log(f"Ошибка открытия my-ipset.txt: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть:\n{e}", parent=self.window())

    def _ips_clear_all(self):
        text = self._i_editor.toPlainText().strip()
        if not text:
            return
        if MessageBox:
            box = MessageBox("Очистить всё", "Удалить все записи?", self.window())
            if box.exec():
                self._i_editor.clear()
        else:
            self._i_editor.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # Exclusions (netrogat.txt) panel + logic
    # ──────────────────────────────────────────────────────────────────────────

    def _build_exclusions_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)

        desc_card = SettingsCard()
        desc = BodyLabel(
            "Список доменов, которые не следует трогать (netrogat.txt). "
            "Изменения сохраняются автоматически. Поддерживается Ctrl+Z."
        )
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        lay.addWidget(desc_card)

        add_card = SettingsCard("Добавить домен")
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._excl_input = LineEdit()
        if hasattr(self._excl_input, "setPlaceholderText"):
            self._excl_input.setPlaceholderText("Например: example.com, site.com или через пробел")
        if hasattr(self._excl_input, "returnPressed"):
            self._excl_input.returnPressed.connect(self._excl_add)
        add_row.addWidget(self._excl_input, 1)
        self._excl_add_btn = ActionButton("Добавить", "fa5s.plus", accent=True)
        self._excl_add_btn.setFixedHeight(38)
        self._excl_add_btn.clicked.connect(self._excl_add)
        add_row.addWidget(self._excl_add_btn)
        add_card.add_layout(add_row)
        lay.addWidget(add_card)

        actions_card = SettingsCard("Действия")
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        defaults_btn = ActionButton("Добавить недостающие", "fa5s.plus-circle")
        defaults_btn.setFixedHeight(36)
        defaults_btn.clicked.connect(self._excl_add_missing_defaults)
        actions_row.addWidget(defaults_btn)
        open_btn = ActionButton("Открыть файл", "fa5s.external-link-alt")
        open_btn.setFixedHeight(36)
        open_btn.clicked.connect(self._excl_open_file)
        actions_row.addWidget(open_btn)
        clear_btn = ActionButton("Очистить всё", "fa5s.trash-alt")
        clear_btn.setFixedHeight(36)
        clear_btn.clicked.connect(self._excl_clear_all)
        actions_row.addWidget(clear_btn)
        actions_row.addStretch()
        actions_card.add_layout(actions_row)
        lay.addWidget(actions_card)

        editor_card = SettingsCard("netrogat.txt (редактор)")
        editor_lay = QVBoxLayout()
        editor_lay.setSpacing(8)
        self._excl_editor = ScrollBlockingPlainTextEdit()
        self._excl_editor.setPlaceholderText(
            "Домены по одному на строку:\ngosuslugi.ru\nvk.com\n\nКомментарии начинаются с #"
        )
        self._excl_editor.setMinimumHeight(350)
        self._excl_editor.textChanged.connect(self._excl_on_text_changed)
        editor_lay.addWidget(self._excl_editor)
        hint = CaptionLabel("💡 Изменения сохраняются автоматически через 500мс")
        editor_lay.addWidget(hint)
        editor_card.add_layout(editor_lay)
        lay.addWidget(editor_card)

        self._excl_status = CaptionLabel()
        lay.addWidget(self._excl_status)
        lay.addStretch()

        self._apply_editor_styles()
        return panel

    def _load_exclusions(self):
        try:
            from utils.netrogat_manager import load_netrogat
            domains = load_netrogat()
            self._excl_editor.blockSignals(True)
            self._excl_editor.setPlainText("\n".join(domains))
            self._excl_editor.blockSignals(False)
            self._excl_update_status()
            log(f"Загружено {len(domains)} доменов netrogat", "INFO")
        except Exception as e:
            log(f"Ошибка загрузки netrogat: {e}", "ERROR")
            if hasattr(self, "_excl_status"):
                self._excl_status.setText(f"❌ Ошибка: {e}")

    def _excl_on_text_changed(self):
        self._excl_save_timer.start(500)
        self._excl_update_status()

    def _excl_auto_save(self):
        self._excl_save()
        if hasattr(self, "_excl_status"):
            self._excl_status.setText(self._excl_status.text() + " • ✅ Сохранено")

    def _excl_save(self):
        try:
            from utils.netrogat_manager import save_netrogat, _normalize_domain
            from ui.pages.netrogat_page import split_domains
            text = self._excl_editor.toPlainText()
            domains: list[str] = []
            normalized_lines: list[str] = []
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    domains.append(line)
                    normalized_lines.append(line)
                    continue
                for item in split_domains(line):
                    norm = _normalize_domain(item)
                    if norm:
                        if norm not in domains:
                            domains.append(norm)
                            normalized_lines.append(norm)
                    else:
                        normalized_lines.append(item)
            if save_netrogat(domains):
                new_text = "\n".join(normalized_lines)
                if new_text != text:
                    cursor = self._excl_editor.textCursor()
                    pos = cursor.position()
                    self._excl_editor.blockSignals(True)
                    self._excl_editor.setPlainText(new_text)
                    cursor = self._excl_editor.textCursor()
                    cursor.setPosition(min(pos, len(new_text)))
                    self._excl_editor.setTextCursor(cursor)
                    self._excl_editor.blockSignals(False)
        except Exception as e:
            log(f"Ошибка сохранения netrogat: {e}", "ERROR")

    def _excl_update_status(self):
        if not hasattr(self, "_excl_status") or not hasattr(self, "_excl_editor"):
            return
        text = self._excl_editor.toPlainText()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        self._excl_status.setText(f"📊 Доменов: {len(lines)}")

    def _excl_add(self):
        try:
            from utils.netrogat_manager import _normalize_domain
            from ui.pages.netrogat_page import split_domains
        except ImportError:
            return
        raw = self._excl_input.text().strip() if hasattr(self._excl_input, "text") else ""
        if not raw:
            return
        parts = split_domains(raw)
        if not parts:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content="Не удалось распознать домен.", parent=self.window())
            return
        current = self._excl_editor.toPlainText()
        current_domains = [ln.strip().lower() for ln in current.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        added: list[str] = []
        skipped: list[str] = []
        invalid: list[str] = []
        for part in parts:
            if part.startswith("#"):
                continue
            norm = _normalize_domain(part)
            if not norm:
                invalid.append(part)
                continue
            if norm.lower() in current_domains or norm.lower() in [a.lower() for a in added]:
                skipped.append(norm)
                continue
            added.append(norm)
        if not added and not skipped and invalid:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content="Не удалось распознать домены.", parent=self.window())
            return
        if not added and skipped:
            if InfoBar:
                if len(skipped) == 1:
                    InfoBar.info(title="Информация", content=f"Домен уже есть: {skipped[0]}", parent=self.window())
                else:
                    InfoBar.info(title="Информация", content=f"Все домены уже есть ({len(skipped)})", parent=self.window())
            return
        if current and not current.endswith("\n"):
            current += "\n"
        current += "\n".join(added)
        self._excl_editor.setPlainText(current)
        if hasattr(self._excl_input, "clear"):
            self._excl_input.clear()
        if skipped and InfoBar:
            InfoBar.success(
                title="Добавлено",
                content=f"Добавлено доменов. Пропущено уже существующих: {len(skipped)}",
                parent=self.window(),
            )

    def _excl_open_file(self):
        try:
            from config import NETROGAT_PATH
            import subprocess
            self._excl_save()
            if NETROGAT_PATH and os.path.exists(NETROGAT_PATH):
                subprocess.run(["explorer", "/select,", NETROGAT_PATH])
            else:
                from config import LISTS_FOLDER
                subprocess.run(["explorer", LISTS_FOLDER])
        except Exception as e:
            log(f"Ошибка открытия netrogat.txt: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть: {e}", parent=self.window())

    def _excl_clear_all(self):
        text = self._excl_editor.toPlainText().strip()
        if not text:
            return
        if MessageBox:
            box = MessageBox("Очистить всё", "Удалить все домены?", self.window())
            if box.exec():
                self._excl_editor.clear()
        else:
            self._excl_editor.clear()

    def _excl_add_missing_defaults(self):
        try:
            from utils.netrogat_manager import add_missing_defaults, _normalize_domain
        except ImportError:
            return
        text = self._excl_editor.toPlainText()
        current_domains: list[str] = []
        for line in text.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                norm = _normalize_domain(line)
                if norm:
                    current_domains.append(norm)
        new_domains, added = add_missing_defaults(current_domains)
        if added == 0:
            if InfoBar:
                InfoBar.success(title="Готово", content="Все домены по умолчанию уже есть.", parent=self.window())
            return
        self._excl_editor.blockSignals(True)
        self._excl_editor.setPlainText("\n".join(new_domains))
        self._excl_editor.blockSignals(False)
        self._excl_save()
        self._excl_update_status()
        if InfoBar:
            InfoBar.success(title="Готово", content=f"Добавлено доменов: {added}", parent=self.window())

    @staticmethod
    def _normalize_ip(text: str) -> Optional[str]:
        line = text.strip()
        if not line or line.startswith("#"):
            return None
        if "://" in line:
            try:
                parsed = urlparse(line)
                host = parsed.netloc or parsed.path.split("/")[0]
                line = host.split(":")[0]
            except Exception:
                pass
        if "-" in line:
            return None
        if "/" in line:
            try:
                return ipaddress.ip_network(line, strict=False).with_prefixlen
            except Exception:
                return None
        try:
            return str(ipaddress.ip_address(line))
        except Exception:
            return None
