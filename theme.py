import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QPixmap, QPalette, QBrush
from PyQt6.QtWidgets import QPushButton
from reg import reg, HKCU

# Константы
THEMES = {
    "Темная синяя": {"file": "dark_blue.xml", "status_color": "#ffffff"},
    "Темная бирюзовая": {"file": "dark_cyan.xml", "status_color": "#ffffff"},
    "Темная янтарная": {"file": "dark_amber.xml", "status_color": "#ffffff"},
    "Темная розовая": {"file": "dark_pink.xml", "status_color": "#ffffff"},
    "Светлая синяя": {"file": "light_blue.xml", "status_color": "#000000"},
    "Светлая бирюзовая": {"file": "light_cyan.xml", "status_color": "#000000"},
    "РКН Тян": {"file": "dark_blue.xml", "status_color": "#ffffff"},  # Используем dark_blue как основу
}

BUTTON_STYLE = """
QPushButton {{
    border: none;
    background-color: rgb({0});
    color: #fff;
    border-radius: 4px;
    padding: 8px;
}}
QPushButton:hover {{
    background-color: rgb({0});
}}
"""

COMMON_STYLE = "color:rgb(0, 119, 255); font-weight: bold;"
BUTTON_HEIGHT = 10

STYLE_SHEET = """
    @keyframes ripple {
        0% {
            transform: scale(0, 0);
            opacity: 0.5;
        }
        100% {
            transform: scale(40, 40);
            opacity: 0;
        }
    }
"""


def get_selected_theme(default: str | None = None) -> str | None:
    """
    Возвращает сохранённую тему или default (None означает «системная тема»).
    """
    return reg(r"Software\Zapret", "SelectedTheme") or default


def set_selected_theme(theme_name: str) -> bool:
    """
    Записывает строку SelectedTheme.
    """
    return reg(r"Software\Zapret", "SelectedTheme", theme_name)


# ------------------------------------------------------------------
# 2. системная тема Windows
#    HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize
#    параметр AppsUseLightTheme = 0/1
# ------------------------------------------------------------------
def get_windows_theme() -> str:
    """
    Читает системную тему Windows: 'light' или 'dark'.
    Если ключа нет – по-умолчанию 'dark'.
    """
    val = reg(
        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        "AppsUseLightTheme",
        root=HKCU
    )
    return "light" if val == 1 else "dark"

class ThemeManager:
    """Класс для управления темами приложения"""
    
    def __init__(self, app, widget, status_label, bin_folder):
        """
        Инициализирует менеджер тем
        
        Параметры:
        - app: экземпляр QApplication
        - widget: виджет, к которому применяется тема
        - status_label: метка статуса для вывода сообщений
        - bin_folder: путь к папке с бинарными файлами
        """
        self.app = app
        self.widget = widget
        self.status_label = status_label
        self.bin_folder = bin_folder
        
        # Загружаем сохраненную тему или используем системную
        saved_theme = get_selected_theme()
        if saved_theme and saved_theme in THEMES:
            self.current_theme = saved_theme
        else:
            windows_theme = get_windows_theme()
            self.current_theme = "Светлая синяя" if windows_theme == "light" else "Темная синяя"
    
    def apply_theme(self, theme_name=None):
        """Применяет указанную тему или текущую, если тема не указана"""
        if theme_name is None:
            theme_name = self.current_theme
        
        try:
            import qt_material
            # Получаем информацию о теме
            theme_info = THEMES[theme_name]
            
            # Применяем тему
            qt_material.apply_stylesheet(self.app, theme=theme_info["file"])
            
            # Обновляем цвет текста статуса
            self.status_label.setStyleSheet(f"color: {theme_info['status_color']};")

            # Если выбрана тема РКН Тян, применяем фоновое изображение
            if theme_name == "РКН Тян":
                QTimer.singleShot(500, self.apply_rkn_background)
            else:
                # Сбрасываем фоновое изображение если оно было
                self.widget.setAutoFillBackground(False)
            
            # Сохраняем тему в реестр
            set_selected_theme(theme_name)
            self.current_theme = theme_name
            
            return True, ""
        except Exception as e:
            error_msg = f"Ошибка при применении темы: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    def apply_rkn_background(self):
        """Применяет фоновое изображение для темы РКН Тян"""
        try:
            import requests
            
            # Путь к папке для временных файлов
            temp_dir = os.path.join(self.bin_folder, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Путь к сохраняемому изображению
            img_path = os.path.join(temp_dir, "rkn_background.jpg")
            
            # Скачиваем изображение, если его нет
            if not os.path.exists(img_path):
                try:
                    self._set_status("Загрузка фонового изображения...")
                    img_url = "https://gitflic.ru/project/main1234/main1234/blob/raw?file=download.jpg"
                    
                    response = requests.get(img_url, stream=True)
                    if response.status_code == 200:
                        with open(img_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        self._set_status("Фоновое изображение загружено")
                except Exception as e:
                    error_msg = f"Ошибка при загрузке фона: {str(e)}"
                    print(error_msg)
                    self._set_status(error_msg)
            
            # Применяем фоновое изображение
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # Создаем палитру и устанавливаем фон
                    palette = self.widget.palette()
                    brush = QBrush(pixmap.scaled(self.widget.width(), self.widget.height(), 
                                                Qt.KeepAspectRatioByExpanding, 
                                                Qt.SmoothTransformation))
                    palette.setBrush(QPalette.Window, brush)
                    self.widget.setPalette(palette)
                    self.widget.setAutoFillBackground(True)
                    print("Фон РКН Тян успешно применен")
                    self._set_status("Фон РКН Тян применен")
                    return True
                else:
                    error_msg = "Ошибка: фоновое изображение не загрузилось"
                    print(error_msg)
                    self._set_status(error_msg)
            else:
                error_msg = f"Ошибка: файл фона не найден: {img_path}"
                print(error_msg)
                self._set_status(error_msg)
        except Exception as e:
            error_msg = f"Ошибка при применении фона РКН Тян: {str(e)}"
            print(error_msg)
            self._set_status(error_msg)
        
        return False
    
    def _set_status(self, text):
        """Устанавливает текст статуса, если метка доступна"""
        if self.status_label:
            self.status_label.setText(text)

class RippleButton(QPushButton):
    def __init__(self, text, parent=None, color=""):
        self.manually_stopped = False  # Флаг для отслеживания намеренной остановки
        super().__init__(text, parent)
        self._ripple_pos = QPoint()
        self._ripple_radius = 0
        self._ripple_opacity = 0
        self._bgcolor = color
        
        # Настройка анимаций
        self._ripple_animation = QPropertyAnimation(self, b"rippleRadius", self)
        self._ripple_animation.setDuration(300)
        self._ripple_animation.setStartValue(0)
        self._ripple_animation.setEndValue(100)
        self._ripple_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._fade_animation = QPropertyAnimation(self, b"rippleOpacity", self)
        self._fade_animation.setDuration(300)
        self._fade_animation.setStartValue(0.5)
        self._fade_animation.setEndValue(0)

    from PyQt6.QtCore import pyqtProperty
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
        self._ripple_opacity = 0.5
        self._ripple_animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._fade_animation.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._ripple_radius > 0:
            from PyQt6.QtGui import QPainter, QColor
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setOpacity(self._ripple_opacity)
            
            painter.setBrush(QColor(255, 255, 255, 60))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                int(self._ripple_pos.x() - self._ripple_radius),
                int(self._ripple_pos.y() - self._ripple_radius),
                int(self._ripple_radius * 2),
                int(self._ripple_radius * 2)
            )

            painter.end()