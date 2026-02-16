# ui/pages/editor_page.py
"""Страница редактора стратегий"""

from __future__ import annotations

from typing import Optional

import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)

from .base_page import BasePage, ScrollBlockingPlainTextEdit
from log import log
from ui.sidebar import ActionButton, SettingsCard
from ui.theme import get_theme_tokens


class EditorPage(BasePage):
    """Страница редактора стратегий"""

    strategies_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Пользовательские стартегии", "Здесь Вы можете создать свои пользовательские стратегии для любых протоколов (TCP, UDP, stun) и отредактировать существующие пользовательские стратегий. Стратегии это набор аргументов, Вы можете взять и посмотреть системные стратегии чтобы понять как писать свои.\nТипичный пример стратегии --lua-desync=multidisorder:pos=4:repeats=10:tcp_md5", parent)
        self.current_category = "tcp"
        self.strategies: dict[str, dict] = {}

        self._editing_strategy_id: Optional[str] = None
        self._build_ui()

    # ──────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        tokens = get_theme_tokens()
        # Категория
        self.add_section_title("Категория")

        cat_card = SettingsCard()
        cat_layout = QHBoxLayout()
        cat_layout.setSpacing(12)

        self.category_combo = QComboBox()
        self.category_combo.addItem("TCP (YouTube, Discord, сайты)", "tcp")
        self.category_combo.addItem("UDP (QUIC, игры)", "udp")
        self.category_combo.addItem("HTTP порт 80", "http80")
        self.category_combo.addItem("Discord Voice", "discord_voice")
        self.category_combo.setStyleSheet(
            f"""
            QComboBox {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 6px;
                padding: 8px 12px;
                color: {tokens.fg};
                min-width: 220px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                selection-background-color: {tokens.accent_soft_bg};
                color: {tokens.fg};
            }}
            """
        )
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        cat_layout.addWidget(self.category_combo, 1)

        refresh_btn = ActionButton("Обновить", "fa5s.sync-alt")
        refresh_btn.clicked.connect(self._load_strategies)
        cat_layout.addWidget(refresh_btn)

        cat_card.add_layout(cat_layout)
        self.add_widget(cat_card)

        self.add_spacing(16)

        # Поиск
        search_card = SettingsCard()
        search_layout = QHBoxLayout()

        search_icon = QLabel()
        search_icon.setPixmap(qta.icon("fa5s.search", color=tokens.fg_faint).pixmap(16, 16))
        search_layout.addWidget(search_icon)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск стратегий...")
        self.search_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {tokens.fg};
                font-size: 13px;
            }}
            """
        )
        self.search_edit.textChanged.connect(self._filter_strategies)
        search_layout.addWidget(self.search_edit, 1)

        search_card.add_layout(search_layout)
        self.add_widget(search_card)

        self.add_spacing(16)

        # Таблица стратегий
        self.add_section_title("Стратегии")

        table_card = SettingsCard()
        table_layout = QVBoxLayout()
        table_layout.setSpacing(0)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.strategies_table = QTableWidget(0, 2)
        self.strategies_table.setHorizontalHeaderLabels(["Источник", "Название"])
        self.strategies_table.verticalHeader().setVisible(False)
        self.strategies_table.setAlternatingRowColors(True)
        self.strategies_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.strategies_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.strategies_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.strategies_table.setShowGrid(False)
        self.strategies_table.verticalHeader().setDefaultSectionSize(28)

        header = self.strategies_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.strategies_table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {tokens.accent_soft_bg};
            }}
            QHeaderView::section {{
                background-color: {tokens.surface_bg};
                color: {tokens.fg_muted};
                padding: 8px;
                border: none;
                font-weight: 600;
                font-size: 11px;
            }}
            """
        )

        self.strategies_table.itemSelectionChanged.connect(self._on_strategy_selected)
        self.strategies_table.cellDoubleClicked.connect(self._on_strategy_double_clicked)
        table_layout.addWidget(self.strategies_table)

        table_card.add_layout(table_layout)
        self.add_widget(table_card)

        self.add_spacing(16)

        # Аргументы выбранной стратегии
        self.args_card = SettingsCard()
        args_layout = QVBoxLayout()
        args_layout.setSpacing(10)

        args_header = QHBoxLayout()
        self.args_title_label = QLabel("Аргументы выбранной стратегии")
        self.args_title_label.setStyleSheet(f"color: {tokens.fg}; font-size: 13px; font-weight: 600;")
        args_header.addWidget(self.args_title_label)
        args_header.addStretch()

        self.edit_selected_btn = ActionButton("Редактировать", "fa5s.edit")
        self.edit_selected_btn.setEnabled(False)
        self.edit_selected_btn.clicked.connect(self._begin_edit_selected)
        args_header.addWidget(self.edit_selected_btn)

        self.delete_selected_btn = ActionButton("Удалить", "fa5s.trash-alt")
        self.delete_selected_btn.setEnabled(False)
        self.delete_selected_btn.clicked.connect(self._delete_selected)
        args_header.addWidget(self.delete_selected_btn)

        args_layout.addLayout(args_header)

        self.args_preview = ScrollBlockingPlainTextEdit()
        self.args_preview.setReadOnly(True)
        self.args_preview.setPlaceholderText("Выберите стратегию в таблице выше…")
        self.args_preview.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.divider};
                border-radius: 6px;
                padding: 10px;
                color: {tokens.fg};
                font-family: Consolas, 'Courier New', monospace;
                font-size: 11px;
            }}
            """
        )
        self.args_preview.setMinimumHeight(110)
        args_layout.addWidget(self.args_preview, 1)

        self.args_card.add_layout(args_layout)
        self.add_widget(self.args_card)

        self.add_spacing(16)

        # Форма добавления/редактирования (внизу вкладки)
        self.form_card = SettingsCard()
        form_layout_outer = QVBoxLayout()
        form_layout_outer.setSpacing(12)

        form_header = QHBoxLayout()
        self.form_title_label = QLabel("Новая стратегия")
        self.form_title_label.setStyleSheet(f"color: {tokens.fg}; font-size: 13px; font-weight: 600;")
        form_header.addWidget(self.form_title_label)
        form_header.addStretch()

        self.form_clear_btn = ActionButton("Очистить", "fa5s.eraser")
        self.form_clear_btn.clicked.connect(self._reset_form)
        form_header.addWidget(self.form_clear_btn)

        form_layout_outer.addLayout(form_header)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("уникальный_id (латиница, цифры, _)")
        self.id_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 6px;
                padding: 8px;
                color: {tokens.fg};
            }}
            QLineEdit:focus {{ border: 1px solid {tokens.accent_hex}; }}
            """
        )
        form_layout.addRow("ID:", self.id_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название стратегии")
        self.name_edit.setStyleSheet(self.id_edit.styleSheet())
        form_layout.addRow("Название:", self.name_edit)

        form_layout_outer.addLayout(form_layout)

        args_label = QLabel("Аргументы командной строки:")
        args_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px; font-weight: 600;")
        form_layout_outer.addWidget(args_label)

        self.args_edit = ScrollBlockingPlainTextEdit()
        self.args_edit.setPlaceholderText("Введите аргументы для winws...\nПример: --payload=tls_client_hello")
        self.args_edit.setStyleSheet(self.args_preview.styleSheet())
        self.args_edit.setMinimumHeight(140)
        form_layout_outer.addWidget(self.args_edit, 1)

        hint = QLabel("💡 Пользовательские стратегии содержат только: ID, Название, Аргументы")
        hint.setStyleSheet(f"color: {tokens.fg_faint}; font-size: 11px;")
        hint.setWordWrap(True)
        form_layout_outer.addWidget(hint)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()

        self.form_cancel_btn = ActionButton("Отмена", "fa5s.times")
        self.form_cancel_btn.setEnabled(False)
        self.form_cancel_btn.clicked.connect(self._reset_form)
        buttons_row.addWidget(self.form_cancel_btn)

        self.form_save_btn = ActionButton("Добавить", "fa5s.plus", accent=True)
        self.form_save_btn.clicked.connect(self._save_from_form)
        buttons_row.addWidget(self.form_save_btn)

        form_layout_outer.addLayout(buttons_row)

        self.form_card.add_layout(form_layout_outer)
        self.add_widget(self.form_card)

        self.add_spacing(12)

        # Статус
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {tokens.fg_faint}; font-size: 11px;")
        self.add_widget(self.status_label)

        self._load_strategies()
        self._reset_form()

    # ──────────────────────────────────────────────────────────────
    # Data loading / table
    # ──────────────────────────────────────────────────────────────

    def _on_category_changed(self, _index: int):
        self.current_category = self.category_combo.currentData()
        self._load_strategies()
        self._reset_form()

    def _load_strategies(self):
        try:
            from strategy_menu.strategy_loader import load_category_strategies

            self.strategies = load_category_strategies(self.current_category)
            self._populate_table()
            self.status_label.setText(f"✅ Загружено {len(self.strategies)} стратегий")
        except Exception as e:
            log(f"Ошибка загрузки стратегий: {e}", "ERROR")
            self.strategies = {}
            self._populate_table()
            self.status_label.setText(f"❌ Ошибка: {e}")

    def _populate_table(self):
        self.strategies_table.setRowCount(0)
        search_text = (self.search_edit.text() or "").strip().lower()

        sorted_items = sorted(
            self.strategies.items(),
            key=lambda x: (0 if x[1].get("_source") == "user" else 1, x[1].get("name", "").lower()),
        )

        for strategy_id, data in sorted_items:
            name = data.get("name", strategy_id)
            if search_text and search_text not in name.lower() and search_text not in strategy_id.lower():
                continue

            row = self.strategies_table.rowCount()
            self.strategies_table.insertRow(row)

            source = data.get("_source", "builtin")
            source_icon = "👤" if source == "user" else "📦"

            source_item = QTableWidgetItem(source_icon)
            source_item.setData(Qt.ItemDataRole.UserRole, strategy_id)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, strategy_id)
            name_item.setToolTip(strategy_id)

            if source == "user":
                name_item.setForeground(QColor(get_theme_tokens().accent_hex))

            self.strategies_table.setItem(row, 0, source_item)
            self.strategies_table.setItem(row, 1, name_item)

        self._clear_args_preview()

    def _filter_strategies(self):
        self._populate_table()

    def _get_selected_strategy_id(self) -> Optional[str]:
        selection = self.strategies_table.selectionModel()
        if not selection or not selection.hasSelection():
            return None

        row = self.strategies_table.currentRow()
        if row < 0:
            return None

        item = self.strategies_table.item(row, 1) or self.strategies_table.item(row, 0)
        if not item:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _on_strategy_selected(self):
        strategy_id = self._get_selected_strategy_id()
        if not strategy_id:
            self._clear_args_preview()
            return

        data = self.strategies.get(strategy_id, {})
        name = data.get("name", strategy_id)
        args = data.get("args", "") or ""

        source = data.get("_source", "builtin")
        self.edit_selected_btn.setEnabled(source == "user")
        self.delete_selected_btn.setEnabled(source == "user")

        self.args_title_label.setText(f"Аргументы: {name}")
        self.args_preview.setPlainText(args)

    def _clear_args_preview(self):
        self.args_title_label.setText("Аргументы выбранной стратегии")
        self.args_preview.setPlainText("")
        self.edit_selected_btn.setEnabled(False)
        self.delete_selected_btn.setEnabled(False)

    # ──────────────────────────────────────────────────────────────
    # Add/Edit
    # ──────────────────────────────────────────────────────────────

    def _on_strategy_double_clicked(self, _row: int, _column: int):
        self._begin_edit_selected()

    def _begin_edit_selected(self):
        strategy_id = self._get_selected_strategy_id()
        if not strategy_id:
            return

        data = self.strategies.get(strategy_id, {})
        if data.get("_source") != "user":
            QMessageBox.information(
                self.window(),
                "Информация",
                "Встроенные стратегии нельзя редактировать.\nСоздайте пользовательскую стратегию снизу.",
            )
            return

        self._editing_strategy_id = strategy_id
        self.form_title_label.setText("Редактирование стратегии")
        self.form_save_btn.setText("Сохранить")
        self.form_cancel_btn.setEnabled(True)

        self.id_edit.setText(strategy_id)
        self.id_edit.setEnabled(False)
        self.name_edit.setText(data.get("name", strategy_id))
        self.args_edit.setPlainText(data.get("args", "") or "")

        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        self.name_edit.setFocus()

    def _reset_form(self):
        self._editing_strategy_id = None
        self.form_title_label.setText("Новая стратегия")
        self.form_save_btn.setText("Добавить")
        self.form_cancel_btn.setEnabled(False)
        self.id_edit.setEnabled(True)
        self.id_edit.setText("")
        self.name_edit.setText("")
        self.args_edit.setPlainText("")
        self.id_edit.setFocus()

    def _save_from_form(self):
        strategy_id = (self.id_edit.text() or "").strip()
        name = (self.name_edit.text() or "").strip()
        args = (self.args_edit.toPlainText() or "").strip()

        if self._editing_strategy_id:
            strategy_id = self._editing_strategy_id

        if not strategy_id:
            QMessageBox.warning(self.window(), "Ошибка", "Введите ID стратегии")
            return

        if not all(c.isalnum() or c == "_" for c in strategy_id):
            QMessageBox.warning(self.window(), "Ошибка", "ID может содержать только латиницу, цифры и _")
            return

        if not name:
            QMessageBox.warning(self.window(), "Ошибка", "Введите название")
            return

        payload = {
            "id": strategy_id,
            "name": name,
            "args": args,
        }

        try:
            from strategy_menu.strategy_loader import save_user_strategy

            success, error = save_user_strategy(self.current_category, payload)
            if not success:
                QMessageBox.warning(self.window(), "Ошибка", f"Не удалось сохранить: {error}")
                return

            self._load_strategies()
            self._clear_cache()
            self.strategies_changed.emit()
            self._reset_form()
        except Exception as e:
            log(f"Ошибка сохранения: {e}", "ERROR")
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось сохранить: {e}")

    # ──────────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────────

    def _delete_selected(self):
        strategy_id = self._get_selected_strategy_id()
        if not strategy_id:
            return

        data = self.strategies.get(strategy_id, {})
        if data.get("_source") != "user":
            return

        reply = QMessageBox.question(
            self.window(),
            "Удаление",
            f"Удалить стратегию '{data.get('name', strategy_id)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from strategy_menu.strategy_loader import delete_user_strategy

            success, error = delete_user_strategy(self.current_category, strategy_id)
            if not success:
                QMessageBox.warning(self.window(), "Ошибка", f"Не удалось удалить: {error}")
                return

            self._load_strategies()
            self._clear_cache()
            self.strategies_changed.emit()

            if self._editing_strategy_id == strategy_id:
                self._reset_form()
        except Exception as e:
            log(f"Ошибка удаления: {e}", "ERROR")
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось удалить: {e}")

    def _clear_cache(self):
        try:
            from strategy_menu.strategies_registry import _strategies_cache, _imported_types

            if self.current_category in _strategies_cache:
                del _strategies_cache[self.current_category]
            if self.current_category in _imported_types:
                _imported_types.discard(self.current_category)
        except Exception as e:
            log(f"Ошибка очистки кэша: {e}", "WARNING")
