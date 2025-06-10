import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty
from PyQt6.QtGui import QPixmap, QPalette, QBrush, QPainter, QColor
from PyQt6.QtWidgets import QPushButton
from config.reg import reg, HKCU

# Константы
THEMES = {
    "Темная синяя": {"file": "dark_blue.xml", "status_color": "#ffffff", "button_color": "0, 125, 242"},
    "Темная бирюзовая": {"file": "dark_cyan.xml", "status_color": "#ffffff", "button_color": "14, 152, 211"},
    "Темная янтарная": {"file": "dark_amber.xml", "status_color": "#ffffff", "button_color": "224, 132, 0"},
    "Темная розовая": {"file": "dark_pink.xml", "status_color": "#ffffff", "button_color": "255, 93, 174"},
    "Светлая синяя": {"file": "light_blue.xml", "status_color": "#000000", "button_color": "25, 118, 210"},
    "Светлая бирюзовая": {"file": "light_cyan.xml", "status_color": "#000000", "button_color": "0, 172, 193"},
    "РКН Тян": {"file": "dark_blue.xml", "status_color": "#ffffff", "button_color": "63, 85, 182"},
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

def get_selected_theme(default: str | None = None) -> str | None:
    """Возвращает сохранённую тему или default"""
    return reg(r"Software\Zapret", "SelectedTheme") or default

def set_selected_theme(theme_name: str) -> bool:
    """Записывает строку SelectedTheme"""
    return reg(r"Software\Zapret", "SelectedTheme", theme_name)

def get_windows_theme() -> str:
    """Читает системную тему Windows"""
    val = reg(
        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        "AppsUseLightTheme",
        root=HKCU
    )
    return "light" if val == 1 else "dark"

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
    
    def __init__(self, app, widget, status_label, bin_folder):
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
        """Применяет указанную тему"""
        if theme_name is None:
            theme_name = self.current_theme
        
        try:
            import qt_material
            theme_info = THEMES[theme_name]
            
            qt_material.apply_stylesheet(self.app, theme=theme_info["file"])
            
            # Обновляем цвет текста статуса
            self.status_label.setStyleSheet(f"color: {theme_info['status_color']}; font-size: 9pt;")

            # Обновляем цвет синих кнопок
            if hasattr(self.widget, 'themed_buttons'):
                button_color = theme_info.get("button_color", "0, 119, 255")
                for button in self.widget.themed_buttons:
                    button.setStyleSheet(BUTTON_STYLE.format(button_color))
                    button._bgcolor = button_color  # Обновляем внутренний цвет для ripple

            # Если выбрана тема РКН Тян, применяем фоновое изображение
            if theme_name == "РКН Тян":
                QTimer.singleShot(500, self.apply_rkn_background)
            else:
                self.widget.setAutoFillBackground(False)
            
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
            
            temp_dir = os.path.join(self.bin_folder, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            img_path = os.path.join(temp_dir, "rkn_background.jpg")
            
            if not os.path.exists(img_path):
                try:
                    self._set_status("Загрузка фонового изображения...")
                    img_url = "https://gitflic.ru/project/main1234/main1234/blob/raw?file=download.jpg"
                    
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
