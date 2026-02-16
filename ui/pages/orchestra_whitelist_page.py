# ui/pages/orchestra_whitelist_page.py
"""
Страница управления белым списком оркестратора (whitelist)
Домены из этого списка НЕ обрабатываются оркестратором.
"""
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget,
    QLineEdit, QFrame, QMessageBox
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from ui.widgets.line_edit_icons import set_line_edit_clear_button_icon
from ui.theme import get_theme_tokens
from log import log


class WhitelistDomainRow(QFrame):
    """Виджет-ряд для одного домена в белом списке"""

    def __init__(self, domain: str, is_default: bool = False, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.is_default = is_default

        self._tokens = get_theme_tokens()
        self._current_qss = ""
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False

        self._lock_icon_label = None
        self._domain_label = None
        self._delete_btn = None

        self._setup_ui(domain, is_default)

    def _setup_ui(self, domain: str, is_default: bool):
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Иконка замка для системных
        if is_default:
            lock_icon = QLabel()
            self._lock_icon_label = lock_icon
            lock_icon.setToolTip("Системный домен (нельзя удалить)")
            lock_icon.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(lock_icon)

        # Домен
        domain_label = QLabel(domain)
        self._domain_label = domain_label
        layout.addWidget(domain_label, 1)

        # Кнопка удаления (только для пользовательских)
        if not is_default:
            delete_btn = QPushButton()
            self._delete_btn = delete_btn
            delete_btn.setIconSize(QSize(16, 16))
            delete_btn.setFixedSize(28, 28)
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setToolTip("Удалить из белого списка")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 107, 107, 0.2);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 107, 107, 0.3);
                }
            """)
            delete_btn.clicked.connect(self._on_delete_clicked)
            layout.addWidget(delete_btn)

        self._apply_theme()

    def refresh_theme(self) -> None:
        self._tokens = get_theme_tokens()
        self._apply_theme()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self.refresh_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = self._tokens or get_theme_tokens("Темная синяя")

            if self.is_default:
                qss = f"""
                    WhitelistDomainRow {{
                        background-color: {tokens.surface_bg_disabled};
                        border: 1px solid {tokens.surface_border_disabled};
                        border-radius: 6px;
                    }}
                """
            else:
                qss = f"""
                    WhitelistDomainRow {{
                        background-color: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 6px;
                    }}
                    WhitelistDomainRow:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border: 1px solid {tokens.surface_border_hover};
                    }}
                """

            if qss != self._current_qss:
                self._current_qss = qss
                self.setStyleSheet(qss)

            if self._lock_icon_label is not None:
                self._lock_icon_label.setPixmap(
                    qta.icon("mdi.lock", color=tokens.fg_faint).pixmap(14, 14)
                )

            if self._domain_label is not None:
                domain_color = tokens.fg_muted if self.is_default else tokens.fg
                self._domain_label.setStyleSheet(
                    f"color: {domain_color}; font-size: 13px; border: none; background: transparent;"
                )

            if self._delete_btn is not None:
                self._delete_btn.setIcon(qta.icon("mdi.close-circle-outline", color=tokens.fg))
        finally:
            self._applying_theme_styles = False

    def _on_delete_clicked(self):
        """При клике на удаление - уведомляем родителя"""
        parent = self.parent()
        while parent and not isinstance(parent, OrchestraWhitelistPage):
            parent = parent.parent()
        if parent:
            parent._on_row_delete_requested(self.domain)


class OrchestraWhitelistPage(BasePage):
    """Страница управления белым списком оркестратора"""

    def __init__(self, parent=None):
        super().__init__(
            "Белый список",
            "Домены, которые НЕ обрабатываются оркестратором. Эти сайты работают без DPI bypass.",
            parent
        )
        self.setObjectName("orchestraWhitelistPage")
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._runner_cache = None  # Кэш для runner когда оркестратор не запущен
        self._all_whitelist_data = []  # Кэш данных для фильтрации
        self._setup_ui()

        self._apply_theme()

    def _setup_ui(self):
        # === Предупреждение о рестарте ===
        self.restart_warning = QLabel(
            "⚠️ Изменения применятся после перезапуска оркестратора"
        )
        self.restart_warning.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 193, 7, 0.15);
                border: 1px solid rgba(255, 193, 7, 0.3);
                border-radius: 6px;
                padding: 10px 14px;
                color: #ffc107;
                font-size: 12px;
            }
        """)
        self.restart_warning.hide()
        self.layout.addWidget(self.restart_warning)

        # === Карточка добавления ===
        add_card = SettingsCard("Добавить домен")
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

        # Поле ввода
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com")
        self.domain_input.returnPressed.connect(self._add_domain)
        # Styled in _apply_theme()
        add_layout.addWidget(self.domain_input, 1)

        # Кнопка добавления (зелёная иконка +)
        self.add_btn = QPushButton()
        # Icon styled in _apply_theme()
        self.add_btn.setIconSize(QSize(18, 18))
        self.add_btn.setFixedSize(36, 36)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setToolTip("Добавить в белый список")
        self.add_btn.clicked.connect(self._add_domain)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(76, 175, 80, 0.2);
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(76, 175, 80, 0.4);
            }
        """)
        add_layout.addWidget(self.add_btn)

        add_card.add_layout(add_layout)
        self.layout.addWidget(add_card)

        # === Карточка списка доменов ===
        domains_card = SettingsCard("Белый список доменов")
        domains_layout = QVBoxLayout()
        domains_layout.setSpacing(8)

        # Строка с поиском и кнопками
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по доменам...")
        self.search_input.setClearButtonEnabled(True)
        set_line_edit_clear_button_icon(self.search_input)
        self.search_input.textChanged.connect(self._filter_list)
        # Styled in _apply_theme()
        top_row.addWidget(self.search_input)

        # Кнопка очистки пользовательских
        self.clear_user_btn = QPushButton("Очистить пользовательские")
        # Icon styled in _apply_theme()
        self.clear_user_btn.setIconSize(QSize(16, 16))
        self.clear_user_btn.setFixedHeight(32)
        self.clear_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_user_btn.setToolTip("Удалить все пользовательские домены (системные останутся)")
        self.clear_user_btn.clicked.connect(self._clear_user_domains)
        # Styled in _apply_theme()
        top_row.addWidget(self.clear_user_btn)
        top_row.addStretch()

        domains_layout.addLayout(top_row)

        # Счётчик
        self.count_label = QLabel()
        domains_layout.addWidget(self.count_label)

        # Контейнер для рядов (без скролла - страница сама прокручивается)
        self.rows_container = QWidget()
        self.rows_container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 8, 0, 0)
        self.rows_layout.setSpacing(4)
        domains_layout.addWidget(self.rows_container)

        # Храним ссылки на ряды для быстрого доступа
        self._domain_rows: list[WhitelistDomainRow] = []

        domains_card.add_layout(domains_layout)
        self.layout.addWidget(domains_card, 1)

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()

            if hasattr(self, "domain_input") and self.domain_input is not None:
                self.domain_input.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background-color: {tokens.surface_bg};
                        color: {tokens.fg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 8px 12px;
                    }}
                    QLineEdit:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border: 1px solid rgba({tokens.accent_rgb_str}, 0.30);
                    }}
                    QLineEdit:focus {{
                        border: 1px solid {tokens.accent_hex};
                    }}
                    QLineEdit::placeholder {{
                        color: {tokens.fg_faint};
                    }}
                    """
                )

            if hasattr(self, "add_btn") and self.add_btn is not None:
                self.add_btn.setIcon(qta.icon("mdi.plus", color=tokens.fg))

            if hasattr(self, "search_input") and self.search_input is not None:
                set_line_edit_clear_button_icon(self.search_input)
                self.search_input.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background-color: {tokens.surface_bg};
                        color: {tokens.fg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 6px 12px;
                        min-width: 200px;
                    }}
                    QLineEdit:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border: 1px solid rgba({tokens.accent_rgb_str}, 0.30);
                    }}
                    QLineEdit:focus {{
                        border: 1px solid {tokens.accent_hex};
                    }}
                    QLineEdit::placeholder {{
                        color: {tokens.fg_faint};
                    }}
                    """
                )

            if hasattr(self, "clear_user_btn") and self.clear_user_btn is not None:
                self.clear_user_btn.setIcon(qta.icon("mdi.delete-sweep", color=tokens.fg))
                self.clear_user_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        color: {tokens.fg};
                        padding: 0 16px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border-color: {tokens.surface_border_hover};
                    }}
                    QPushButton:pressed {{
                        background-color: {tokens.surface_bg_pressed};
                    }}
                    """
                )

            if hasattr(self, "count_label") and self.count_label is not None:
                self.count_label.setStyleSheet(
                    f"color: {tokens.fg_faint}; font-size: 11px;"
                )

            # Section headers inside the list.
            try:
                if hasattr(self, "rows_layout") and self.rows_layout is not None:
                    for i in range(self.rows_layout.count()):
                        item = self.rows_layout.itemAt(i)
                        w = item.widget() if item else None
                        if not isinstance(w, QLabel):
                            continue
                        section = w.property("whitelistSection")
                        if section == "user":
                            w.setStyleSheet(
                                f"color: {tokens.accent_hex}; font-size: 11px; font-weight: 600; padding: 4px 0;"
                            )
                        elif section == "system":
                            w.setStyleSheet(
                                f"color: {tokens.fg_faint}; font-size: 11px; font-weight: 600; padding: 4px 0;"
                            )
            except Exception:
                pass

            # Refresh row widgets.
            try:
                for row in list(getattr(self, "_domain_rows", [])):
                    if hasattr(row, "refresh_theme"):
                        row.refresh_theme()
            except Exception:
                pass
        finally:
            self._applying_theme_styles = False

    def showEvent(self, event):
        """При показе страницы обновляем данные"""
        super().showEvent(event)
        self._refresh_data()

    def _get_runner(self):
        """Получает orchestra_runner из главного окна или создаёт временный"""
        # Сначала пробуем из главного окна
        app = self.window()
        if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
            return app.orchestra_runner
        
        # Если нет - создаём/используем кэшированный для работы с whitelist
        if not self._runner_cache:
            try:
                from orchestra.orchestra_runner import OrchestraRunner
                self._runner_cache = OrchestraRunner()
            except Exception as e:
                log(f"Ошибка создания OrchestraRunner: {e}", "ERROR")
                return None
        return self._runner_cache

    def _is_orchestra_running(self) -> bool:
        """Проверяет, запущен ли оркестратор"""
        app = self.window()
        if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
            return app.orchestra_runner.is_running()
        return False

    def _refresh_data(self):
        """Обновляет список доменов"""
        # Очищаем старые ряды
        self._domain_rows.clear()
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._all_whitelist_data = []

        runner = self._get_runner()
        if not runner:
            self.count_label.setText("Ошибка инициализации")
            return

        # Получаем полный список с пометками о типе
        whitelist = runner.get_whitelist()

        system_count = 0
        user_count = 0

        # Разделяем на системные и пользовательские
        system_domains = []
        user_domains = []

        for entry in whitelist:
            domain = entry['domain']
            is_default = entry['is_default']
            self._all_whitelist_data.append((domain, is_default))

            if is_default:
                system_domains.append(domain)
                system_count += 1
            else:
                user_domains.append(domain)
                user_count += 1

        # Сортируем
        system_domains.sort()
        user_domains.sort()

        # Добавляем заголовок и ряды для пользовательских (если есть)
        if user_domains:
            user_header = QLabel(f"Пользовательские ({user_count})")
            user_header.setProperty("whitelistSection", "user")
            self.rows_layout.addWidget(user_header)

            for domain in user_domains:
                row = WhitelistDomainRow(domain, is_default=False)
                self.rows_layout.addWidget(row)
                self._domain_rows.append(row)

        # Разделитель между группами
        if user_domains and system_domains:
            spacer = QWidget()
            spacer.setFixedHeight(12)
            spacer.setStyleSheet("background: transparent;")
            self.rows_layout.addWidget(spacer)

        # Добавляем заголовок и ряды для системных (если есть)
        if system_domains:
            system_header = QLabel(f"🔒 Системные ({system_count}) — нельзя удалить")
            system_header.setProperty("whitelistSection", "system")
            self.rows_layout.addWidget(system_header)

            for domain in system_domains:
                row = WhitelistDomainRow(domain, is_default=True)
                self.rows_layout.addWidget(row)
                self._domain_rows.append(row)

        self.count_label.setText(f"Всего: {len(whitelist)} ({system_count} системных + {user_count} пользовательских)")
        self._apply_filter()

        self._apply_theme()

    def _filter_list(self, text: str):
        """Фильтрует список по введённому тексту"""
        self._apply_filter()

    def _apply_filter(self):
        """Применяет текущий фильтр к рядам"""
        search = self.search_input.text().lower().strip()
        for row in self._domain_rows:
            domain = row.domain.lower()
            row.setVisible(search in domain if search else True)

    def _show_restart_warning(self):
        """Показывает предупреждение о необходимости рестарта"""
        if self._is_orchestra_running():
            self.restart_warning.show()

    def _add_domain(self):
        """Добавляет домен в пользовательский whitelist"""
        domain = self.domain_input.text().strip().lower()
        if not domain:
            return

        runner = self._get_runner()
        if not runner:
            QMessageBox.warning(self, "Ошибка", "Не удалось инициализировать оркестратор")
            return

        if runner.add_to_whitelist(domain):
            self.domain_input.clear()
            self._refresh_data()
            self._show_restart_warning()
            log(f"Добавлен в белый список: {domain}", "INFO")
        else:
            QMessageBox.information(self, "Информация", f"Домен {domain} уже в списке")

    def _on_row_delete_requested(self, domain: str):
        """Удаление при нажатии кнопки X в ряду"""
        runner = self._get_runner()
        if not runner:
            return

        if runner.remove_from_whitelist(domain):
            self._refresh_data()
            self._show_restart_warning()
            log(f"Удалён из белого списка: {domain}", "INFO")

    def _clear_user_domains(self):
        """Очищает все пользовательские домены из белого списка"""
        runner = self._get_runner()
        if not runner:
            return

        # Получаем список пользовательских доменов
        whitelist = runner.get_whitelist()
        user_domains = [entry['domain'] for entry in whitelist if not entry['is_default']]

        if not user_domains:
            QMessageBox.information(
                self,
                "Информация",
                "Нет пользовательских доменов для удаления.\n\nСистемные домены не удаляются.",
                QMessageBox.StandardButton.Ok
            )
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить все пользовательские домены ({len(user_domains)})?\n\nСистемные домены останутся.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for domain in user_domains:
                runner.remove_from_whitelist(domain)
            log(f"Очищены все пользовательские домены из белого списка ({len(user_domains)})", "INFO")
            self._refresh_data()
            self._show_restart_warning()
