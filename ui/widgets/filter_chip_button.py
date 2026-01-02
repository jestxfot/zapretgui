# ui/widgets/filter_chip_button.py
"""
Chip-кнопки для фильтрации стратегий в стиле Windows 11 Fluent Design.
Поддерживает множественный выбор (не exclusive).
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class FilterChipButton(QPushButton):
    """
    Chip-кнопка с checkable состоянием в стиле Windows 11.

    Стили:
    - Неактивная: rgba(255,255,255,0.06), border rgba(255,255,255,0.08)
    - Активная: rgba(96,205,255,0.15), border rgba(96,205,255,0.4), цвет #60cdff
    - Hover: rgba(255,255,255,0.1)
    """

    def __init__(self, text: str, filter_key: str, parent=None):
        super().__init__(text, parent)
        self._filter_key = filter_key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 9))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._apply_style()

    @property
    def filter_key(self) -> str:
        return self._filter_key

    def _apply_style(self):
        """Применяет стили Windows 11 Fluent Design"""
        self.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                color: rgba(255, 255, 255, 0.7);
                padding: 4px 12px;
                min-height: 24px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:checked {
                background: rgba(96, 205, 255, 0.15);
                border: 1px solid rgba(96, 205, 255, 0.4);
                color: #60cdff;
            }
            QPushButton:checked:hover {
                background: rgba(96, 205, 255, 0.2);
                border: 1px solid rgba(96, 205, 255, 0.5);
            }
            QPushButton:pressed {
                background: rgba(96, 205, 255, 0.25);
            }
        """)


class FilterButtonGroup(QWidget):
    """
    Группа chip-кнопок для фильтрации стратегий.

    Множественный выбор (не exclusive):
    - "Все" снимает остальные фильтры
    - Выбор других фильтров снимает "Все"
    - Можно комбинировать TCP + Discord и т.д.

    Signals:
        filters_changed(set): Эмитит set активных filter_key
    """

    filters_changed = pyqtSignal(set)

    # Конфигурация фильтров
    FILTERS_CONFIG = [
        ("all", "Все"),
        ("tcp", "TCP"),
        ("udp", "UDP"),
        ("discord", "Discord"),
        ("voice", "Voice"),
        ("games", "Games"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = {}  # {filter_key: FilterChipButton}
        self._build_ui()

    def _build_ui(self):
        """Создает UI с chip-кнопками"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(6)

        for filter_key, label in self.FILTERS_CONFIG:
            btn = FilterChipButton(label, filter_key, self)
            btn.clicked.connect(self._on_button_clicked)
            self._buttons[filter_key] = btn
            layout.addWidget(btn)

            # По умолчанию "Все" выбрано
            if filter_key == "all":
                btn.setChecked(True)

        layout.addStretch()

    def _on_button_clicked(self):
        """Обработчик клика по кнопке фильтра"""
        sender = self.sender()
        if not isinstance(sender, FilterChipButton):
            return

        clicked_key = sender.filter_key
        is_checked = sender.isChecked()

        if clicked_key == "all":
            # Клик на "Все" - снимаем остальные
            if is_checked:
                for key, btn in self._buttons.items():
                    if key != "all":
                        btn.setChecked(False)
            else:
                # Нельзя снять "Все" если нет других выбранных
                if not self._has_other_selected():
                    sender.setChecked(True)
        else:
            # Клик на другой фильтр
            if is_checked:
                # Снимаем "Все" при выборе конкретного фильтра
                self._buttons["all"].setChecked(False)
            else:
                # Если сняли последний фильтр - включаем "Все"
                if not self._has_other_selected():
                    self._buttons["all"].setChecked(True)

        # Эмитим изменения
        self.filters_changed.emit(self.get_active_filters())

    def _has_other_selected(self) -> bool:
        """Проверяет, выбран ли хотя бы один фильтр кроме 'all'"""
        for key, btn in self._buttons.items():
            if key != "all" and btn.isChecked():
                return True
        return False

    def get_active_filters(self) -> set:
        """
        Возвращает set активных filter_key.

        Returns:
            set: {"all"} или {"tcp", "discord"} и т.д.
        """
        active = set()
        for key, btn in self._buttons.items():
            if btn.isChecked():
                active.add(key)
        return active

    def set_active_filters(self, filters: set):
        """
        Устанавливает активные фильтры.

        Args:
            filters: set с filter_key для активации
        """
        # Блокируем сигналы при программной установке
        self.blockSignals(True)

        for key, btn in self._buttons.items():
            btn.setChecked(key in filters)

        # Если ничего не выбрано - выбираем "Все"
        if not filters or not self._has_other_selected():
            self._buttons["all"].setChecked(True)
            for key, btn in self._buttons.items():
                if key != "all":
                    btn.setChecked(False)

        self.blockSignals(False)

    def reset(self):
        """Сбрасывает фильтры к состоянию 'Все'"""
        self.set_active_filters({"all"})
        self.filters_changed.emit({"all"})
