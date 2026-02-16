# ui/pages/hostlist_page.py
"""Объединенная страница управления hostlist/ipset листами."""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.theme import get_theme_tokens
from log import log


class HostlistPage(BasePage):
    """Единая вкладка 'Листы' (hostlist + ipset)."""

    def __init__(self, parent=None):
        super().__init__("Листы", "Управление hostlist и ipset списками для обхода блокировок", parent)
        self._build_ui()

    def _build_ui(self):
        """Строит UI страницы."""
        tokens = get_theme_tokens()
        intro_card = SettingsCard()
        intro = QLabel(
            "На этой странице собраны оба типа списков:\n"
            "• Hostlist — домены\n"
            "• IPset — IP-адреса и подсети"
        )
        intro.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 13px;")
        intro.setWordWrap(True)
        intro_card.add_widget(intro)
        self.layout.addWidget(intro_card)

        hostlist_card = SettingsCard("Hostlist")
        hostlist_desc = QLabel(
            "Используется для обхода блокировок по доменам."
        )
        hostlist_desc.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        hostlist_card.add_widget(hostlist_desc)
        hostlist_card.add_widget(
            self._build_action_row(
                title="Открыть папку хостлистов",
                icon_name="fa5s.folder-open",
                icon_color=tokens.accent_hex,
                button_text="Открыть",
                button_icon="fa5s.external-link-alt",
                callback=self._open_lists_folder,
            )
        )
        hostlist_card.add_widget(
            self._build_action_row(
                title="Перестроить хостлисты",
                icon_name="fa5s.sync-alt",
                icon_color="#ff9800",
                button_text="Перестроить",
                button_icon="fa5s.sync-alt",
                callback=self._rebuild_hostlists,
                subtitle="Обновляет списки из встроенной базы",
            )
        )
        self.hostlist_info_label = QLabel("Загрузка информации...")
        self.hostlist_info_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        self.hostlist_info_label.setWordWrap(True)
        hostlist_card.add_widget(self.hostlist_info_label)
        self.layout.addWidget(hostlist_card)

        ipset_card = SettingsCard("IPset")
        ipset_desc = QLabel(
            "Используется для обхода блокировок по IP-адресам и подсетям."
        )
        ipset_desc.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        ipset_card.add_widget(ipset_desc)
        ipset_card.add_widget(
            self._build_action_row(
                title="Открыть папку IP-сетов",
                icon_name="fa5s.folder-open",
                icon_color=tokens.accent_hex,
                button_text="Открыть",
                button_icon="fa5s.external-link-alt",
                callback=self._open_lists_folder,
            )
        )
        self.ipset_info_label = QLabel("Загрузка информации...")
        self.ipset_info_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        self.ipset_info_label.setWordWrap(True)
        ipset_card.add_widget(self.ipset_info_label)
        self.layout.addWidget(ipset_card)

        QTimer.singleShot(100, self._load_info)
        self.layout.addStretch()

    def _build_action_row(
        self,
        *,
        title: str,
        icon_name: str,
        icon_color: str,
        button_text: str,
        button_icon: str,
        callback,
        subtitle: str = "",
    ) -> QWidget:
        tokens = get_theme_tokens()
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
        row_layout.addWidget(icon)

        if subtitle:
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)

            title_label = QLabel(title)
            title_label.setStyleSheet(f"color: {tokens.fg}; font-size: 13px;")
            text_layout.addWidget(title_label)

            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(f"color: {tokens.fg_faint}; font-size: 11px;")
            text_layout.addWidget(subtitle_label)

            row_layout.addLayout(text_layout, 1)
        else:
            title_label = QLabel(title)
            title_label.setStyleSheet(f"color: {tokens.fg}; font-size: 13px;")
            row_layout.addWidget(title_label, 1)

        action_btn = ActionButton(button_text, button_icon)
        action_btn.setFixedHeight(32)
        action_btn.clicked.connect(callback)
        row_layout.addWidget(action_btn)

        return row

    @staticmethod
    def _is_ipset_file_name(file_name: str) -> bool:
        lower = (file_name or "").lower()
        return lower.startswith("ipset-") or "ipset" in lower or "subnet" in lower

    @staticmethod
    def _count_lines(folder: str, file_names: list[str], *, max_files: int, skip_comments: bool) -> int:
        import os

        total = 0
        for file_name in file_names[:max_files]:
            try:
                path = os.path.join(folder, file_name)
                with open(path, "r", encoding="utf-8", errors="ignore") as file_obj:
                    if skip_comments:
                        total += sum(1 for line in file_obj if line.strip() and not line.startswith("#"))
                    else:
                        total += sum(1 for _ in file_obj)
            except Exception:
                continue
        return total

    def _open_lists_folder(self):
        """Открывает папку со списками."""
        try:
            from config import LISTS_FOLDER
            import os

            os.startfile(LISTS_FOLDER)
        except Exception as e:
            log(f"Ошибка открытия папки: {e}", "ERROR")
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть папку:\n{e}")

    def _rebuild_hostlists(self):
        """Перестраивает hostlist-файлы из встроенной базы."""
        try:
            from utils.hostlists_manager import startup_hostlists_check

            startup_hostlists_check()
            QMessageBox.information(self.window(), "Готово", "Хостлисты обновлены")
            self._load_info()
        except Exception as e:
            log(f"Ошибка перестроения: {e}", "ERROR")
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось перестроить:\n{e}")

    def _load_info(self):
        """Загружает статистику по hostlist и ipset файлам."""
        try:
            from config import LISTS_FOLDER
            import os

            if not os.path.exists(LISTS_FOLDER):
                self.hostlist_info_label.setText("Папка листов не найдена")
                self.ipset_info_label.setText("Папка листов не найдена")
                return

            txt_files = [f for f in os.listdir(LISTS_FOLDER) if f.endswith(".txt")]
            ipset_files = [f for f in txt_files if self._is_ipset_file_name(f)]
            hostlist_files = [f for f in txt_files if f not in ipset_files]

            hostlist_lines = self._count_lines(
                LISTS_FOLDER,
                hostlist_files,
                max_files=12,
                skip_comments=False,
            )
            ipset_lines = self._count_lines(
                LISTS_FOLDER,
                ipset_files,
                max_files=12,
                skip_comments=True,
            )

            self.hostlist_info_label.setText(
                f"📁 Папка: {LISTS_FOLDER}\n"
                f"📄 Файлов: {len(hostlist_files)}\n"
                f"📝 Примерно строк: {hostlist_lines:,}"
            )
            self.ipset_info_label.setText(
                f"📁 Папка: {LISTS_FOLDER}\n"
                f"📄 IP-файлов: {len(ipset_files)}\n"
                f"🌐 Примерно IP/подсетей: {ipset_lines:,}"
            )
        except Exception as e:
            self.hostlist_info_label.setText(f"Ошибка загрузки информации: {e}")
            self.ipset_info_label.setText(f"Ошибка загрузки информации: {e}")
