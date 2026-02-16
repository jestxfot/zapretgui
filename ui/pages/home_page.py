# ui/pages/home_page.py
"""Главная страница - обзор состояния системы"""

from PyQt6.QtCore import (
    Qt,
    QSize,
    QTimer,
    QThread,
    pyqtSignal,
    QEasingCurve,
    QPropertyAnimation,
    QParallelAnimationGroup,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QSizePolicy, QProgressBar, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QFont
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, StatusIndicator, ActionButton
from ui.theme import get_theme_tokens, get_card_gradient_qss
from ui.theme_semantic import get_semantic_palette
from log import log


class AutostartCheckWorker(QThread):
    """Быстрая фоновая проверка статуса автозапуска"""
    finished = pyqtSignal(bool)  # True если автозапуск включён
    
    def run(self):
        try:
            result = self._check_autostart()
            self.finished.emit(result)
        except Exception as e:
            log(f"AutostartCheckWorker error: {e}", "WARNING")
            self.finished.emit(False)
    
    def _check_autostart(self) -> bool:
        """Быстрая проверка наличия автозапуска через реестр"""
        try:
            from autostart.registry_check import AutostartRegistryChecker
            return AutostartRegistryChecker.is_autostart_enabled()
        except Exception:
            return False


def _build_progress_style() -> str:
    """Indeterminate progress bar style (theme-aware)."""
    tokens = get_theme_tokens()
    accent = tokens.accent_hex
    return f"""
    QProgressBar {{
        background-color: {tokens.surface_bg};
        border: none;
        border-radius: 2px;
        height: 4px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 transparent,
            stop:0.3 {accent},
            stop:0.5 {accent},
            stop:0.7 {accent},
            stop:1 transparent
        );
        border-radius: 2px;
    }}
    """


class StatusCard(QFrame):
    """Большая карточка статуса на главной странице"""

    clicked = pyqtSignal()  # Сигнал клика по карточке

    def __init__(self, icon_name: str, title: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._use_fluent_icon = False
        self._applying_theme_styles = False
        self.setObjectName("statusCard")
        self.setMinimumHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)  # Курсор "рука" при наведении
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        
        # Верхняя строка: иконка + заголовок
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)
        
        # Иконка (объёмная с градиентом)
        self.icon_label = QLabel()
        try:
            from ui.fluent_icons import fluent_pixmap
            self.icon_label.setPixmap(fluent_pixmap(icon_name, 28))
            self._use_fluent_icon = True
        except:
            self.icon_label.setPixmap(qta.icon(icon_name, color=get_theme_tokens().accent_hex).pixmap(28, 28))
        self.icon_label.setFixedSize(32, 32)
        top_layout.addWidget(self.icon_label)
        
        # Заголовок
        title_label = QLabel(title)
        try:
            title_label.setProperty("tone", "muted")
        except Exception:
            pass
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
            }
        """)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # Значение (большой текст)
        self.value_label = QLabel("—")
        try:
            self.value_label.setProperty("tone", "primary")
        except Exception:
            pass
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.value_label)
        
        # Дополнительная информация
        self.info_label = QLabel("")
        try:
            self.info_label.setProperty("tone", "muted")
        except Exception:
            pass
        self.info_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
            }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            card_bg = get_card_gradient_qss(tokens.theme_name)
            card_bg_hover = get_card_gradient_qss(tokens.theme_name, hover=True)
            self.setStyleSheet(
                f"""
                QFrame#statusCard {{
                    background: {card_bg};
                    border: 1px solid {tokens.surface_border};
                    border-radius: 8px;
                }}
                QFrame#statusCard:hover {{
                    background: {card_bg_hover};
                    border: 1px solid {tokens.surface_border_hover};
                }}
                """
            )

            if not bool(self._use_fluent_icon):
                try:
                    self.icon_label.setPixmap(
                        qta.icon(self._icon_name, color=tokens.accent_hex).pixmap(28, 28)
                    )
                except Exception:
                    pass
        finally:
            self._applying_theme_styles = False

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                if self._applying_theme_styles:
                    return super().changeEvent(event)
                self._apply_theme()
        except Exception:
            pass
        super().changeEvent(event)
        
    def set_value(self, value: str, info: str = ""):
        """Устанавливает текстовое значение"""
        # Скрываем иконки, показываем текст
        if hasattr(self, 'icons_container'):
            self.icons_container.hide()
        self.value_label.show()
        self.value_label.setText(value)
        self.info_label.setText(info)
    
    def set_value_with_icons(self, categories_data: list, info: str = ""):
        """
        Устанавливает значение с иконками категорий.
        
        Args:
            categories_data: список кортежей (icon_name, icon_color, is_active)
            info: текст подписи
        """
        # Создаём контейнер для иконок если его нет
        if not hasattr(self, 'icons_container'):
            self.icons_container = QWidget()
            self.icons_layout = QHBoxLayout(self.icons_container)
            self.icons_layout.setContentsMargins(0, 0, 0, 0)
            self.icons_layout.setSpacing(4)
            # Вставляем после value_label
            lay = self.layout()
            if isinstance(lay, QVBoxLayout):
                lay.insertWidget(2, self.icons_container)
            else:
                # Fallback: keep layout stable even if stubs/types differ.
                try:
                    lay.insertWidget(2, self.icons_container)  # type: ignore[attr-defined]
                except Exception:
                    try:
                        lay.addWidget(self.icons_container)  # type: ignore[attr-defined]
                    except Exception:
                        pass
        
        # Очищаем старые иконки
        while self.icons_layout.count():
            item = self.icons_layout.takeAt(0)
            if not item:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        
        # Скрываем текстовый label, показываем иконки
        self.value_label.hide()
        self.icons_container.show()
        
        # Добавляем иконки категорий
        active_count = 0
        for icon_name, icon_color, is_active in categories_data:
            if is_active:
                active_count += 1
                icon_label = QLabel()
                try:
                    pixmap = qta.icon(icon_name, color=icon_color).pixmap(20, 20)
                    icon_label.setPixmap(pixmap)
                except:
                    pixmap = qta.icon('fa5s.globe', color=get_theme_tokens().accent_hex).pixmap(20, 20)
                    icon_label.setPixmap(pixmap)
                icon_label.setFixedSize(22, 22)
                icon_label.setToolTip(icon_name.split('.')[-1].replace('-', ' ').title())
                self.icons_layout.addWidget(icon_label)
        
        # Если слишком много - показываем +N
        if active_count > 10:
            # Оставляем первые 9 + счётчик
            while self.icons_layout.count() > 9:
                item = self.icons_layout.takeAt(9)
                if not item:
                    continue
                w = item.widget()
                if w is not None:
                    w.deleteLater()
            
            extra_label = QLabel(f"+{active_count - 9}")
            tokens = get_theme_tokens()
            extra_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {tokens.fg_muted};
                    font-size: 11px;
                    font-weight: 600;
                    padding: 2px 6px;
                    background: {tokens.surface_bg};
                    border: 1px solid {tokens.surface_border};
                    border-radius: 8px;
                }}
                """
            )
            self.icons_layout.addWidget(extra_label)
        
        self.icons_layout.addStretch()
        self.info_label.setText(info)
        
    def set_status_color(self, status: str):
        """Меняет цвет иконки по статусу"""
        semantic = get_semantic_palette()
        try:
            neutral = get_theme_tokens().accent_hex
        except Exception:
            neutral = get_theme_tokens("Темная синяя").accent_hex
        colors = {
            'running': semantic.success,
            'stopped': semantic.error,
            'warning': semantic.warning,
            'neutral': neutral,
        }
        color = colors.get(status, colors['neutral'])
        # Для простоты меняем только цвет value_label
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 18px;
                font-weight: 600;
            }}
        """)

    def mousePressEvent(self, event):  # type: ignore[override]
        """Обработка клика по карточке"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HomePage(BasePage):
    """Главная страница - обзор состояния"""

    # Сигналы для навигации на другие страницы
    navigate_to_control = pyqtSignal()
    navigate_to_strategies = pyqtSignal()
    navigate_to_autostart = pyqtSignal()
    navigate_to_premium = pyqtSignal()

    _LAUNCH_METHOD_LABELS = {
        "direct_zapret2": "Zapret 2",
        "direct_zapret1": "Zapret 1 (прямой запуск)",
        "bat": "Zapret 1 (bat)",
        "orchestra": "Оркестратор",
        "direct_zapret2_orchestra": "Оркестраторный Zapret 2",
    }

    def __init__(self, parent=None):
        super().__init__("Главная", "Обзор состояния Zapret", parent)

        self._autostart_worker = None
        self._home_intro_checked = False
        self._home_intro_running = False
        self._home_intro_pending = 0
        self._home_intro_animations = []
        self._home_intro_target_heights = {}
        self._build_ui()
        self._connect_card_signals()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                if hasattr(self, "progress_bar") and self.progress_bar is not None:
                    self.progress_bar.setStyleSheet(_build_progress_style())
        except Exception:
            pass
        super().changeEvent(event)
    
    def showEvent(self, event):  # type: ignore[override]
        """При показе страницы обновляем статус автозапуска"""
        super().showEvent(event)
        # Запускаем проверку автозапуска в фоне с небольшой задержкой
        QTimer.singleShot(100, self._check_autostart_status)
        # Обновляем карточку метода запуска, когда UI стабилизировался.
        QTimer.singleShot(150, self._refresh_strategy_card)
        if not self._home_intro_checked:
            QTimer.singleShot(0, self._maybe_play_home_intro)

    def _get_launch_method_display_name(self) -> str:
        """Возвращает человекочитаемое название текущего метода запуска."""
        try:
            from strategy_menu import get_strategy_launch_method

            method = (get_strategy_launch_method() or "").strip().lower()
            if method:
                return self._LAUNCH_METHOD_LABELS.get(method, self._LAUNCH_METHOD_LABELS["direct_zapret2"])
        except Exception:
            pass
        return self._LAUNCH_METHOD_LABELS["direct_zapret2"]

    def update_launch_method_card(self) -> None:
        """Обновляет карточку метода запуска на главной странице."""
        self.strategy_card.set_value(
            self._get_launch_method_display_name(),
            "Текущий метод запуска",
        )

    def _refresh_strategy_card(self) -> None:
        """Обновляет карточку метода запуска после инициализации UI."""
        self.update_launch_method_card()
    
    def _check_autostart_status(self):
        """Запускает фоновую проверку статуса автозапуска"""
        if self._autostart_worker is not None and self._autostart_worker.isRunning():
            return
        
        self._autostart_worker = AutostartCheckWorker()
        self._autostart_worker.finished.connect(self._on_autostart_checked)
        self._autostart_worker.start()
    
    def _on_autostart_checked(self, enabled: bool):
        """Обработчик результата проверки автозапуска"""
        self.update_autostart_status(enabled)
        
    def _build_ui(self):
        # Сетка карточек статуса
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Карточка статуса DPI
        self.dpi_status_card = StatusCard("fa5s.shield-alt", "Статус Zapret")
        self.dpi_status_card.set_value("Проверка...", "Определение состояния")
        cards_layout.addWidget(self.dpi_status_card, 0, 0)
        
        # Карточка стратегии
        self.strategy_card = StatusCard("fa5s.cog", "Метод запуска")
        self.strategy_card.set_value("Zapret 2", "Текущий метод запуска")
        cards_layout.addWidget(self.strategy_card, 0, 1)
        
        # Карточка автозапуска
        self.autostart_card = StatusCard("fa5s.rocket", "Автозапуск")
        self.autostart_card.set_value("Отключён", "Запускайте вручную")
        cards_layout.addWidget(self.autostart_card, 1, 0)
        
        # Карточка подписки
        self.subscription_card = StatusCard("fa5s.star", "Подписка")
        self.subscription_card.set_value("Free", "Базовые функции")
        cards_layout.addWidget(self.subscription_card, 1, 1)
        
        self.cards_widget = QWidget(self.content)  # ✅ Явный родитель
        self.cards_widget.setLayout(cards_layout)
        self.add_widget(self.cards_widget)
        
        self.add_spacing(8)
        
        # Быстрые действия
        self.add_section_title("Быстрые действия")
        
        self.actions_card = SettingsCard()
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # Кнопка запуска
        self.start_btn = ActionButton("Запустить", "fa5s.play", accent=True)
        actions_layout.addWidget(self.start_btn)
        
        # Кнопка остановки
        self.stop_btn = ActionButton("Остановить", "fa5s.stop")
        self.stop_btn.setVisible(False)
        actions_layout.addWidget(self.stop_btn)
        
        # Кнопка теста
        self.test_btn = ActionButton("Тест соединения", "fa5s.wifi")
        actions_layout.addWidget(self.test_btn)
        
        # Кнопка папки
        self.folder_btn = ActionButton("Открыть папку", "fa5s.folder-open")
        actions_layout.addWidget(self.folder_btn)
        
        actions_layout.addStretch()
        self.actions_card.add_layout(actions_layout)
        self.add_widget(self.actions_card)
        
        self.add_spacing(8)
        
        # Статусная строка
        self.add_section_title("Статус")
        
        self.status_card = SettingsCard()
        self.status_indicator = StatusIndicator()
        self.status_indicator.set_status("Готов к работе", "neutral")
        self.status_card.add_widget(self.status_indicator)
        self.add_widget(self.status_card)
        
        # Индикатор загрузки (бегающая полоска)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(_build_progress_style())
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate mode
        self.progress_bar.setVisible(False)
        self.add_widget(self.progress_bar)

        self.add_spacing(12)

        # Блок Premium
        self._build_premium_block()

    def _maybe_play_home_intro(self) -> None:
        if self._home_intro_checked or self._home_intro_running:
            return

        self._home_intro_checked = True
        self._play_home_intro()

    def _play_home_intro(self) -> None:
        widgets = [
            getattr(self, "cards_widget", None),
            getattr(self, "actions_card", None),
            getattr(self, "status_card", None),
            getattr(self, "premium_card", None),
        ]
        widgets = [w for w in widgets if isinstance(w, QWidget)]
        if not widgets:
            self._finish_home_intro()
            return

        self._home_intro_running = True
        self._home_intro_pending = 0
        self._home_intro_target_heights = {}
        self._home_intro_animations = []

        for index, widget in enumerate(widgets):
            try:
                effect = widget.graphicsEffect()
                if not isinstance(effect, QGraphicsOpacityEffect):
                    effect = QGraphicsOpacityEffect(widget)
                    widget.setGraphicsEffect(effect)

                target_height = self._calc_intro_target_height(widget)
                self._home_intro_target_heights[id(widget)] = target_height
                widget.setMaximumHeight(0)
                effect.setOpacity(0.08)
                self._home_intro_pending += 1
            except Exception:
                continue

            QTimer.singleShot(index * 90, lambda target=widget: self._animate_home_intro_widget(target))

        if self._home_intro_pending <= 0:
            self._finish_home_intro()

    def _calc_intro_target_height(self, widget: QWidget) -> int:
        target = 0
        try:
            target = int(widget.sizeHint().height())
        except Exception:
            target = 0

        if target <= 0:
            try:
                target = int(widget.height())
            except Exception:
                target = 0

        return max(36, target)

    def _animate_home_intro_widget(self, widget: QWidget) -> None:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            self._home_intro_pending = max(0, self._home_intro_pending - 1)
            if self._home_intro_pending == 0:
                self._finish_home_intro()
            return

        target_height = self._home_intro_target_heights.get(id(widget), 0)
        if target_height <= 0:
            target_height = self._calc_intro_target_height(widget)

        opacity_animation = QPropertyAnimation(effect, b"opacity", self)
        opacity_animation.setDuration(360)
        opacity_animation.setStartValue(float(effect.opacity()))
        opacity_animation.setEndValue(1.0)
        opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        height_animation = QPropertyAnimation(widget, b"maximumHeight", self)
        height_animation.setDuration(360)
        height_animation.setStartValue(max(0, int(widget.maximumHeight())))
        height_animation.setEndValue(int(target_height))
        height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity_animation)
        group.addAnimation(height_animation)
        self._home_intro_animations.append(group)

        def _on_finished():
            try:
                widget.setMaximumHeight(16777215)
                widget.setGraphicsEffect(None)
            except Exception:
                pass

            try:
                effect.deleteLater()
            except Exception:
                pass

            self._home_intro_target_heights.pop(id(widget), None)

            try:
                self._home_intro_animations.remove(group)
            except Exception:
                pass

            try:
                group.deleteLater()
            except Exception:
                pass

            self._home_intro_pending = max(0, self._home_intro_pending - 1)
            if self._home_intro_pending == 0:
                self._finish_home_intro()

        group.finished.connect(_on_finished)
        group.start()

    def _finish_home_intro(self) -> None:
        self._home_intro_running = False
        self._home_intro_pending = 0
        self._home_intro_target_heights = {}

        for animation in list(self._home_intro_animations):
            try:
                animation.stop()
                animation.deleteLater()
            except Exception:
                pass
        self._home_intro_animations = []

        for widget in (
            getattr(self, "cards_widget", None),
            getattr(self, "actions_card", None),
            getattr(self, "status_card", None),
            getattr(self, "premium_card", None),
        ):
            if not isinstance(widget, QWidget):
                continue
            try:
                widget.setMaximumHeight(16777215)
                effect = widget.graphicsEffect()
                if isinstance(effect, QGraphicsOpacityEffect):
                    effect.setOpacity(1.0)
                    widget.setGraphicsEffect(None)
                    effect.deleteLater()
            except Exception:
                pass

    def _connect_card_signals(self):
        """Подключает клики по карточкам к сигналам навигации"""
        self.dpi_status_card.clicked.connect(self.navigate_to_control.emit)
        self.strategy_card.clicked.connect(self.navigate_to_strategies.emit)
        self.autostart_card.clicked.connect(self.navigate_to_autostart.emit)
        self.subscription_card.clicked.connect(self.navigate_to_premium.emit)
        
    def update_dpi_status(self, is_running: bool, strategy_name: str | None = None):
        """Обновляет отображение статуса DPI"""
        if is_running:
            self.dpi_status_card.set_value("Запущен", "Обход блокировок активен")
            self.dpi_status_card.set_status_color('running')
            self.start_btn.setVisible(False)
            self.stop_btn.setVisible(True)
        else:
            self.dpi_status_card.set_value("Остановлен", "Нажмите Запустить")
            self.dpi_status_card.set_status_color('stopped')
            self.start_btn.setVisible(True)
            self.stop_btn.setVisible(False)
            
        # На главной всегда отображаем текущий метод запуска (без иконок категорий).
        self.update_launch_method_card()

    def _update_strategy_card_with_icons(self, strategy_name: str):
        """Совместимость: карточка на главной теперь показывает метод запуска."""
        _ = strategy_name
        self.update_launch_method_card()
    
    def _truncate_strategy_name(self, name: str, max_items: int = 2) -> str:
        """Обрезает длинное название стратегии для карточки"""
        if not name or name in ("Не выбрана", "Прямой запуск"):
            return name
        
        # Определяем разделитель - поддерживаем и " • " (Direct режим) и ", " (старый формат)
        separator = " • " if " • " in name else ", "
        
        # Если это список категорий
        if separator in name:
            parts = name.split(separator)
            # Проверяем есть ли "+N ещё" в конце
            extra = ""
            if parts and (parts[-1].startswith("+") or "ещё" in parts[-1]):
                # Извлекаем число из "+N ещё"
                last_part = parts[-1]
                if last_part.startswith("+"):
                    # Формат "+2 ещё"
                    extra_num = int(''.join(filter(str.isdigit, last_part))) or 0
                    parts = parts[:-1]
                    extra_num += len(parts) - max_items
                    if extra_num > 0:
                        extra = f"+{extra_num}"
            elif len(parts) > max_items:
                extra = f"+{len(parts) - max_items}"
                
            if len(parts) > max_items:
                return separator.join(parts[:max_items]) + (f" {extra}" if extra else "")
            elif extra:
                return separator.join(parts) + f" {extra}"
                
        return name
            
    def update_autostart_status(self, enabled: bool):
        """Обновляет отображение статуса автозапуска"""
        if enabled:
            self.autostart_card.set_value("Включён", "Запускается с Windows")
            self.autostart_card.set_status_color('running')
        else:
            self.autostart_card.set_value("Отключён", "Запускайте вручную")
            self.autostart_card.set_status_color('neutral')
            
    def update_subscription_status(self, is_premium: bool, days: int | None = None):
        """Обновляет отображение статуса подписки"""
        if is_premium:
            if days:
                self.subscription_card.set_value("Premium", f"Осталось {days} дней")
            else:
                self.subscription_card.set_value("Premium", "Все функции доступны")
            self.subscription_card.set_status_color('running')
        else:
            self.subscription_card.set_value("Free", "Базовые функции")
            self.subscription_card.set_status_color('neutral')
            
    def set_status(self, text: str, status: str = "neutral"):
        """Устанавливает текст статусной строки"""
        self.status_indicator.set_status(text, status)
    
    def set_loading(self, loading: bool, text: str = ""):
        """Показывает/скрывает индикатор загрузки и блокирует кнопки"""
        self.progress_bar.setVisible(loading)
        
        # Блокируем/разблокируем кнопки
        self.start_btn.setEnabled(not loading)
        self.stop_btn.setEnabled(not loading)
        
        # Обновляем статус если есть текст
        if loading and text:
            self.status_indicator.set_status(text, "neutral")
        
    def _build_premium_block(self):
        """Создает блок Premium на главной странице"""
        self.premium_card = SettingsCard()
        
        premium_layout = QHBoxLayout()
        premium_layout.setSpacing(16)
        
        # Иконка звезды
        star_label = QLabel()
        star_label.setPixmap(qta.icon('fa5s.star', color='#ffc107').pixmap(32, 32))
        star_label.setFixedSize(40, 40)
        premium_layout.addWidget(star_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title = QLabel("Zapret Premium")
        try:
            title.setProperty("tone", "primary")
        except Exception:
            pass
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        text_layout.addWidget(title)
        
        desc = QLabel("Дополнительные темы, приоритетная поддержка и VPN-сервис")
        try:
            desc.setProperty("tone", "muted")
        except Exception:
            pass
        desc.setStyleSheet("font-size: 12px;")
        desc.setWordWrap(True)
        text_layout.addWidget(desc)
        
        premium_layout.addLayout(text_layout, 1)
        
        # Кнопка Premium
        self.premium_link_btn = ActionButton("Подробнее", "fa5s.arrow-right")
        self.premium_link_btn.setFixedHeight(36)
        premium_layout.addWidget(self.premium_link_btn)
        
        self.premium_card.add_layout(premium_layout)
        self.add_widget(self.premium_card)
