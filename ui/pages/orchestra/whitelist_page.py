# ui/pages/orchestra/whitelist_page.py
"""
Страница управления белым списком оркестратора (whitelist)
Домены из этого списка НЕ обрабатываются оркестратором.
"""
from PyQt6.QtCore import Qt, QSize, QEvent
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QWidget, QLineEdit, QFrame, QPushButton
)
import qtawesome as qta

try:
    from qfluentwidgets import (
        LineEdit,
        PushButton,
        TransparentToolButton,
        CardWidget,
        StrongBodyLabel,
        BodyLabel,
        MessageBox,
        InfoBar,
        CaptionLabel,
    )
    _HAS_FLUENT = True
except ImportError:
    LineEdit = QLineEdit
    PushButton = QPushButton
    TransparentToolButton = QPushButton
    CardWidget = QFrame
    StrongBodyLabel = QLabel
    BodyLabel = QLabel
    MessageBox = None
    InfoBar = None
    CaptionLabel = QLabel
    _HAS_FLUENT = False

from ..base_page import BasePage
from ui.compat_widgets import set_tooltip
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
            set_tooltip(lock_icon, "Системный домен (нельзя удалить)")
            layout.addWidget(lock_icon)

        # Домен
        domain_label = BodyLabel(domain)
        if is_default:
            domain_label.setEnabled(False)
        self._domain_label = domain_label
        layout.addWidget(domain_label, 1)

        # Кнопка удаления (только для пользовательских)
        if not is_default:
            delete_btn = TransparentToolButton(self)
            self._delete_btn = delete_btn
            delete_btn.setIconSize(QSize(16, 16))
            delete_btn.setFixedSize(28, 28)
            set_tooltip(delete_btn, "Удалить из белого списка")
            delete_btn.clicked.connect(self._on_delete_clicked)
            layout.addWidget(delete_btn)

        self._apply_theme()

    def changeEvent(self, event) -> None:
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            self._apply_theme()
        super().changeEvent(event)

    def refresh_theme(self) -> None:
        self._tokens = get_theme_tokens()
        self._apply_theme()

    def _apply_theme(self) -> None:
        tokens = self._tokens or get_theme_tokens("Темная синяя")

        if self.is_default:
            qss = f"""
                WhitelistDomainRow {{
                    background: transparent;
                    border: 1px solid {tokens.surface_border_disabled};
                    border-radius: 6px;
                }}
            """
        else:
            qss = f"""
                WhitelistDomainRow {{
                    background: transparent;
                    border: 1px solid {tokens.surface_border};
                    border-radius: 6px;
                }}
                WhitelistDomainRow:hover {{
                    background: {tokens.surface_bg};
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

        if self._delete_btn is not None:
            self._delete_btn.setIcon(qta.icon("mdi.close-circle-outline", color=tokens.fg))

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

        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(lambda _: self._apply_theme())
        qconfig.themeColorChanged.connect(lambda _: self._apply_theme())

        self._setup_ui()

        self._apply_theme()

    def _create_card(self, title: str):
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        title_label = StrongBodyLabel(title, card) if _HAS_FLUENT else QLabel(title)
        if not _HAS_FLUENT:
            title_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        card_layout.addWidget(title_label)

        return card, card_layout

    def _setup_ui(self):
        # === Предупреждение о рестарте ===
        self.restart_warning = CaptionLabel(
            "⚠️ Изменения применятся после перезапуска оркестратора"
        )
        self.restart_warning.hide()
        self.layout.addWidget(self.restart_warning)

        # === Карточка добавления ===
        add_card, add_card_layout = self._create_card("Добавить домен")
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

        # Поле ввода
        self.domain_input = LineEdit()
        self.domain_input.setPlaceholderText("example.com")
        self.domain_input.returnPressed.connect(self._add_domain)
        add_layout.addWidget(self.domain_input, 1)

        # Кнопка добавления
        self.add_btn = TransparentToolButton(self)
        # Icon styled in _apply_theme()
        self.add_btn.setIconSize(QSize(18, 18))
        self.add_btn.setFixedSize(36, 36)
        set_tooltip(self.add_btn, "Добавить в белый список")
        self.add_btn.clicked.connect(self._add_domain)
        add_layout.addWidget(self.add_btn)

        add_card_layout.addLayout(add_layout)
        self.layout.addWidget(add_card)

        # === Карточка списка доменов ===
        domains_card, domains_layout = self._create_card("Белый список доменов")
        domains_layout.setSpacing(8)

        # Строка с поиском и кнопками
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Поиск
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("Поиск по доменам...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_list)
        top_row.addWidget(self.search_input)

        # Кнопка очистки пользовательских
        self.clear_user_btn = PushButton("Очистить пользовательские")
        self.clear_user_btn.setFixedHeight(32)
        set_tooltip(self.clear_user_btn, "Удалить все пользовательские домены (системные останутся)")
        self.clear_user_btn.clicked.connect(self._clear_user_domains)
        top_row.addWidget(self.clear_user_btn)
        top_row.addStretch()

        domains_layout.addLayout(top_row)

        # Счётчик
        self.count_label = CaptionLabel()
        domains_layout.addWidget(self.count_label)

        # Контейнер для рядов (без скролла - страница сама прокручивается)
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 8, 0, 0)
        self.rows_layout.setSpacing(4)
        domains_layout.addWidget(self.rows_container)

        # Храним ссылки на ряды для быстрого доступа
        self._domain_rows: list[WhitelistDomainRow] = []

        self.layout.addWidget(domains_card, 1)

    def _apply_theme(self) -> None:
        tokens = get_theme_tokens()

        if hasattr(self, "add_btn") and self.add_btn is not None:
            self.add_btn.setIcon(qta.icon("mdi.plus", color=tokens.fg))

        if hasattr(self, "clear_user_btn") and self.clear_user_btn is not None:
            self.clear_user_btn.setIcon(qta.icon("mdi.delete-sweep", color=tokens.fg))

        if hasattr(self, "restart_warning") and self.restart_warning is not None:
            self.restart_warning.setStyleSheet(
                f"""
                QLabel {{
                    background: transparent;
                    border: 1px solid {tokens.surface_border};
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: {tokens.fg_muted};
                    font-size: 12px;
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
            InfoBar.error(title="Ошибка", content="Не удалось инициализировать оркестратор", parent=self.window())
            return

        if runner.add_to_whitelist(domain):
            self.domain_input.clear()
            self._refresh_data()
            self._show_restart_warning()
            log(f"Добавлен в белый список: {domain}", "INFO")
        else:
            InfoBar.info(title="Информация", content=f"Домен {domain} уже в списке", parent=self.window())

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
            InfoBar.info(
                title="Информация",
                content="Нет пользовательских доменов для удаления. Системные домены не удаляются.",
                parent=self.window(),
            )
            return

        box = MessageBox(
            "Подтверждение",
            f"Удалить все пользовательские домены ({len(user_domains)})?\n\nСистемные домены останутся.",
            self.window(),
        )
        if box.exec():
            for domain in user_domains:
                runner.remove_from_whitelist(domain)
            log(f"Очищены все пользовательские домены из белого списка ({len(user_domains)})", "INFO")
            self._refresh_data()
            self._show_restart_warning()
