# ui/theme.py
import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QPixmap, QPalette, QBrush, QPainter, QColor
from PyQt6.QtWidgets import QPushButton, QMessageBox, QApplication, QMenu
from config import reg, HKCU
from log import log
from typing import Optional, Tuple
import time

# Константы (без изменений)
THEMES = {
    "Темная синяя": {"file": "dark_blue.xml", "status_color": "#ffffff", "button_color": "0, 125, 242"},
    "Темная бирюзовая": {"file": "dark_cyan.xml", "status_color": "#ffffff", "button_color": "14, 152, 211"},
    "Темная янтарная": {"file": "dark_amber.xml", "status_color": "#ffffff", "button_color": "224, 132, 0"},
    "Темная розовая": {"file": "dark_pink.xml", "status_color": "#ffffff", "button_color": "255, 93, 174"},
    "Светлая синяя": {"file": "light_blue.xml", "status_color": "#000000", "button_color": "25, 118, 210"},
    "Светлая бирюзовая": {"file": "light_cyan.xml", "status_color": "#000000", "button_color": "0, 172, 193"},
    "РКН Тян": {"file": "dark_blue.xml", "status_color": "#ffffff", "button_color": "63, 85, 182"},
    
    # Новые премиум темы
    "AMOLED Синяя": {"file": "dark_blue.xml", "status_color": "#ffffff", "button_color": "0, 150, 255", "amoled": True},
    "AMOLED Зеленая": {"file": "dark_teal.xml", "status_color": "#ffffff", "button_color": "0, 255, 127", "amoled": True},
    "AMOLED Фиолетовая": {"file": "dark_purple.xml", "status_color": "#ffffff", "button_color": "187, 134, 252", "amoled": True},
    "AMOLED Красная": {"file": "dark_red.xml", "status_color": "#ffffff", "button_color": "255, 82, 82", "amoled": True},
    
    # Полностью черная тема (премиум)
    "Полностью черная": {
        "file": "dark_blue.xml", 
        "status_color": "#ffffff", 
        "button_color": "32, 32, 32",
        "pure_black": True
    },
}

BUTTON_STYLE = """
QPushButton {{
    border: none;
    background-color: rgb({0});
    color: #fff;
    border-radius: 6px;
    padding: 10px;
    font-weight: bold;
    font-size: 10pt;
    min-height: 35px;
}}
QPushButton:hover {{
    background-color: rgba({0}, 0.8);
}}
QPushButton:pressed {{
    background-color: rgba({0}, 0.6);
}}
"""

COMMON_STYLE = "font-family: 'Segoe UI', Arial, sans-serif;"
BUTTON_HEIGHT = 35

STYLE_SHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
}
"""

# Стили для AMOLED тем
AMOLED_OVERRIDE_STYLE = """
QWidget {
    background-color: #000000;
    color: #ffffff;
}

QMainWindow {
    background-color: #000000;
}

QFrame {
    background-color: #000000;
    border: none;  /* Убираем рамку */
}

QLabel {
    background-color: transparent;
    color: #ffffff;
    border: none;  /* Убираем рамку у меток */
}

QComboBox {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    color: #ffffff;
    padding: 5px;
    border-radius: 4px;
}

QComboBox::drop-down {
    background-color: #1a1a1a;
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #000000;
    border: 1px solid #333333;
    selection-background-color: #333333;
    color: #ffffff;
}

QStackedWidget {
    background-color: #000000;
    border: none;  /* Убираем рамку */
}

/* Убираем рамки у кнопок в стеках */
QStackedWidget > QPushButton {
    border: none;
}

/* Убираем рамки у разделителей */
QFrame[frameShape="4"] {
    color: #333333;
    max-height: 1px;
}
"""

# Стили для полностью черной темы
PURE_BLACK_OVERRIDE_STYLE = """
QWidget {
    background-color: #000000;
    color: #ffffff;
}

QMainWindow {
    background-color: #000000;
}

QFrame {
    background-color: #000000;
    border: none;  /* Убираем рамку */
}

QLabel {
    background-color: transparent;
    color: #ffffff;
}

QComboBox {
    background-color: #000000;
    border: none;  /* Убираем рамку */
    color: #ffffff;
    padding: 5px;
    border-radius: 4px;
}

QComboBox::drop-down {
    background-color: #000000;
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #000000;
    border: none;  /* Убираем рамку */
    selection-background-color: #1a1a1a;
    color: #ffffff;
}

QStackedWidget {
    background-color: #000000;
}

QPushButton {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    color: #ffffff;
}

QPushButton:hover {
    background-color: #333333;
    border: none;  /* Убираем рамку */
}

QPushButton:pressed {
    background-color: #0a0a0a;
}

QFrame[frameShape="4"] {
    color: #1a1a1a;
}
"""

def get_selected_theme(default: str | None = None) -> str | None:
    """Возвращает сохранённую тему или default"""
    return reg(r"Software\ZapretReg2", "SelectedTheme") or default

def set_selected_theme(theme_name: str) -> bool:
    """Записывает строку SelectedTheme"""
    return reg(r"Software\ZapretReg2", "SelectedTheme", theme_name)

def get_windows_theme() -> str:
    """Читает системную тему Windows"""
    val = reg(
        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        "AppsUseLightTheme",
        root=HKCU
    )
    return "light" if val == 1 else "dark"


class PremiumCheckWorker(QObject):
    """Воркер для асинхронной проверки премиум статуса"""
    
    finished = pyqtSignal(bool, str, object)  # is_premium, message, days
    error = pyqtSignal(str)
    
    def __init__(self, donate_checker):
        super().__init__()
        self.donate_checker = donate_checker
    
    def run(self):
        """Выполнить проверку подписки"""
        try:
            log("Начало асинхронной проверки подписки", "DEBUG")
            start_time = time.time()
            
            if not self.donate_checker:
                self.finished.emit(False, "Checker не доступен", None)
                return
            
            # Проверяем тип checker'а
            checker_type = self.donate_checker.__class__.__name__
            if checker_type == 'DummyChecker':
                self.finished.emit(False, "Dummy checker", None)
                return
            
            # Выполняем проверку
            is_premium, message, days = self.donate_checker.check_subscription_status()
            
            elapsed = time.time() - start_time
            log(f"Асинхронная проверка завершена за {elapsed:.2f}с: premium={is_premium}", "DEBUG")
            
            self.finished.emit(is_premium, message, days)
            
        except Exception as e:
            log(f"Ошибка в PremiumCheckWorker: {e}", "❌ ERROR")
            self.error.emit(str(e))
            self.finished.emit(False, f"Ошибка: {e}", None)


class RippleButton(QPushButton):
    def __init__(self, text, parent=None, color=""):
        super().__init__(text, parent)
        self._ripple_pos = QPoint()
        self._ripple_radius = 0
        self._ripple_opacity = 0
        self._bgcolor = color
        
        # Настройка анимаций
        self._ripple_animation = QPropertyAnimation(self, b"rippleRadius", self)
        self._ripple_animation.setDuration(350)
        self._ripple_animation.setStartValue(0)
        self._ripple_animation.setEndValue(100)
        self._ripple_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._fade_animation = QPropertyAnimation(self, b"rippleOpacity", self)
        self._fade_animation.setDuration(350)
        self._fade_animation.setStartValue(0.4)
        self._fade_animation.setEndValue(0)

    @pyqtProperty(float)
    def rippleRadius(self):
        return self._ripple_radius

    @rippleRadius.setter
    def rippleRadius(self, value):
        self._ripple_radius = value
        self.update()

    @pyqtProperty(float)
    def rippleOpacity(self):
        return self._ripple_opacity

    @rippleOpacity.setter
    def rippleOpacity(self, value):
        self._ripple_opacity = value
        self.update()

    def mousePressEvent(self, event):
        self._ripple_pos = event.pos()
        self._ripple_opacity = 0.4
        
        # Вычисляем максимальный радиус
        max_radius = max(
            self._ripple_pos.x(),
            self._ripple_pos.y(),
            self.width() - self._ripple_pos.x(),
            self.height() - self._ripple_pos.y()
        ) * 1.5
        
        self._ripple_animation.setEndValue(max_radius)
        self._ripple_animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._fade_animation.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._ripple_radius > 0 and self._ripple_opacity > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setOpacity(self._ripple_opacity)
            
            painter.setBrush(QColor(255, 255, 255, 80))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                self._ripple_pos,
                int(self._ripple_radius),
                int(self._ripple_radius)
            )
            painter.end()


class ThemeManager:
    """Класс для управления темами приложения"""

    def __init__(self, app, widget, status_label, theme_folder, donate_checker=None):
        self.app = app
        self.widget = widget
        self.status_label = status_label
        self.theme_folder = theme_folder
        self.donate_checker = donate_checker
        self._fallback_due_to_premium: str | None = None
        
        # Кеш для премиум статуса
        self._premium_cache: Optional[Tuple[bool, str, Optional[int]]] = None
        self._cache_time: Optional[float] = None
        self._cache_duration = 60  # 60 секунд кеша
        
        # Потоки для асинхронных проверок
        self._check_thread: Optional[QThread] = None
        self._check_worker: Optional[PremiumCheckWorker] = None

        # список тем с премиум-статусом
        self.themes = []
        for name, info in THEMES.items():
            is_premium = (name == "РКН Тян" or 
                         name.startswith("AMOLED") or 
                         name == "Полностью черная" or
                         info.get("amoled", False) or
                         info.get("pure_black", False))
            self.themes.append({'name': name, 'premium': is_premium})

        # выбираем стартовую тему
        saved = get_selected_theme()
        if saved and saved in THEMES:
            if self._is_premium_theme(saved):
                # Используем кешированный результат или считаем что нет премиума при старте
                self.current_theme = "Темная синяя"
                self._fallback_due_to_premium = saved
                log(f"Премиум тема {saved} отложена до проверки подписки", "INFO")
            else:
                self.current_theme = saved
        else:
            self.current_theme = (
                "Светлая синяя" if get_windows_theme() == "light"
                else "Темная синяя"
            )

        # применяем тему, НО БЕЗ записи в настройки
        self.apply_theme(self.current_theme, persist=False)

    def __del__(self):
        """Деструктор для очистки ресурсов"""
        try:
            # Останавливаем поток если он запущен
            if hasattr(self, '_check_thread') and self._check_thread is not None:
                try:
                    if self._check_thread.isRunning():
                        self._check_thread.quit()
                        self._check_thread.wait(500)  # Ждем максимум 0.5 секунды
                except RuntimeError:
                    pass
        except Exception:
            pass

    def cleanup(self):
        """Безопасная очистка всех ресурсов"""
        try:
            # Очищаем кеш
            self._premium_cache = None
            self._cache_time = None
            
            # Останавливаем поток проверки
            if hasattr(self, '_check_thread') and self._check_thread is not None:
                try:
                    if self._check_thread.isRunning():
                        log("Останавливаем поток проверки премиума", "DEBUG")
                        self._check_thread.quit()
                        if not self._check_thread.wait(1000):
                            log("Принудительное завершение потока", "WARNING")
                            self._check_thread.terminate()
                            self._check_thread.wait()
                except RuntimeError:
                    pass
                finally:
                    self._check_thread = None
                    self._check_worker = None
                    
            log("ThemeManager очищен", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при очистке ThemeManager: {e}", "ERROR")

    def _is_premium_theme(self, theme_name: str) -> bool:
        """Проверяет, является ли тема премиум"""
        clean_name = self.get_clean_theme_name(theme_name)
        theme_info = THEMES.get(clean_name, {})
        return (clean_name in ["РКН Тян", "Полностью черная"] or 
                clean_name.startswith("AMOLED") or
                theme_info.get("amoled", False) or
                theme_info.get("pure_black", False))

    def _is_premium_available(self) -> bool:
        """Проверяет доступность премиума (использует кеш)"""
        if not self.donate_checker:
            return False
        
        # Проверяем кеш
        if self._premium_cache and self._cache_time:
            cache_age = time.time() - self._cache_time
            if cache_age < self._cache_duration:
                log(f"Используем кешированный премиум статус: {self._premium_cache[0]}", "DEBUG")
                return self._premium_cache[0]
        
        # Если кеша нет, возвращаем False и запускаем асинхронную проверку
        log("Кеш премиума отсутствует, запускаем асинхронную проверку", "DEBUG")
        self._start_async_premium_check()
        return False

    def _start_async_premium_check(self):
        """Запускает асинхронную проверку премиум статуса"""
        if not self.donate_checker:
            return
        
        # ✅ ДОБАВИТЬ ЗАЩИТУ
        if hasattr(self, '_check_in_progress') and self._check_in_progress:
            log("Проверка премиума уже выполняется, пропускаем", "DEBUG")
            return
        
        self._check_in_progress = True
            
        # Проверяем тип checker'а
        checker_type = self.donate_checker.__class__.__name__
        if checker_type == 'DummyChecker':
            log("DummyChecker обнаружен, пропускаем асинхронную проверку", "DEBUG")
            return
        
        # Проверяем существование потока перед проверкой isRunning
        if self._check_thread is not None:
            try:
                if self._check_thread.isRunning():
                    log("Асинхронная проверка уже выполняется", "DEBUG")
                    return
            except RuntimeError:
                # Поток был удален, сбрасываем ссылку
                log("Предыдущий поток был удален, создаем новый", "DEBUG")
                self._check_thread = None
                self._check_worker = None
        
        log("Запуск асинхронной проверки премиум статуса", "DEBUG")
        
        # Очищаем старые ссылки перед созданием новых
        if self._check_thread is not None:
            try:
                if self._check_thread.isRunning():
                    self._check_thread.quit()
                    self._check_thread.wait(1000)  # Ждем максимум 1 секунду
            except RuntimeError:
                pass
            self._check_thread = None
            self._check_worker = None
        
        # Создаем воркер и поток
        self._check_thread = QThread()
        self._check_worker = PremiumCheckWorker(self.donate_checker)
        self._check_worker.moveToThread(self._check_thread)
        
        # Подключаем сигналы
        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.finished.connect(self._on_premium_check_finished)
        self._check_worker.error.connect(self._on_premium_check_error)
        
        # Правильная очистка потока после завершения
        def cleanup_thread():
            try:
                self._check_in_progress = False
                if self._check_worker:
                    self._check_worker.deleteLater()
                    self._check_worker = None
                if self._check_thread:
                    self._check_thread.deleteLater()
                    self._check_thread = None
            except RuntimeError:
                # Объекты уже удалены
                self._check_worker = None
                self._check_thread = None
        
        self._check_worker.finished.connect(self._check_thread.quit)
        self._check_thread.finished.connect(cleanup_thread)
        
        # Запускаем поток
        try:
            self._check_thread.start()
        except RuntimeError as e:
            log(f"Ошибка запуска потока проверки премиума: {e}", "❌ ERROR")
            self._check_thread = None
            self._check_worker = None

    def _on_premium_check_finished(self, is_premium: bool, message: str, days: Optional[int]):
        """Обработчик завершения асинхронной проверки"""
        log(f"Асинхронная проверка завершена: premium={is_premium}, msg='{message}', days={days}", "DEBUG")
        
        # Обновляем кеш
        self._premium_cache = (is_premium, message, days)
        self._cache_time = time.time()
        
        # Обновляем заголовок окна
        if hasattr(self.widget, "update_title_with_subscription_status"):
            try:
                self.widget.update_title_with_subscription_status(is_premium, self.current_theme, days)
            except Exception as e:
                log(f"Ошибка обновления заголовка: {e}", "❌ ERROR")
        
        # Если есть отложенная премиум тема и премиум доступен, применяем её
        if self._fallback_due_to_premium and is_premium:
            log(f"Восстанавливаем отложенную премиум тему: {self._fallback_due_to_premium}", "INFO")
            self.apply_theme(self._fallback_due_to_premium, persist=True)
            self._fallback_due_to_premium = None
        
        # Обновляем список доступных тем в UI
        if hasattr(self.widget, 'theme_handler'):
            try:
                self.widget.theme_handler.update_available_themes()
            except Exception as e:
                log(f"Ошибка обновления списка тем: {e}", "DEBUG")

    def _on_premium_check_error(self, error: str):
        """Обработчик ошибки асинхронной проверки"""
        log(f"Ошибка асинхронной проверки премиума: {error}", "❌ ERROR")
        
        # Устанавливаем кеш с негативным результатом
        self._premium_cache = (False, f"Ошибка: {error}", None)
        self._cache_time = time.time()

    def reapply_saved_theme_if_premium(self):
        """Восстанавливает премиум-тему после инициализации DonateChecker"""
        # Запускаем асинхронную проверку
        self._start_async_premium_check()

    def get_available_themes(self):
        """Возвращает список доступных тем с учетом статуса подписки"""
        themes = []
        
        # Используем кешированный результат
        is_premium = False
        if self._premium_cache:
            is_premium = self._premium_cache[0]
        
        for theme_info in self.themes:
            theme_name = theme_info['name']
            
            if theme_info['premium'] and not is_premium:
                # Разные метки для разных типов премиум тем
                if theme_name.startswith("AMOLED"):
                    themes.append(f"{theme_name} (AMOLED Premium)")
                elif theme_name == "Полностью черная":
                    themes.append(f"{theme_name} (Pure Black Premium)")
                else:
                    themes.append(f"{theme_name} (заблокировано)")
            else:
                themes.append(theme_name)
                
        return themes

    def get_clean_theme_name(self, display_name):
        """Извлекает чистое имя темы из отображаемого названия"""
        clean_name = display_name
        suffixes = [" (заблокировано)", " (AMOLED Premium)", " (Pure Black Premium)"]
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, "")
        return clean_name

    def _is_amoled_theme(self, theme_name: str) -> bool:
        """Проверяет, является ли тема AMOLED"""
        clean_name = self.get_clean_theme_name(theme_name)
        theme_info = THEMES.get(clean_name, {})
        return (clean_name.startswith("AMOLED") or 
                theme_info.get("amoled", False))

    def _is_pure_black_theme(self, theme_name: str) -> bool:
        """Проверяет, является ли тема полностью черной"""
        clean_name = self.get_clean_theme_name(theme_name)
        theme_info = THEMES.get(clean_name, {})
        return (clean_name == "Полностью черная" or 
                theme_info.get("pure_black", False))

    def apply_theme(self, theme_name: str | None = None, *, persist: bool = True) -> tuple[bool, str]:
        """Применяет тему с поддержкой всех специальных тем"""
        import qt_material

        if theme_name is None:
            theme_name = self.current_theme

        clean = self.get_clean_theme_name(theme_name)

        # проверка премиум для всех премиум тем (используем кеш)
        if self._is_premium_theme(clean):
            # Проверяем кешированный результат
            is_available = False
            if self._premium_cache:
                is_available = self._premium_cache[0]
            
            if not is_available:
                theme_type = self._get_theme_type_name(clean)
                QMessageBox.information(
                    self.widget, f"{theme_type}",
                    f"{theme_type} «{clean}» доступна только для подписчиков Zapret Premium."
                )
                # Запускаем асинхронную проверку на случай если кеш устарел
                self._start_async_premium_check()
                return False, "need premium"

        try:
            info = THEMES[clean]
            
            # Применяем базовую тему
            qt_material.apply_stylesheet(self.app, theme=info["file"])
            
            # Применяем специальные стили в зависимости от типа темы
            if self._is_pure_black_theme(clean):
                current_style = self.app.styleSheet()
                pure_black_style = current_style + "\n" + PURE_BLACK_OVERRIDE_STYLE
                self.app.setStyleSheet(pure_black_style)
                self.apply_pure_black_enhancements()
                log(f"Применена полностью черная тема: {clean}", "INFO")
                
            elif self._is_amoled_theme(clean):
                current_style = self.app.styleSheet()
                amoled_style = current_style + "\n" + AMOLED_OVERRIDE_STYLE
                self.app.setStyleSheet(amoled_style)
                self.apply_amoled_enhancements()
                log(f"Применена AMOLED тема: {clean}", "INFO")

            # остальная логика применения темы...
            self.status_label.setStyleSheet(
                f"color: {info['status_color']}; font-size: 9pt;"
            )

            # Переопределяем ВСЕ кнопки для полностью черной темы
            if self._is_pure_black_theme(clean):
                self._apply_pure_black_button_colors()
                self._apply_pure_black_label_colors()
            else:
                self._apply_normal_button_colors(info)
                self._apply_normal_label_colors(info)

            # Обновление заголовка (асинхронно если нужно)
            self._update_title_async(clean)

            # Специальный фон только для РКН Тян
            if clean == "РКН Тян":
                QTimer.singleShot(500, self.apply_rkn_background)
            else:
                self.widget.setAutoFillBackground(False)

            if persist:
                set_selected_theme(clean)
            self.current_theme = clean
            return True, "ok"

        except Exception as e:
            log(f"Theme error: {e}", "❌ ERROR")
            return False, str(e)

    def _update_title_async(self, current_theme):
        """Асинхронно обновляет заголовок окна"""
        try:
            # Используем кешированный результат если есть
            if self._premium_cache and hasattr(self.widget, "update_title_with_subscription_status"):
                is_premium, message, days = self._premium_cache
                self.widget.update_title_with_subscription_status(is_premium, current_theme, days)
            else:
                # Показываем FREE статус и запускаем асинхронную проверку
                if hasattr(self.widget, "update_title_with_subscription_status"):
                    self.widget.update_title_with_subscription_status(False, current_theme, None)
                # Запускаем асинхронную проверку
                self._start_async_premium_check()
                
        except Exception as e:
            log(f"Ошибка обновления заголовка: {e}", "❌ ERROR")

    # Остальные методы остаются без изменений...
    def _apply_pure_black_button_colors(self):
        """Применяет цвета кнопок для полностью черной темы"""
        try:
            # Для полностью черной темы все кнопки становятся темно-серыми с белым текстом
            pure_black_button_color = "32, 32, 32"  # Очень темно-серый
            pure_black_special_color = "64, 64, 64"  # Чуть светлее для accent кнопок
            
            # Стиль для обычных кнопок в черной теме
            pure_black_button_style = f"""
            QPushButton {{
                border: 1px solid #333333;
                background-color: rgb({pure_black_button_color});
                color: #ffffff;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 10pt;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: rgb({pure_black_special_color});
                border: 1px solid #555555;
            }}
            QPushButton:pressed {{
                background-color: rgb(16, 16, 16);
                border: 1px solid #777777;
            }}
            """
            
            # Стиль для accent кнопок (start, stop и т.д.)
            pure_black_accent_style = f"""
            QPushButton {{
                border: 1px solid #444444;
                background-color: rgb({pure_black_special_color});
                color: #ffffff;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 10pt;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: rgb(96, 96, 96);
                border: 1px solid #666666;
            }}
            QPushButton:pressed {{
                background-color: rgb(16, 16, 16);
                border: 1px solid #888888;
            }}
            """

            # Применяем стили ко всем кнопкам
            buttons_to_style = []
            
            # Обычные кнопки (themed_buttons)
            if hasattr(self.widget, "themed_buttons"):
                for btn in self.widget.themed_buttons:
                    btn.setStyleSheet(pure_black_button_style)
                    btn._bgcolor = pure_black_button_color
                    buttons_to_style.append(("themed", btn))

            # Специальные кнопки с accent цветом
            special_buttons = [
                'start_btn', 'stop_btn', 'autostart_enable_btn', 'autostart_disable_btn',
                'subscription_btn', 'proxy_button', 'update_check_btn'
            ]
            
            for btn_name in special_buttons:
                if hasattr(self.widget, btn_name):
                    btn = getattr(self.widget, btn_name)
                    btn.setStyleSheet(pure_black_accent_style)
                    btn._bgcolor = pure_black_special_color
                    buttons_to_style.append(("special", btn))

            log(f"Применены цвета полностью черной темы к {len(buttons_to_style)} кнопкам", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при применении цветов полностью черной темы: {e}", "❌ ERROR")

    def _apply_normal_button_colors(self, theme_info):
        """Применяет обычные цвета кнопок для всех тем кроме полностью черной"""
        try:
            # Обычные themed кнопки
            if hasattr(self.widget, "themed_buttons"):
                btn_color = theme_info.get("button_color", "0, 119, 255")
                for btn in self.widget.themed_buttons:
                    if self._is_pure_black_theme(self.current_theme):
                        special_style = self._get_pure_black_button_style(btn_color)
                        btn.setStyleSheet(special_style)
                    else:
                        btn.setStyleSheet(BUTTON_STYLE.format(btn_color))
                    btn._bgcolor = btn_color

            # Специальные кнопки с их оригинальными цветами
            special_button_colors = {
                'start_btn': "54, 153, 70",
                'autostart_enable_btn': "54, 153, 70", 
                'stop_btn': "255, 93, 174",
                'autostart_disable_btn': "255, 93, 174",
                'subscription_btn': "224, 132, 0",
                'update_check_btn': "38, 38, 38"
            }
            
            for btn_name, color in special_button_colors.items():
                if hasattr(self.widget, btn_name):
                    btn = getattr(self.widget, btn_name)
                    btn.setStyleSheet(BUTTON_STYLE.format(color))
                    btn._bgcolor = color

            # Обновляем состояние proxy кнопки
            if hasattr(self.widget, 'update_proxy_button_state'):
                self.widget.update_proxy_button_state()
                
        except Exception as e:
            log(f"Ошибка при применении обычных цветов кнопок: {e}", "❌ ERROR")

    def _apply_pure_black_label_colors(self):
        """Применяет белые цвета для текстовых меток в полностью черной теме"""
        try:
            white_color = "#ffffff"
            
            if hasattr(self.widget, "themed_labels"):
                for lbl in self.widget.themed_labels:
                    current_style = lbl.styleSheet()
                    new_style = self._update_color_in_style(current_style, white_color)
                    lbl.setStyleSheet(new_style)
                    
            log(f"Применены белые цвета к {len(getattr(self.widget, 'themed_labels', []))} меткам", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при применении белых цветов меток: {e}", "❌ ERROR")

    def _apply_normal_label_colors(self, theme_info):
        """Применяет обычные цвета для текстовых меток"""
        try:
            if hasattr(self.widget, "themed_labels"):
                lbl_color = theme_info.get("button_color", "0, 119, 255")
                if "," in lbl_color:
                    r, g, b = [int(x) for x in lbl_color.split(",")]
                    lbl_color = f"#{r:02x}{g:02x}{b:02x}"
                for lbl in self.widget.themed_labels:
                    cur = lbl.styleSheet()
                    lbl.setStyleSheet(self._update_color_in_style(cur, lbl_color))
                    
        except Exception as e:
            log(f"Ошибка при применении обычных цветов меток: {e}", "❌ ERROR")

    def _get_theme_type_name(self, theme_name: str) -> str:
        """Возвращает красивое название типа темы"""
        if theme_name.startswith("AMOLED"):
            return "AMOLED тема"
        elif theme_name == "Полностью черная":
            return "Pure Black тема"
        elif theme_name == "РКН Тян":
            return "Премиум-тема"
        else:
            return "Премиум-тема"

    def _get_pure_black_button_style(self, color: str) -> str:
        """Возвращает специальный стиль кнопок для полностью черной темы"""
        return f"""
        QPushButton {{
            border: 1px solid #333333;
            background-color: rgb(32, 32, 32);
            color: #ffffff;
            border-radius: 6px;
            padding: 10px;
            font-weight: bold;
            font-size: 10pt;
            min-height: 35px;
        }}
        QPushButton:hover {{
            background-color: rgb(64, 64, 64);
            border: 1px solid #555555;
        }}
        QPushButton:pressed {{
            background-color: rgb(16, 16, 16);
            border: 1px solid #777777;
        }}
        """

    def apply_pure_black_enhancements(self):
        """Применяет дополнительные улучшения для полностью черной темы"""
        try:
            additional_style = """
            QFrame[frameShape="4"] {
                color: #1a1a1a;
            }
            
            QPushButton:focus {
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
            
            QComboBox:focus {
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
            
            QLabel[objectName="title_label"] {
                text-shadow: 0px 0px 5px rgba(255, 255, 255, 0.1);
            }
            """
            
            current_style = self.app.styleSheet()
            self.app.setStyleSheet(current_style + additional_style)
            
            log("Pure Black улучшения применены", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при применении Pure Black улучшений: {e}", "DEBUG")


    def apply_amoled_enhancements(self):
        """Применяет дополнительные улучшения для AMOLED тем"""
        try:
            additional_style = """
            /* Убираем все лишние рамки */
            QFrame {
                border: none;
            }
            
            /* Рамка только при наведении на кнопки */
            QPushButton:hover {
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            /* Убираем text-shadow который создает размытие */
            QLabel {
                text-shadow: none;
            }
            
            /* Фокус на комбобоксе */
            QComboBox:focus {
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            /* Только горизонтальные линии оставляем видимыми */
            QFrame[frameShape="4"] {
                color: #222222;
                max-height: 1px;
                border: none;
            }
            
            /* Убираем отступы где возможно */
            QWidget {
                outline: none;
            }
            
            /* Компактные отступы для контейнеров */
            QStackedWidget {
                margin: 0;
                padding: 0;
            }
            """
            
            current_style = self.app.styleSheet()
            self.app.setStyleSheet(current_style + additional_style)
            
            log("AMOLED улучшения применены", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при применении AMOLED улучшений: {e}", "DEBUG")

    def _update_color_in_style(self, current_style, new_color):
        """Обновляет цвет в существующем стиле"""
        import re
        if 'color:' in current_style:
            updated_style = re.sub(r'color:\s*[^;]+;', f'color: {new_color};', current_style)
        else:
            updated_style = current_style + f' color: {new_color};'
        return updated_style
    
    def apply_rkn_background(self):
        """Применяет фоновое изображение для темы РКН Тян"""
        try:
            import requests
            
            temp_dir = os.path.join(self.theme_folder, "rkn_tyan")
            os.makedirs(temp_dir, exist_ok=True)
            
            img_path = os.path.join(temp_dir, "rkn_background.jpg")
            
            if not os.path.exists(img_path):
                try:
                    self._set_status("Загрузка фонового изображения...")
                    img_url = "https://github.com/youtubediscord/src/releases/download/files/rkn_background.jpg"
                    
                    response = requests.get(img_url, stream=True, timeout=10)
                    if response.status_code == 200:
                        with open(img_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        self._set_status("Фоновое изображение загружено")
                except Exception as e:
                    print(f"Ошибка при загрузке фона: {str(e)}")
                    self._set_status("Ошибка загрузки фона")
            
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    palette = self.widget.palette()
                    brush = QBrush(pixmap.scaled(
                        self.widget.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    palette.setBrush(QPalette.ColorRole.Window, brush)
                    self.widget.setPalette(palette)
                    self.widget.setAutoFillBackground(True)
                    return True
                    
        except Exception as e:
            print(f"Ошибка при применении фона РКН Тян: {str(e)}")
        
        return False
    
    def _set_status(self, text):
        """Устанавливает текст статуса"""
        if self.status_label:
            self.status_label.setText(text)


class ThemeHandler:
    """Обработчик событий связанных с темами"""
    
    def __init__(self, theme_manager, app_window):
        self.theme_manager = theme_manager
        self.app_window = app_window
    
    def update_subscription_status_in_title(self):
        """Обновляет статус подписки в title_label"""
        try:
            # Проверяем наличие необходимых компонентов
            if not hasattr(self.app_window, 'donate_checker') or not self.app_window.donate_checker:
                log("donate_checker не инициализирован", "⚠ WARNING")
                return
            
            if not hasattr(self.app_window, 'theme_manager'):
                log("theme_manager не инициализирован", "⚠ WARNING")
                return

            # Используем кэшированные данные для быстрого обновления
            donate_checker = self.app_window.donate_checker
            is_premium, status_msg, days_remaining = donate_checker.check_subscription_status(use_cache=True)
            current_theme = self.theme_manager.current_theme
            
            # Получаем полную информацию о подписке
            sub_info = donate_checker.get_full_subscription_info()
            
            # Обновляем заголовок
            self.app_window.update_title_with_subscription_status(
                sub_info['is_premium'], 
                current_theme, 
                sub_info['days_remaining']
            )
            
            # Также обновляем текст кнопки подписки если нужно
            if hasattr(self.app_window, 'update_subscription_button_text'):
                self.app_window.update_subscription_button_text(
                    sub_info['is_premium'],
                    sub_info['days_remaining']
                )
            
            log(f"Заголовок обновлен для темы '{current_theme}'", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при обновлении статуса подписки: {e}", "❌ ERROR")
            # В случае ошибки показываем базовый заголовок
            try:
                self.app_window.update_title_with_subscription_status(False, None, 0, False)
            except:
                pass  # Игнорируем вторичные ошибки
    
    def change_theme(self, theme_name):
        """Обработчик изменения темы"""
        try:
            # Проверяем, не является ли тема заблокированной
            if any(suffix in theme_name for suffix in ["(заблокировано)", "(AMOLED Premium)", "(Pure Black Premium)"]):
                clean_theme_name = self.theme_manager.get_clean_theme_name(theme_name)
                
                # Показываем предупреждение о заблокированной теме
                success, message = self.theme_manager.apply_theme(clean_theme_name)
                
                if not success:
                    # Возвращаемся к текущей теме
                    available_themes = self.theme_manager.get_available_themes()
                    for theme in available_themes:
                        if self.theme_manager.get_clean_theme_name(theme) == self.theme_manager.current_theme:
                            self.app_window.theme_combo.blockSignals(True)
                            self.app_window.theme_combo.setCurrentText(theme)
                            self.app_window.theme_combo.blockSignals(False)
                            break
                    return
            
            # Применяем тему
            success, message = self.theme_manager.apply_theme(theme_name)
            
            if success:
                log(f"Тема изменена на: {theme_name}", level="INFO")
                self.app_window.set_status(f"Тема изменена: {theme_name}")
                
                # Обновляем стили комбо-бокса после смены темы
                QTimer.singleShot(50, self.update_theme_combo_styles)
                
                # Обновляем статус подписки с новой темой (асинхронно)
                QTimer.singleShot(100, self.update_subscription_status_in_title)
            else:
                log(f"Ошибка при изменении темы: {message}", level="❌ ERROR")
                self.app_window.set_status(f"Ошибка изменения темы: {message}")
                
        except Exception as e:
            log(f"Ошибка при обработке изменения темы: {e}", level="❌ ERROR")
            self.app_window.set_status(f"Ошибка: {e}")

    def update_theme_combo_styles(self):
        """Применяет стили к комбо-боксу тем для выделения заблокированных элементов"""
        if not hasattr(self.app_window, 'theme_combo'):
            log("theme_combo не найден в app_window", "DEBUG")
            return
        
        # Проверяем, используется ли полностью черная тема
        is_pure_black = False
        if hasattr(self.theme_manager, '_is_pure_black_theme'):
            current_theme = getattr(self.theme_manager, 'current_theme', '')
            is_pure_black = self.theme_manager._is_pure_black_theme(current_theme)
            
        if is_pure_black:
            # Стили для полностью черной темы
            style = f"""
            QComboBox {{
                {COMMON_STYLE}
                text-align: center;
                font-size: 10pt;
                padding: 5px;
                border: 1px solid #333333;
                border-radius: 4px;
                background-color: #000000;
                color: #ffffff;
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
                background-color: #000000;
            }}
            
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            
            QComboBox QAbstractItemView {{
                selection-background-color: #333333;
                selection-color: white;
                border: 1px solid #333333;
                background-color: #000000;
                color: #ffffff;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 8px;
                border-bottom: 1px solid #333333;
                color: #ffffff;
            }}
            
            QComboBox QAbstractItemView::item:contains("заблокировано") {{
                color: #888888;
                background-color: #1a1a1a;
                font-style: italic;
            }}
            
            QComboBox QAbstractItemView::item:contains("AMOLED Premium") {{
                color: #bb86fc;
                background-color: #1a1a1a;
                font-weight: bold;
                font-style: italic;
            }}
            
            QComboBox QAbstractItemView::item:contains("Pure Black Premium") {{
                color: #ffffff;
                background-color: #1a1a1a;
                font-weight: bold;
                font-style: italic;
            }}
            
            QComboBox QAbstractItemView::item:contains("Полностью черная") {{
                color: #ffffff;
                font-weight: bold;
            }}
            
            QComboBox QAbstractItemView::item:contains("заблокировано"):hover,
            QComboBox QAbstractItemView::item:contains("AMOLED Premium"):hover,
            QComboBox QAbstractItemView::item:contains("Pure Black Premium"):hover {{
                background-color: #333333;
                color: #ffffff;
            }}
            """
        else:
            # Обычные стили для других тем
            style = f"""
            QComboBox {{
                {COMMON_STYLE}
                text-align: center;
                font-size: 10pt;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            
            QComboBox QAbstractItemView {{
                selection-background-color: #007ACC;
                selection-color: white;
                border: 1px solid #ccc;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 8px;
                border-bottom: 1px solid #eee;
            }}
            
            QComboBox QAbstractItemView::item:contains("заблокировано") {{
                color: #888888;
                background-color: #f5f5f5;
                font-style: italic;
            }}
            
            QComboBox QAbstractItemView::item:contains("AMOLED Premium") {{
                color: #6a4c93;
                background-color: #f0f0f8;
                font-weight: bold;
                font-style: italic;
            }}
            
            QComboBox QAbstractItemView::item:contains("Pure Black Premium") {{
                color: #2c2c2c;
                background-color: #f8f8f8;
                font-weight: bold;
                font-style: italic;
            }}
            
            QComboBox QAbstractItemView::item:contains("заблокировано"):hover,
            QComboBox QAbstractItemView::item:contains("AMOLED Premium"):hover,
            QComboBox QAbstractItemView::item:contains("Pure Black Premium"):hover {{
                background-color: #e8e8e8;
                color: #666666;
            }}
            """
        
        try:
            self.app_window.theme_combo.setStyleSheet(style)
            log("Стили комбо-бокса тем применены", "DEBUG")
        except Exception as e:
            log(f"Ошибка применения стилей комбо-бокса: {e}", "❌ ERROR")

    def update_available_themes(self):
        """Обновляет список доступных тем в комбо-боксе"""
        if not hasattr(self.app_window, 'theme_combo'):
            return
            
        try:
            available_themes = self.theme_manager.get_available_themes()
            current_theme = self.app_window.theme_combo.currentText()
            
            # Временно отключаем сигналы
            self.app_window.theme_combo.blockSignals(True)
            
            # Обновляем список
            self.app_window.theme_combo.clear()
            self.app_window.theme_combo.addItems(available_themes)
            
            # Восстанавливаем выбор
            clean_current = self.theme_manager.get_clean_theme_name(current_theme)
            for theme in available_themes:
                clean_theme = self.theme_manager.get_clean_theme_name(theme)
                if clean_theme == clean_current:
                    self.app_window.theme_combo.setCurrentText(theme)
                    break
            else:
                # Если текущая тема недоступна, выбираем первую доступную
                if available_themes:
                    for theme in available_themes:
                        if "(заблокировано)" not in theme and "(Premium)" not in theme:
                            self.app_window.theme_combo.setCurrentText(theme)
                            break
                    else:
                        self.app_window.theme_combo.setCurrentText(available_themes[0])
            
            # Включаем сигналы обратно
            self.app_window.theme_combo.blockSignals(False)
            
            # Применяем стили
            self.update_theme_combo_styles()
            
            log("Список доступных тем обновлен", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка обновления списка тем: {e}", "❌ ERROR")