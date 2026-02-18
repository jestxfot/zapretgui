# ui/pages/autostart_page.py
"""Страница настроек автозапуска"""

from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
import qtawesome as qta
import os

from .base_page import BasePage
from ui.compat_widgets import SettingsCard, ActionButton
from ui.theme import get_theme_tokens
from ui.theme_semantic import get_semantic_palette
from log import log

try:
    from qfluentwidgets import (
        SimpleCardWidget,
        StrongBodyLabel,
        BodyLabel,
        CaptionLabel,
    )
    _HAS_FLUENT = True
except ImportError:
    SimpleCardWidget = QWidget  # type: ignore[misc,assignment]
    StrongBodyLabel = QLabel    # type: ignore[misc,assignment]
    BodyLabel = QLabel          # type: ignore[misc,assignment]
    CaptionLabel = QLabel       # type: ignore[misc,assignment]
    _HAS_FLUENT = False


class AutostartDetectorWorker(QThread):
    """Фоновый поток для определения типа автозапуска"""
    finished = pyqtSignal(str)  # Передаёт тип автозапуска или None

    # Маппинг методов из реестра в UI типы
    METHOD_TO_TYPE = {
        "exe": "gui",              # GUI автозапуск
        "direct_task": "logon",    # Direct режим - при входе
        "direct_boot": "boot",     # Direct режим - при загрузке
        "direct_service": "service",  # Direct служба Windows
        "service": "service",      # BAT служба Windows
        "task": "logon",           # BAT задача при входе
        "direct_task_bat": "logon",
        "direct_boot_bat": "boot",
    }

    def run(self):
        try:
            autostart_type = self._detect_type()
            self.finished.emit(autostart_type or "")
        except Exception as e:
            log(f"AutostartDetectorWorker error: {e}", "WARNING")
            self.finished.emit("")

    def _detect_type(self) -> str:
        """Определяет какой тип автозапуска сейчас активен"""
        try:
            from autostart.registry_check import AutostartRegistryChecker

            # 1. Проверяем статус и метод из реестра (основной источник)
            if AutostartRegistryChecker.is_autostart_enabled():
                method = AutostartRegistryChecker.get_autostart_method()
                if method and method in self.METHOD_TO_TYPE:
                    return self.METHOD_TO_TYPE[method]

            # 2. Если реестр пустой, возвращаем None
            return None

        except Exception as e:
            log(f"Error in _detect_type: {e}", "WARNING")
            return None


class AutostartOptionCard(SimpleCardWidget):
    """Карточка опции автозапуска"""

    clicked = pyqtSignal()

    def __init__(self, icon_name: str, title: str, description: str,
                 accent: bool = False, recommended: bool = False, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._accent = accent
        self._recommended = recommended
        self._disabled = False
        self._is_active = False
        self._icon_name = icon_name
        self._tokens = get_theme_tokens()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Иконка
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(36, 36)
        layout.addWidget(self._icon_label)

        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        self._title_label = StrongBodyLabel(title)
        title_layout.addWidget(self._title_label)

        self._rec_label = None
        if recommended:
            semantic = get_semantic_palette()
            self._rec_label = QLabel("Рекомендуется")
            self._rec_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {semantic.success_badge};
                    color: {semantic.on_color};
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 8px;
                    border-radius: 8px;
                }}
            """)
            title_layout.addWidget(self._rec_label)

        title_layout.addStretch()
        text_layout.addLayout(title_layout)

        self._desc_label = CaptionLabel(description)
        self._desc_label.setWordWrap(True)
        text_layout.addWidget(self._desc_label)

        layout.addLayout(text_layout, 1)

        # Стрелка
        self._arrow = QLabel()
        layout.addWidget(self._arrow)

        self._apply_visuals()

    def refresh_theme(self) -> None:
        self._tokens = get_theme_tokens()
        self._apply_visuals()

    def _apply_visuals(self) -> None:
        tokens = self._tokens or get_theme_tokens("Темная синяя")
        semantic = get_semantic_palette()

        if self._is_active:
            icon_color = semantic.success
            arrow_icon = qta.icon("fa5s.check-circle", color=semantic.success)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self._disabled:
            icon_color = tokens.fg_faint
            arrow_icon = qta.icon("fa5s.chevron-right", color=tokens.fg_faint)
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            icon_color = tokens.accent_hex if self._accent else tokens.fg
            arrow_icon = qta.icon("fa5s.chevron-right", color=tokens.fg_faint)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._icon_label.setPixmap(qta.icon(self._icon_name, color=icon_color).pixmap(28, 28))

        if self._rec_label:
            if self._disabled:
                # Dim the badge when the option is not available.
                self._rec_label.setStyleSheet(
                    f"""
                    QLabel {{
                        background-color: {tokens.surface_bg_disabled};
                        border: 1px solid {tokens.surface_border_disabled};
                        color: {tokens.fg_faint};
                        font-size: 10px;
                        font-weight: 600;
                        padding: 2px 8px;
                        border-radius: 8px;
                    }}
                    """
                )
            else:
                # Keep a stable green semantic badge.
                semantic = get_semantic_palette()
                self._rec_label.setStyleSheet(
                    f"""
                    QLabel {{
                        background-color: {semantic.success_badge};
                        color: {semantic.on_color};
                        font-size: 10px;
                        font-weight: 600;
                        padding: 2px 8px;
                        border-radius: 8px;
                    }}
                    """
                )

        self._arrow.setPixmap(arrow_icon.pixmap(18 if self._is_active else 16, 18 if self._is_active else 16))

    def set_disabled(self, disabled: bool, is_active: bool = False):
        """
        Устанавливает состояние карточки.

        Args:
            disabled: True - карточка заблокирована (не кликабельна)
            is_active: True - карточка активна (выделена зелёным, но не кликабельна)
        """
        self._disabled = disabled
        self._is_active = is_active

        self._apply_visuals()
        self.update()  # Принудительное обновление виджета

    def enterEvent(self, event):
        if not self._disabled and not self._is_active:
            pass  # SimpleCardWidget handles its own hover background
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        # Не реагируем на клик если карточка заблокирована или активна
        if event.button() == Qt.MouseButton.LeftButton and not self._disabled and not self._is_active:
            self.clicked.emit()
        super().mousePressEvent(event)


class ClickableModeCard(SimpleCardWidget):
    """Кликабельная карточка режима"""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def refresh_theme(self) -> None:
        # SimpleCardWidget handles its own theming; nothing extra needed.
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            log("ClickableModeCard: clicked!", "DEBUG")
            self.clicked.emit()
        super().mousePressEvent(event)


class AutostartPage(BasePage):
    """Страница настроек автозапуска"""

    # Сигналы для связи с main.py
    autostart_enabled = pyqtSignal()
    autostart_disabled = pyqtSignal()
    navigate_to_dpi_settings = pyqtSignal()  # Переход на страницу настроек DPI

    def __init__(self, parent=None):
        super().__init__("Автозапуск", "Настройка автоматического запуска Zapret", parent)

        self._app_instance = None
        self.strategy_name = None
        self.bat_folder = None
        self.json_folder = None
        self._current_autostart_type = None  # Текущий активный тип автозапуска
        self._detector_worker = None  # Фоновый поток для определения типа
        self._detection_pending = False  # Флаг ожидания результата

        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._autostart_enabled = False

        self._build_ui()

        # Apply theme to custom inline widgets.
        self._apply_theme()

    def showEvent(self, event):
        """Вызывается при показе страницы - запускаем определение в фоне"""
        super().showEvent(event)
        # Spontaneous showEvent = система показала окно (восстановление из трея/свёрнутого).
        # Пропускаем тяжёлую детекцию при простом восстановлении окна.
        if event.spontaneous():
            return
        # Запускаем определение типа автозапуска в фоновом потоке
        # с небольшой задержкой чтобы UI успел отрисоваться
        QTimer.singleShot(50, self._start_autostart_detection)

    def _start_autostart_detection(self):
        """Запускает определение типа автозапуска в фоновом потоке"""
        # Если уже идёт проверка, не запускаем новую
        if self._detection_pending:
            return

        # Если предыдущий поток ещё жив, ждём его завершения
        if self._detector_worker is not None and self._detector_worker.isRunning():
            return

        self._detection_pending = True
        self._detector_worker = AutostartDetectorWorker()
        self._detector_worker.finished.connect(self._on_autostart_detected)
        self._detector_worker.start()

    def _on_autostart_detected(self, autostart_type: str):
        """Обработчик результата определения типа автозапуска"""
        self._detection_pending = False

        # Пустая строка означает None
        if not autostart_type:
            autostart_type = None

        log(f"Detected autostart type: {autostart_type}", "DEBUG")

        if autostart_type:
            self._current_autostart_type = autostart_type
            self.update_status(True, self.strategy_name, autostart_type)
        else:
            self._current_autostart_type = None
            self.update_status(False)

    @property
    def app_instance(self):
        """Ленивая инициализация app_instance"""
        if self._app_instance is None:
            self._auto_init()
        return self._app_instance

    @app_instance.setter
    def app_instance(self, value):
        self._app_instance = value

    def _auto_init(self):
        """Автоматическая инициализация из parent или глобального контекста"""
        try:
            from config import BAT_FOLDER, INDEXJSON_FOLDER

            # Ищем главное приложение через цепочку parent
            widget = self.parent()
            while widget is not None:
                # LupiDPIApp имеет атрибут dpi_controller
                if hasattr(widget, 'dpi_controller'):
                    self._app_instance = widget
                    log("AutostartPage: app_instance найден через parent", "DEBUG")
                    break
                widget = widget.parent() if hasattr(widget, 'parent') else None

            # Устанавливаем папки
            if self.bat_folder is None:
                self.bat_folder = BAT_FOLDER
            if self.json_folder is None:
                self.json_folder = INDEXJSON_FOLDER

            # Обновляем имя стратегии
            if self._app_instance and self.strategy_name is None:
                if hasattr(self._app_instance, 'current_strategy_label'):
                    self.strategy_name = self._app_instance.current_strategy_label.text()
                    if self.strategy_name == "Автостарт DPI отключен":
                        from config.reg import get_last_bat_strategy
                        self.strategy_name = get_last_bat_strategy()
                    self.current_strategy_label.setText(self.strategy_name or "Не выбрана")

        except Exception as e:
            log(f"AutostartPage._auto_init ошибка: {e}", "WARNING")

    def set_app_instance(self, app):
        """Устанавливает ссылку на главное приложение"""
        self._app_instance = app

    def set_folders(self, bat_folder: str, json_folder: str):
        """Устанавливает папки для BAT режима"""
        self.bat_folder = bat_folder
        self.json_folder = json_folder

    def _ensure_folders_initialized(self):
        """Гарантирует что папки инициализированы"""
        if self.bat_folder is None or self.json_folder is None:
            from config import BAT_FOLDER, INDEXJSON_FOLDER
            if self.bat_folder is None:
                self.bat_folder = BAT_FOLDER
                log(f"AutostartPage: bat_folder установлен из config: {BAT_FOLDER}", "DEBUG")
            if self.json_folder is None:
                self.json_folder = INDEXJSON_FOLDER
                log(f"AutostartPage: json_folder установлен из config: {INDEXJSON_FOLDER}", "DEBUG")

    def set_strategy_name(self, name: str):
        """Устанавливает имя текущей стратегии"""
        self.strategy_name = name
        if hasattr(self, 'current_strategy_label'):
            self.current_strategy_label.setText(name or "Не выбрана")

    def _build_ui(self):
        tokens = get_theme_tokens()
        # ═══════════════════════════════════════════════════════════
        # Статус автозапуска
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Статус")

        status_card = SettingsCard()

        status_layout = QHBoxLayout()
        status_layout.setSpacing(14)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(qta.icon('fa5s.circle', color=tokens.fg_faint).pixmap(20, 20))
        self.status_icon.setFixedSize(24, 24)
        status_layout.addWidget(self.status_icon)

        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(4)

        self.status_label = StrongBodyLabel("Автозапуск отключён")
        status_text_layout.addWidget(self.status_label)

        self.status_desc = CaptionLabel("Zapret не запускается автоматически")
        status_text_layout.addWidget(self.status_desc)

        status_layout.addLayout(status_text_layout, 1)

        # Кнопка отключения (видна только когда автозапуск включен)
        self.disable_btn = ActionButton("Отключить", "fa5s.times")
        self.disable_btn.setFixedHeight(36)
        self.disable_btn.setVisible(False)
        self.disable_btn.clicked.connect(self._on_disable_clicked)
        status_layout.addWidget(self.disable_btn)

        status_card.add_layout(status_layout)
        self.add_widget(status_card)

        self.add_spacing(20)

        # ═══════════════════════════════════════════════════════════
        # Режим запуска (кликабельная карточка)
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Режим")

        self.mode_card = ClickableModeCard()
        self.mode_card.clicked.connect(self._on_mode_card_clicked)

        mode_card_layout = QVBoxLayout(self.mode_card)
        mode_card_layout.setContentsMargins(16, 14, 16, 14)
        mode_card_layout.setSpacing(0)

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(12)

        self._mode_icon_label = QLabel()
        self._mode_icon_label.setFixedSize(22, 22)
        self._mode_icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mode_layout.addWidget(self._mode_icon_label)

        self._mode_text_label = CaptionLabel("Текущий режим:")
        self._mode_text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mode_layout.addWidget(self._mode_text_label)

        self.mode_label = BodyLabel("Загрузка...")
        self.mode_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mode_layout.addWidget(self.mode_label)

        mode_layout.addSpacing(20)

        self._strategy_text_label = CaptionLabel("Стратегия:")
        self._strategy_text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mode_layout.addWidget(self._strategy_text_label)

        self.current_strategy_label = BodyLabel("Не выбрана")
        self.current_strategy_label.setWordWrap(True)  # Перенос текста
        self.current_strategy_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mode_layout.addWidget(self.current_strategy_label, 1)

        # Стрелка для индикации кликабельности
        self.mode_arrow = QLabel()
        self.mode_arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mode_layout.addWidget(self.mode_arrow)

        mode_card_layout.addLayout(mode_layout)

        self.add_widget(self.mode_card)

        self.add_spacing(20)

        # ═══════════════════════════════════════════════════════════
        # Варианты автозапуска
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Выберите тип автозапуска")

        # GUI автозапуск
        self.gui_option = AutostartOptionCard(
            "fa5s.desktop",
            "Автозапуск программы Zapret",
            "Запускает главное окно программы при входе в Windows. "
            "Вы сможете управлять DPI из системного трея.",
            accent=True
        )
        self.gui_option.clicked.connect(self._on_gui_autostart)
        self.add_widget(self.gui_option)

        self.add_spacing(12)

        # Контейнер для опций стратегий
        self.strategies_container = QWidget()
        self.strategies_layout = QVBoxLayout(self.strategies_container)
        self.strategies_layout.setContentsMargins(0, 0, 0, 0)
        self.strategies_layout.setSpacing(12)

        # Служба Windows (для Direct режима) - СКРЫТО: пока не реализовано
        self.service_option = AutostartOptionCard(
            "fa5s.server",
            "Служба Windows",
            "Создает настоящую службу Windows для запуска winws.exe. "
            "Самый надежный способ — работает даже если никто не вошел в систему.",
            recommended=True
        )
        self.service_option.clicked.connect(self._on_service_autostart)
        self.strategies_layout.addWidget(self.service_option)
        self.service_option.hide()  # Временно скрыто

        # Задача при входе - СКРЫТО: пока не реализовано
        self.logon_option = AutostartOptionCard(
            "fa5s.user",
            "Задача при входе пользователя",
            "Создает задачу планировщика для запуска DPI при входе пользователя в систему."
        )
        self.logon_option.clicked.connect(self._on_logon_autostart)
        self.strategies_layout.addWidget(self.logon_option)
        self.logon_option.hide()  # Временно скрыто

        # Задача при загрузке - СКРЫТО: пока не реализовано
        self.boot_option = AutostartOptionCard(
            "fa5s.power-off",
            "Задача при загрузке системы",
            "Создает задачу планировщика для запуска DPI при загрузке Windows (до входа пользователя)."
        )
        self.boot_option.clicked.connect(self._on_boot_autostart)
        self.strategies_layout.addWidget(self.boot_option)
        self.boot_option.hide()  # Временно скрыто

        self.add_widget(self.strategies_container)

        self.add_spacing(20)

        # ═══════════════════════════════════════════════════════════
        # Информация
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Информация")

        info_card = SettingsCard()
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        # Подсказка
        tip_layout = QHBoxLayout()
        tip_layout.setSpacing(10)

        tip_icon = QLabel()
        tip_icon.setPixmap(qta.icon('fa5s.lightbulb', color=get_semantic_palette().warning).pixmap(18, 18))
        tip_icon.setFixedSize(22, 22)
        tip_layout.addWidget(tip_icon)

        self._tip_text_label = CaptionLabel(
            "Рекомендация: Для максимальной надежности используйте "
            "«Служба Windows» — она запускается раньше всех программ и автоматически "
            "перезапускается при сбоях."
        )
        self._tip_text_label.setWordWrap(True)
        tip_layout.addWidget(self._tip_text_label, 1)

        info_layout.addLayout(tip_layout)
        info_card.add_layout(info_layout)
        self.add_widget(info_card)

        # Обновляем режим
        self._update_mode()

        # Apply theme once after building the UI.
        self._apply_theme()

    def _update_mode(self):
        """Обновляет отображение режима"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            # Режим оркестратора - только автозапуск программы
            is_orchestra = method in ("orchestra", "direct_zapret2_orchestra")

            if method == "direct_zapret2":
                self.mode_label.setText("Прямой запуск (Zapret 2)")
            elif method == "direct_zapret2_orchestra":
                self.mode_label.setText("Оркестратор Zapret 2")
            elif method == "orchestra":
                self.mode_label.setText("Оркестр (автообучение)")
            else:
                self.mode_label.setText("Классический (BAT файлы)")

            # Опции службы/задач:
            # - orchestra/direct_zapret2_orchestra: оставляем только GUI автозапуск
            # - остальные режимы: показываем службу и задачу при входе
            self.service_option.setVisible(not is_orchestra)
            self.logon_option.setVisible(not is_orchestra)
            self.boot_option.setVisible(False)

        except Exception as e:
            log(f"Ошибка обновления режима: {e}", "WARNING")
            self.mode_label.setText("Неизвестно")

    def _on_mode_card_clicked(self):
        """Обработчик клика по карточке режима"""
        log("AutostartPage: mode_card clicked, emitting navigate_to_dpi_settings", "DEBUG")
        self.navigate_to_dpi_settings.emit()

    def _update_arrow_color(self):
        """Обновляет цвет стрелки в зависимости от темы"""
        if not hasattr(self, 'mode_arrow'):
            return

        tokens = get_theme_tokens()
        self.mode_arrow.setPixmap(qta.icon('fa5s.chevron-right', color=tokens.fg_faint).pixmap(14, 14))

    def on_theme_changed(self):
        """Вызывается при смене темы"""
        self._schedule_theme_refresh()

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

            # Mode card icon — accent color still needs manual update
            if hasattr(self, "_mode_icon_label"):
                self._mode_icon_label.setPixmap(qta.icon("fa5s.cog", color=tokens.accent_hex).pixmap(18, 18))

            # mode_label gets accent color; Fluent label handles its own fg otherwise
            if hasattr(self, "mode_label"):
                self.mode_label.setStyleSheet(
                    f"color: {tokens.accent_hex}; font-size: 13px; font-weight: 600;"
                )

            # current_strategy_label bold override
            if hasattr(self, "current_strategy_label"):
                self.current_strategy_label.setStyleSheet(
                    f"color: {tokens.fg}; font-size: 13px; font-weight: 500;"
                )

            self._update_arrow_color()

            # Keep the status icon consistent with the current theme.
            if hasattr(self, "status_icon"):
                if getattr(self, "_autostart_enabled", False):
                    self.status_icon.setPixmap(qta.icon('fa5s.check-circle', color=get_semantic_palette().success).pixmap(20, 20))
                else:
                    self.status_icon.setPixmap(qta.icon('fa5s.circle', color=tokens.fg_faint).pixmap(20, 20))

            # Refresh option cards.
            for card_name in ("gui_option", "service_option", "logon_option", "boot_option"):
                card = getattr(self, card_name, None)
                if card is not None and hasattr(card, "refresh_theme"):
                    try:
                        card.refresh_theme()
                    except Exception:
                        pass
            if hasattr(self, "mode_card") and hasattr(self.mode_card, "refresh_theme"):
                try:
                    self.mode_card.refresh_theme()
                except Exception:
                    pass
        finally:
            self._applying_theme_styles = False

    def update_status(self, enabled: bool, strategy_name: str = None, autostart_type: str = None):
        """Обновляет отображение статуса автозапуска"""
        self._autostart_enabled = bool(enabled)
        if enabled:
            self.status_label.setText("Автозапуск включён")

            type_desc = ""
            if autostart_type:
                type_map = {
                    "service": "как служба Windows",
                    "logon": "при входе пользователя",
                    "boot": "при загрузке системы",
                    "gui": "программа Zapret"
                }
                type_desc = type_map.get(autostart_type, "")

            desc = f"Zapret запускается автоматически"
            if type_desc:
                desc += f" {type_desc}"
            self.status_desc.setText(desc)

            self.status_icon.setPixmap(qta.icon('fa5s.check-circle', color=get_semantic_palette().success).pixmap(20, 20))
            self.disable_btn.setVisible(True)
        else:
            self.status_label.setText("Автозапуск отключён")
            self.status_desc.setText("Zapret не запускается автоматически")
            tokens = get_theme_tokens()
            self.status_icon.setPixmap(qta.icon('fa5s.circle', color=tokens.fg_faint).pixmap(20, 20))
            self.disable_btn.setVisible(False)

        if strategy_name:
            self.current_strategy_label.setText(strategy_name)

        # Обновляем состояние карточек (блокировка/разблокировка)
        self._update_options_state(enabled, autostart_type)

        # Обновляем режим при каждом обновлении статуса
        self._update_mode()

    def _update_options_state(self, autostart_enabled: bool, active_type: str = None):
        """Обновляет состояние карточек автозапуска (блокировка неактивных)"""
        # Если тип не передан но автозапуск включён, используем сохранённый тип
        if autostart_enabled and not active_type:
            active_type = self._current_autostart_type

        log(f"_update_options_state: enabled={autostart_enabled}, type={active_type}", "DEBUG")

        # Карта типов автозапуска к карточкам
        type_to_card = {
            "gui": self.gui_option,
            "service": self.service_option,
            "logon": self.logon_option,
            "boot": self.boot_option
        }

        if autostart_enabled and active_type:
            # Блокируем ВСЕ карточки, активную выделяем особым образом
            for type_name, card in type_to_card.items():
                is_active_card = type_name == active_type
                log(f"  Card '{type_name}': active={is_active_card}", "DEBUG")
                card.set_disabled(True, is_active=is_active_card)
        else:
            # Разблокируем все карточки
            for type_name, card in type_to_card.items():
                log(f"  Card '{type_name}': disabled=False", "DEBUG")
                card.set_disabled(False, is_active=False)

    def _on_disable_clicked(self):
        """Отключение автозапуска"""
        try:
            from autostart.autostart_remove import AutoStartCleaner

            cleaner = AutoStartCleaner()
            removed = cleaner.run()

            self._current_autostart_type = None
            self.update_status(False)
            self.autostart_disabled.emit()

            if removed:
                log(f"Автозапуск отключён, удалено записей: {removed}", "INFO")

        except Exception as e:
            log(f"Ошибка отключения автозапуска: {e}", "ERROR")

    def _on_gui_autostart(self):
        """Автозапуск GUI программы"""
        try:
            from autostart.autostart_exe import setup_autostart_for_exe

            ok = setup_autostart_for_exe(
                selected_mode=self.strategy_name or "Default",
                status_cb=lambda msg: log(msg, "INFO"),
            )

            if ok:
                self._current_autostart_type = "gui"
                self.update_status(True, self.strategy_name, "gui")
                self.autostart_enabled.emit()
            else:
                log("Не удалось настроить автозапуск GUI", "ERROR")

        except Exception as e:
            log(f"Ошибка автозапуска GUI: {e}", "ERROR")

    def _on_service_autostart(self):
        """Создание службы Windows"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            if method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                self._setup_direct_service()
            else:
                self._setup_bat_service()

        except Exception as e:
            log(f"Ошибка создания службы: {e}", "ERROR")

    def _on_logon_autostart(self):
        """Задача при входе пользователя"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            if method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                self._setup_direct_logon_task()
            else:
                self._setup_bat_logon_task()

        except Exception as e:
            log(f"Ошибка создания задачи: {e}", "ERROR")

    def _on_boot_autostart(self):
        """Задача при загрузке системы"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            if method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                self._setup_direct_boot_task()
            else:
                self._setup_bat_service()  # Для BAT это служба

        except Exception as e:
            log(f"Ошибка создания задачи: {e}", "ERROR")

    def _setup_direct_service(self):
        """Служба Windows для Direct режима"""
        from autostart.autostart_direct import collect_direct_strategy_args
        from autostart.autostart_direct_service import setup_direct_service

        if not self.app_instance:
            log("Приложение не инициализировано", "ERROR")
            return

        args, name, winws_exe = collect_direct_strategy_args(self.app_instance)

        if not args or not winws_exe:
            log("Не удалось собрать аргументы стратегии", "ERROR")
            return

        ok = setup_direct_service(
            winws_exe=winws_exe,
            strategy_args=args,
            strategy_name=name,
            ui_error_cb=lambda msg: log(msg, "ERROR")
        )

        if ok:
            self._current_autostart_type = "service"
            self.update_status(True, name, "service")
            self.autostart_enabled.emit()

    def _setup_direct_logon_task(self):
        """Задача при входе для Direct режима"""
        from autostart.autostart_direct import collect_direct_strategy_args, setup_direct_autostart_task

        if not self.app_instance:
            log("Приложение не инициализировано", "ERROR")
            return

        args, name, winws_exe = collect_direct_strategy_args(self.app_instance)

        if not args or not winws_exe:
            log("Не удалось собрать аргументы стратегии", "ERROR")
            return

        ok = setup_direct_autostart_task(
            winws_exe=winws_exe,
            strategy_args=args,
            strategy_name=name,
            ui_error_cb=lambda msg: log(msg, "ERROR")
        )

        if ok:
            self._current_autostart_type = "logon"
            self.update_status(True, name, "logon")
            self.autostart_enabled.emit()

    def _setup_direct_boot_task(self):
        """Задача при загрузке для Direct режима"""
        from autostart.autostart_direct import collect_direct_strategy_args, setup_direct_autostart_service

        if not self.app_instance:
            log("Приложение не инициализировано", "ERROR")
            return

        args, name, winws_exe = collect_direct_strategy_args(self.app_instance)

        if not args or not winws_exe:
            log("Не удалось собрать аргументы стратегии", "ERROR")
            return

        ok = setup_direct_autostart_service(
            winws_exe=winws_exe,
            strategy_args=args,
            strategy_name=name,
            ui_error_cb=lambda msg: log(msg, "ERROR")
        )

        if ok:
            self._current_autostart_type = "boot"
            self.update_status(True, name, "boot")
            self.autostart_enabled.emit()

    def _setup_bat_logon_task(self):
        """Задача при входе для BAT режима"""
        from autostart.autostart_strategy import setup_autostart_for_strategy
        from config.reg import get_last_bat_strategy

        # Инициализируем папки если не установлены
        self._ensure_folders_initialized()

        if not self.bat_folder:
            log("Папка стратегий не настроена", "ERROR")
            return

        # Для BAT режима используем сохранённую BAT-стратегию (отдельный ключ реестра).
        bat_strategy_name = get_last_bat_strategy()
        if not bat_strategy_name:
            log("Для BAT режима необходимо сначала выбрать стратегию", "ERROR")
            return

        ok = setup_autostart_for_strategy(
            selected_mode=bat_strategy_name,
            bat_folder=self.bat_folder,
            ui_error_cb=lambda msg: log(msg, "ERROR"),
        )

        if ok:
            self._current_autostart_type = "logon"
            self.update_status(True, bat_strategy_name, "logon")
            self.autostart_enabled.emit()

    def _setup_bat_service(self):
        """Служба для BAT режима"""
        from autostart.autostart_service import setup_service_for_strategy
        from config.reg import get_last_bat_strategy

        # Инициализируем папки если не установлены
        self._ensure_folders_initialized()

        if not self.bat_folder:
            log("Папка стратегий не настроена", "ERROR")
            return

        # Для BAT режима используем сохранённую BAT-стратегию (отдельный ключ реестра).
        bat_strategy_name = get_last_bat_strategy()
        if not bat_strategy_name:
            log("Для BAT режима необходимо сначала выбрать стратегию", "ERROR")
            return

        ok = setup_service_for_strategy(
            selected_mode=bat_strategy_name,
            bat_folder=self.bat_folder,
            ui_error_cb=lambda msg: log(msg, "ERROR"),
        )

        if ok:
            self._current_autostart_type = "service"
            self.update_status(True, bat_strategy_name, "service")
            self.autostart_enabled.emit()
