# ui/pages/orchestra_whitelist_page.py
"""
Страница управления белым списком оркестратора (whitelist)
Домены из этого списка НЕ обрабатываются оркестратором.
"""
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget,
    QLineEdit, QFrame, QMessageBox
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from ui.widgets.line_edit_icons import set_line_edit_clear_button_icon
from log import log


class WhitelistDomainRow(QFrame):
    """Виджет-ряд для одного домена в белом списке"""

    def __init__(self, domain: str, is_default: bool = False, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.is_default = is_default
        self._setup_ui(domain, is_default)

    def _setup_ui(self, domain: str, is_default: bool):
        self.setFixedHeight(40)

        if is_default:
            # Системные домены - тёмный стиль, без hover
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.04);
                    border-radius: 6px;
                }
            """)
        else:
            # Пользовательские - интерактивные
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 6px;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Иконка замка для системных
        if is_default:
            lock_icon = QLabel()
            lock_icon.setPixmap(qta.icon("mdi.lock", color="rgba(255,255,255,0.4)").pixmap(14, 14))
            lock_icon.setToolTip("Системный домен (нельзя удалить)")
            lock_icon.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(lock_icon)

        # Домен
        domain_label = QLabel(domain)
        if is_default:
            domain_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 13px; border: none; background: transparent;")
        else:
            domain_label.setStyleSheet("color: white; font-size: 13px; border: none; background: transparent;")
        layout.addWidget(domain_label, 1)

        # Кнопка удаления (только для пользовательских)
        if not is_default:
            delete_btn = QPushButton()
            delete_btn.setIcon(qta.icon("mdi.close-circle-outline", color="white"))
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
        self._runner_cache = None  # Кэш для runner когда оркестратор не запущен
        self._all_whitelist_data = []  # Кэш данных для фильтрации
        self._setup_ui()

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
        self.domain_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 8px 12px;
            }
            QLineEdit:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QLineEdit:focus {
                border: 1px solid #60cdff;
            }
        """)
        add_layout.addWidget(self.domain_input, 1)

        # Кнопка добавления (зелёная иконка +)
        self.add_btn = QPushButton()
        self.add_btn.setIcon(qta.icon("mdi.plus", color="white"))
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
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 200px;
            }
            QLineEdit:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QLineEdit:focus {
                border: 1px solid #60cdff;
            }
        """)
        top_row.addWidget(self.search_input)

        # Кнопка очистки пользовательских
        self.clear_user_btn = QPushButton("Очистить пользовательские")
        self.clear_user_btn.setIcon(qta.icon("mdi.delete-sweep", color="white"))
        self.clear_user_btn.setIconSize(QSize(16, 16))
        self.clear_user_btn.setFixedHeight(32)
        self.clear_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_user_btn.setToolTip("Удалить все пользовательские домены (системные останутся)")
        self.clear_user_btn.clicked.connect(self._clear_user_domains)
        self.clear_user_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.20);
            }
        """)
        top_row.addWidget(self.clear_user_btn)
        top_row.addStretch()

        domains_layout.addLayout(top_row)

        # Счётчик
        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
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
            user_header.setStyleSheet("color: #60cdff; font-size: 11px; font-weight: 600; padding: 4px 0;")
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
            system_header.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px; font-weight: 600; padding: 4px 0;")
            self.rows_layout.addWidget(system_header)

            for domain in system_domains:
                row = WhitelistDomainRow(domain, is_default=True)
                self.rows_layout.addWidget(row)
                self._domain_rows.append(row)

        self.count_label.setText(f"Всего: {len(whitelist)} ({system_count} системных + {user_count} пользовательских)")
        self._apply_filter()

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
