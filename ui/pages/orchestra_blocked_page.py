# ui/pages/orchestra_blocked_page.py
"""
Страница управления заблокированными стратегиями оркестратора (чёрный список).
Каждая блокировка отображается в виде ряда с редактируемым номером стратегии.
Изменения автоматически сохраняются в реестр.
"""
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QPushButton, QLineEdit, QSpinBox, QFrame, QMessageBox, QApplication,
    QComboBox
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from ui.widgets.line_edit_icons import set_line_edit_clear_button_icon
from ui.theme import get_theme_tokens
from log import log
from orchestra.blocked_strategies_manager import ASKEY_ALL


class BlockedDomainRow(QFrame):
    """Виджет-ряд для одной заблокированной стратегии с редактируемым номером"""

    def __init__(self, hostname: str, strategy: int, askey: str, is_default: bool = False, parent=None):
        super().__init__(parent)
        self.hostname = hostname
        self.original_strategy = strategy  # Сохраняем оригинальную стратегию для изменений
        self.askey = askey
        self.is_default = is_default

        self._tokens = get_theme_tokens()
        self._current_qss = ""
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False

        self._lock_icon_label = None
        self._domain_label = None
        self._proto_label = None
        self._default_strat_label = None
        self._add_btn = None
        self._delete_btn = None

        self._setup_ui(hostname, strategy, askey, is_default)

    def _setup_ui(self, hostname: str, strategy: int, askey: str, is_default: bool):
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Иконка замка для дефолтных
        if is_default:
            lock_icon = QLabel()
            self._lock_icon_label = lock_icon
            lock_icon.setToolTip("Системная блокировка (нельзя изменить)")
            lock_icon.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(lock_icon)

        # Домен
        domain_label = QLabel(hostname)
        self._domain_label = domain_label
        layout.addWidget(domain_label, 1)

        # Протокол
        proto_label = QLabel(f"[{askey.upper()}]")
        self._proto_label = proto_label
        proto_label.setFixedWidth(60)
        layout.addWidget(proto_label)

        if is_default:
            # Для системных - только текст стратегии
            strat_label = QLabel(f"#{strategy}")
            self._default_strat_label = strat_label
            strat_label.setFixedWidth(50)
            layout.addWidget(strat_label)
        else:
            # Для пользовательских - редактируемый SpinBox
            self.strat_spin = QSpinBox()
            self.strat_spin.setRange(1, 999)
            self.strat_spin.setValue(strategy)
            self.strat_spin.setFixedWidth(70)
            self.strat_spin.valueChanged.connect(self._on_strategy_changed)
            layout.addWidget(self.strat_spin)

            # Кнопка добавления ещё одной блокировки для этого домена
            add_btn = QPushButton()
            self._add_btn = add_btn
            add_btn.setIconSize(QSize(14, 14))
            add_btn.setFixedSize(24, 24)
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.setToolTip("Добавить ещё одну заблокированную стратегию для этого домена")
            add_btn.setStyleSheet("""
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
            add_btn.clicked.connect(self._on_add_clicked)
            layout.addWidget(add_btn)

            # Кнопка удаления (разблокировать)
            delete_btn = QPushButton()
            self._delete_btn = delete_btn
            delete_btn.setIconSize(QSize(16, 16))
            delete_btn.setFixedSize(28, 28)
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setToolTip("Разблокировать")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(76, 175, 80, 0.2);
                }
                QPushButton:pressed {
                    background-color: rgba(76, 175, 80, 0.3);
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
                    BlockedDomainRow {{
                        background-color: {tokens.surface_bg_disabled};
                        border: 1px solid {tokens.surface_border_disabled};
                        border-radius: 6px;
                    }}
                """
            else:
                qss = f"""
                    BlockedDomainRow {{
                        background-color: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 6px;
                    }}
                    BlockedDomainRow:hover {{
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
            if self._proto_label is not None:
                proto_color = tokens.fg_faint if self.is_default else tokens.fg_muted
                self._proto_label.setStyleSheet(
                    f"color: {proto_color}; font-size: 11px; border: none; background: transparent;"
                )
            if self._default_strat_label is not None:
                self._default_strat_label.setStyleSheet(
                    f"color: {tokens.fg_muted}; font-size: 13px; border: none; background: transparent;"
                )

            if (not self.is_default) and hasattr(self, "strat_spin") and self.strat_spin is not None:
                self.strat_spin.setStyleSheet(
                    f"""
                    QSpinBox {{
                        background-color: {tokens.surface_bg_hover};
                        color: #ff6b6b;
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 13px;
                        font-weight: 600;
                    }}
                    QSpinBox:hover {{
                        background-color: {tokens.surface_bg_pressed};
                        border: 1px solid rgba(255, 107, 107, 0.30);
                    }}
                    QSpinBox:focus {{
                        border: 1px solid #ff6b6b;
                    }}
                    QSpinBox::up-button, QSpinBox::down-button {{
                        width: 0px;
                        border: none;
                    }}
                    """
                )

            if self._add_btn is not None:
                self._add_btn.setIcon(qta.icon("mdi.plus", color=tokens.fg))
            if self._delete_btn is not None:
                self._delete_btn.setIcon(qta.icon("mdi.close-circle-outline", color=tokens.fg))
        finally:
            self._applying_theme_styles = False

    def _on_strategy_changed(self, new_value: int):
        """При изменении номера стратегии - уведомляем родителя для автосохранения"""
        parent = self.parent()
        while parent and not isinstance(parent, OrchestraBlockedPage):
            parent = parent.parent()
        if parent:
            parent._on_row_strategy_changed(self.hostname, self.original_strategy, new_value, self.askey)
            self.original_strategy = new_value  # Обновляем для следующих изменений

    def _on_add_clicked(self):
        """При клике на + - заполняем форму для добавления новой блокировки этого домена"""
        parent = self.parent()
        while parent and not isinstance(parent, OrchestraBlockedPage):
            parent = parent.parent()
        if parent:
            parent._prefill_domain(self.hostname)

    def _on_delete_clicked(self):
        """При клике на удаление - уведомляем родителя"""
        parent = self.parent()
        while parent and not isinstance(parent, OrchestraBlockedPage):
            parent = parent.parent()
        if parent:
            parent._on_row_delete_requested(self.hostname, self.original_strategy, self.askey)


class OrchestraBlockedPage(BasePage):
    """Страница управления заблокированными стратегиями (чёрный список)"""

    def __init__(self, parent=None):
        super().__init__(
            "Заблокированные стратегии",
            "Системные блокировки (strategy=1 для заблокированных РКН сайтов) + пользовательский чёрный список. Оркестратор не будет их использовать.",
            parent
        )
        self.setObjectName("orchestraBlockedPage")
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._hint_label = None
        # Инициализируем пустые данные (будут загружены при первом showEvent)
        self._direct_blocked_by_askey = {askey: {} for askey in ASKEY_ALL}
        self._initial_load_done = False
        self._setup_ui()

        self._apply_theme()

    def _setup_ui(self):
        # === Карточка добавления ===
        add_card = SettingsCard("Заблокировать стратегию вручную")
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

        # Домен
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com")
        # Styled in _apply_theme()
        add_layout.addWidget(self.domain_input, 1)

        # Протокол (askey)
        self.proto_combo = QComboBox()
        self.proto_combo.addItems([askey.upper() for askey in ASKEY_ALL])
        self.proto_combo.setFixedWidth(90)
        # Styled in _apply_theme()
        add_layout.addWidget(self.proto_combo)

        # Стратегия
        self.strat_spin = QSpinBox()
        self.strat_spin.setRange(1, 999)
        self.strat_spin.setValue(1)
        self.strat_spin.setFixedWidth(70)
        # Styled in _apply_theme()
        add_layout.addWidget(self.strat_spin)

        # Кнопка добавления
        self.block_btn = QPushButton()
        # Icon styled in _apply_theme()
        self.block_btn.setIconSize(QSize(18, 18))
        self.block_btn.setFixedSize(36, 36)
        self.block_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.block_btn.setToolTip("Заблокировать стратегию")
        self.block_btn.clicked.connect(self._block_strategy)
        self.block_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 107, 107, 0.2);
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 107, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 107, 107, 0.4);
            }
        """)
        add_layout.addWidget(self.block_btn)

        add_card.add_layout(add_layout)
        self.layout.addWidget(add_card)

        # === Карточка списка ===
        list_card = SettingsCard("Чёрный список")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        # Кнопка и счётчик сверху
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

        # Кнопка обновления списка из реестра
        self.refresh_btn = QPushButton("Обновить")
        # Icon styled in _apply_theme()
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._reload_from_registry)
        # Styled in _apply_theme()
        top_row.addWidget(self.refresh_btn)

        self.unblock_all_btn = QPushButton("Очистить пользовательские")
        # Icon styled in _apply_theme()
        self.unblock_all_btn.setIconSize(QSize(16, 16))
        self.unblock_all_btn.setFixedHeight(32)
        self.unblock_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unblock_all_btn.setToolTip("Удалить все пользовательские блокировки (системные останутся)")
        self.unblock_all_btn.clicked.connect(self._unblock_all)
        # Styled in _apply_theme()
        top_row.addWidget(self.unblock_all_btn)
        top_row.addStretch()

        list_layout.addLayout(top_row)

        # Счётчик на отдельной строке (чтобы влезал в таб)
        self.count_label = QLabel()
        list_layout.addWidget(self.count_label)

        # Подсказка
        hint_label = QLabel("Измените номер стратегии и она автоматически сохранится • Системные блокировки неизменяемы")
        self._hint_label = hint_label
        list_layout.addWidget(hint_label)

        # Контейнер для рядов (без скролла - страница сама прокручивается)
        self.rows_container = QWidget()
        self.rows_container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 8, 0, 0)
        self.rows_layout.setSpacing(4)
        list_layout.addWidget(self.rows_container)

        # Храним ссылки на ряды для быстрого доступа
        self._blocked_rows: list[BlockedDomainRow] = []

        list_card.add_layout(list_layout)
        self.layout.addWidget(list_card)

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
            popup_bg = "rgba(246, 248, 252, 0.98)" if tokens.is_light else "rgba(45, 45, 48, 0.96)"

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
                        border: 1px solid rgba(255, 107, 107, 0.30);
                    }}
                    QLineEdit:focus {{
                        border: 1px solid #ff6b6b;
                        background-color: {tokens.surface_bg_hover};
                    }}
                    QLineEdit::placeholder {{
                        color: {tokens.fg_faint};
                    }}
                    """
                )

            if hasattr(self, "proto_combo") and self.proto_combo is not None:
                selection_fg = "rgba(0, 0, 0, 0.90)" if tokens.is_light else "rgba(245, 245, 245, 0.92)"
                self.proto_combo.setStyleSheet(
                    f"""
                    QComboBox {{
                        background-color: {tokens.surface_bg};
                        color: {tokens.fg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 8px 12px;
                    }}
                    QComboBox:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border: 1px solid rgba(255, 107, 107, 0.30);
                    }}
                    QComboBox:focus {{
                        border: 1px solid #ff6b6b;
                    }}
                    QComboBox::drop-down {{ border: none; }}
                    QComboBox QAbstractItemView {{
                        background-color: {popup_bg};
                        color: {tokens.fg};
                        border: 1px solid {tokens.surface_border};
                        selection-background-color: rgba(255, 107, 107, 0.25);
                        selection-color: {selection_fg};
                    }}
                    """
                )

            if hasattr(self, "strat_spin") and self.strat_spin is not None:
                self.strat_spin.setStyleSheet(
                    f"""
                    QSpinBox {{
                        background-color: {tokens.surface_bg};
                        color: {tokens.fg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 8px 12px;
                    }}
                    QSpinBox:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border: 1px solid rgba(255, 107, 107, 0.30);
                    }}
                    QSpinBox:focus {{
                        border: 1px solid #ff6b6b;
                    }}
                    QSpinBox::up-button, QSpinBox::down-button {{
                        width: 0px;
                        border: none;
                    }}
                    """
                )

            if hasattr(self, "block_btn") and self.block_btn is not None:
                self.block_btn.setIcon(qta.icon("mdi.plus", color=tokens.fg))

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

            for btn_attr, icon_name in (("refresh_btn", "mdi.refresh"), ("unblock_all_btn", "mdi.delete-sweep")):
                btn = getattr(self, btn_attr, None)
                if btn is None:
                    continue
                try:
                    btn.setIcon(qta.icon(icon_name, color=tokens.fg))
                    btn.setStyleSheet(
                        f"""
                        QPushButton {{
                            background-color: {tokens.surface_bg};
                            border: 1px solid {tokens.surface_border};
                            border-radius: 4px;
                            color: {tokens.fg};
                            padding: 0 16px;
                            font-size: 12px;
                            font-weight: 600;
                            font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
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
                except Exception:
                    pass

            if hasattr(self, "count_label") and self.count_label is not None:
                self.count_label.setStyleSheet(
                    f"color: {tokens.fg_faint}; font-size: 11px;"
                )
            if self._hint_label is not None:
                self._hint_label.setStyleSheet(
                    f"color: {tokens.fg_faint}; font-size: 10px; font-style: italic;"
                )

            # Section headers inside the list.
            try:
                if hasattr(self, "rows_layout") and self.rows_layout is not None:
                    for i in range(self.rows_layout.count()):
                        item = self.rows_layout.itemAt(i)
                        w = item.widget() if item else None
                        if not isinstance(w, QLabel):
                            continue
                        section = w.property("blockedSection")
                        if section == "user":
                            w.setStyleSheet("color: #ff6b6b; font-size: 11px; font-weight: 600; padding: 4px 0;")
                        elif section == "default":
                            w.setStyleSheet(
                                f"color: {tokens.fg_faint}; font-size: 11px; font-weight: 600; padding: 4px 0;"
                            )
            except Exception:
                pass

            try:
                for row in list(getattr(self, "_blocked_rows", [])):
                    if hasattr(row, "refresh_theme"):
                        row.refresh_theme()
            except Exception:
                pass
        finally:
            self._applying_theme_styles = False

    def showEvent(self, event):
        """При показе страницы загружаем данные один раз (без авто-обновления)"""
        super().showEvent(event)
        # Загружаем данные только при первом показе
        if not self._initial_load_done:
            self._initial_load_done = True
            self._reload_from_registry()

    def _get_runner(self):
        """Получает orchestra_runner из главного окна"""
        app = self.window()
        if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
            return app.orchestra_runner
        return None

    def _refresh_data(self):
        """Обновляет все данные на странице"""
        self._refresh_blocked_list()

    def _reload_from_registry(self):
        """Перезагружает данные из реестра и обновляет список"""
        # Визуальный фидбек (без processEvents — избегаем реентрантность)
        old_text = self.refresh_btn.text()
        self.refresh_btn.setText("Загрузка...")
        self.refresh_btn.setEnabled(False)

        def _do_reload():
            try:
                runner = self._get_runner()
                if runner and hasattr(runner, 'blocked_manager'):
                    runner.blocked_manager.load()
                    log("Список заблокированных перезагружен из реестра (runner)", "INFO")
                else:
                    self._load_directly_from_registry()
                    log("Список заблокированных перезагружен из реестра (direct)", "INFO")
                self._refresh_data()
            finally:
                self.refresh_btn.setText(old_text)
                self.refresh_btn.setEnabled(True)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, _do_reload)

    def _load_directly_from_registry(self):
        """Загружает данные напрямую из реестра (без активного runner)"""
        from orchestra.blocked_strategies_manager import BlockedStrategiesManager
        # Создаём временный менеджер для загрузки данных
        temp_manager = BlockedStrategiesManager()
        temp_manager.load()
        # Сохраняем данные для отображения
        self._direct_blocked_by_askey = {askey: dict(temp_manager.blocked_by_askey[askey]) for askey in ASKEY_ALL}
        # Логируем количество загруженных записей
        total = sum(len(strategies) for askey_data in temp_manager.blocked_by_askey.values() for strategies in askey_data.values())
        log(f"Загружено напрямую из реестра: {total} заблокированных стратегий", "INFO")

    def _refresh_blocked_list(self):
        """Обновляет список заблокированных стратегий"""
        # Очищаем старые ряды
        self._blocked_rows.clear()
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        runner = self._get_runner()

        # Источник данных: runner или напрямую загруженные из реестра
        if runner:
            blocked_data = runner.blocked_manager.blocked_by_askey
            blocked_manager = runner.blocked_manager
        elif hasattr(self, '_direct_blocked_by_askey'):
            blocked_data = self._direct_blocked_by_askey
            blocked_manager = None
        else:
            # Нет данных - попробуем загрузить
            self._load_directly_from_registry()
            blocked_data = getattr(self, '_direct_blocked_by_askey', {askey: {} for askey in ASKEY_ALL})
            blocked_manager = None

        # Собираем все блокировки с флагом is_default по всем askey
        all_blocked = []
        for askey in ASKEY_ALL:
            for hostname, strategies in blocked_data.get(askey, {}).items():
                for strategy in strategies:
                    if blocked_manager:
                        is_default = blocked_manager.is_default_blocked(hostname, strategy)
                    else:
                        # Без менеджера - проверяем только strategy=1 для TLS
                        from orchestra.blocked_strategies_manager import is_default_blocked_pass_domain
                        is_default = (strategy == 1 and askey == "tls" and is_default_blocked_pass_domain(hostname))
                    all_blocked.append((hostname, strategy, askey, is_default))

        # Сортируем: сначала пользовательские, потом дефолтные, внутри групп по алфавиту
        all_blocked.sort(key=lambda x: (x[3], x[0].lower(), x[2], x[1]))

        # Добавляем разделитель если есть оба типа
        user_items = [x for x in all_blocked if not x[3]]
        default_items = [x for x in all_blocked if x[3]]

        if user_items:
            user_header = QLabel(f"Пользовательские ({len(user_items)})")
            user_header.setProperty("blockedSection", "user")
            self.rows_layout.addWidget(user_header)

            for hostname, strategy, askey, is_default in user_items:
                row = BlockedDomainRow(hostname, strategy, askey, is_default=False)
                self.rows_layout.addWidget(row)
                self._blocked_rows.append(row)

        if default_items:
            if user_items:
                # Разделитель
                spacer = QWidget()
                spacer.setFixedHeight(12)
                spacer.setStyleSheet("background: transparent;")
                self.rows_layout.addWidget(spacer)

            default_header = QLabel(f"Системные ({len(default_items)}) - заблокированные РКН сайты")
            default_header.setProperty("blockedSection", "default")
            self.rows_layout.addWidget(default_header)

            for hostname, strategy, askey, is_default in default_items:
                row = BlockedDomainRow(hostname, strategy, askey, is_default=True)
                self.rows_layout.addWidget(row)
                self._blocked_rows.append(row)

        self._update_count()
        self._apply_filter()

        self._apply_theme()

    def _filter_list(self, text: str):
        """Фильтрует список по введённому тексту"""
        self._apply_filter()

    def _apply_filter(self):
        """Применяет текущий фильтр к рядам"""
        search = self.search_input.text().lower().strip()
        for row in self._blocked_rows:
            hostname = row.hostname.lower()
            row.setVisible(search in hostname if search else True)

    def _on_row_strategy_changed(self, hostname: str, old_strategy: int, new_strategy: int, askey: str):
        """Автосохранение при изменении стратегии в SpinBox"""
        runner = self._get_runner()
        if runner and hasattr(runner, 'blocked_manager'):
            # Удаляем старую блокировку и добавляем новую
            runner.blocked_manager.unblock(hostname, old_strategy, askey)
            runner.blocked_manager.block(hostname, new_strategy, askey)
            log(f"Изменена блокировка: {hostname} [{askey.upper()}] #{old_strategy} -> #{new_strategy}", "INFO")
        else:
            log(f"Не удалось изменить блокировку: оркестратор не запущен", "WARNING")

    def _on_row_delete_requested(self, hostname: str, strategy: int, askey: str):
        """Разблокирование при нажатии кнопки удаления"""
        runner = self._get_runner()
        if not runner:
            return

        success = runner.blocked_manager.unblock(hostname, strategy, askey)
        if success:
            log(f"Разблокирована стратегия #{strategy} для {hostname} [{askey.upper()}]", "INFO")
            # Перезапускаем оркестратор чтобы применить изменения
            if runner.is_running():
                QMessageBox.information(
                    self,
                    "Перезапуск оркестратора",
                    f"Стратегия #{strategy} разблокирована для {hostname}.\n\nОркестратор будет перезапущен для применения изменений."
                )
                runner.restart()
        self._refresh_data()

    def _prefill_domain(self, hostname: str):
        """Заполняет форму добавления указанным доменом и фокусируется на SpinBox"""
        self.domain_input.setText(hostname)
        self.strat_spin.setFocus()
        self.strat_spin.selectAll()

    def _update_count(self):
        """Обновляет счётчик"""
        runner = self._get_runner()

        # Источник данных
        if runner:
            blocked_data = runner.blocked_manager.blocked_by_askey
            blocked_manager = runner.blocked_manager
        elif hasattr(self, '_direct_blocked_by_askey'):
            blocked_data = self._direct_blocked_by_askey
            blocked_manager = None
        else:
            self.count_label.setText("Нажмите 'Обновить' для загрузки данных")
            return

        user_count = 0
        default_count = 0
        for askey in ASKEY_ALL:
            for hostname, strategies in blocked_data.get(askey, {}).items():
                for strategy in strategies:
                    if blocked_manager:
                        is_default = blocked_manager.is_default_blocked(hostname, strategy)
                    else:
                        from orchestra.blocked_strategies_manager import is_default_blocked_pass_domain
                        is_default = (strategy == 1 and askey == "tls" and is_default_blocked_pass_domain(hostname))
                    if is_default:
                        default_count += 1
                    else:
                        user_count += 1
        total = user_count + default_count
        self.count_label.setText(f"Всего: {total} ({user_count} пользовательских + {default_count} системных)")

    def _block_strategy(self):
        """Блокирует стратегию"""
        runner = self._get_runner()
        if not runner:
            return

        domain = self.domain_input.text().strip().lower()
        if not domain:
            return

        strategy = self.strat_spin.value()
        askey = self.proto_combo.currentText().lower()

        # Очищаем поле после добавления
        self.domain_input.clear()

        runner.blocked_manager.block(domain, strategy, askey, user_block=True)
        log(f"Заблокирована стратегия #{strategy} для {domain} [{askey.upper()}]", "INFO")
        self._refresh_data()

        # Перезапускаем оркестратор чтобы применить изменения
        if runner.is_running():
            QMessageBox.information(
                self,
                "Перезапуск оркестратора",
                f"Стратегия #{strategy} заблокирована для {domain}.\n\nОркестратор будет перезапущен для применения изменений."
            )
            runner.restart()

    def _unblock_all(self):
        """Очищает пользовательский чёрный список (системные блокировки остаются)"""
        runner = self._get_runner()
        if not runner:
            return

        # Считаем только пользовательские блокировки по всем askey
        user_count = 0
        for askey in ASKEY_ALL:
            for hostname, strategies in runner.blocked_manager.blocked_by_askey.get(askey, {}).items():
                for strategy in strategies:
                    if not runner.blocked_manager.is_default_blocked(hostname, strategy):
                        user_count += 1

        if user_count == 0:
            QMessageBox.information(
                self,
                "Информация",
                "Нет пользовательских блокировок для удаления.\n\nСистемные блокировки (для заблокированных РКН сайтов) не удаляются.",
                QMessageBox.StandardButton.Ok
            )
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Очистить пользовательский чёрный список ({user_count} записей)?\n\nСистемные блокировки останутся.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            runner.blocked_manager.clear()
            log(f"Очищен пользовательский чёрный список ({user_count} записей)", "INFO")
            self._refresh_data()
            # Перезапускаем оркестратор чтобы применить изменения
            if runner.is_running():
                QMessageBox.information(
                    self,
                    "Перезапуск оркестратора",
                    "Чёрный список очищен.\n\nОркестратор будет перезапущен для применения изменений."
                )
                runner.restart()
