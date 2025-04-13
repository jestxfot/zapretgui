import os
import winreg
from PyQt5.QtCore import Qt, QTimer,  QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QPixmap, QPalette, QBrush
from PyQt5.QtWidgets import QPushButton

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


def get_selected_theme():
    """Получает сохраненную тему из реестра"""
    try:
        registry = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Zapret"
        )
        value, _ = winreg.QueryValueEx(registry, "SelectedTheme")
        winreg.CloseKey(registry)
        return value
    except:
        # По умолчанию возвращаем None, что означает "использовать системную тему"
        return None
    
def set_selected_theme(theme_name):
    """Сохраняет выбранную тему в реестр"""
    try:
        # Пытаемся открыть ключ, если его нет - создаем
        try:
            registry = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Zapret",
                0, 
                winreg.KEY_WRITE
            )
        except:
            registry = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Zapret"
            )
        
        # Записываем значение
        winreg.SetValueEx(registry, "SelectedTheme", 0, winreg.REG_SZ, theme_name)
        winreg.CloseKey(registry)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении темы: {str(e)}")
        return False

def get_windows_theme():
    """Определяет текущую тему Windows (светлая/темная)"""
    try:
        registry = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(registry, "AppsUseLightTheme")
        winreg.CloseKey(registry)
        return "light" if value == 1 else "dark"
    except:
        return "dark"  # По умолчанию темная тема

class ThemeManager:
    """Класс для управления темами приложения"""
    
    def __init__(self, app, widget, status_label, author_label, bin_folder, author_url, bol_van_url, support_label):
        """
        Инициализирует менеджер тем
        
        Параметры:
        - app: экземпляр QApplication
        - widget: виджет, к которому применяется тема
        - status_label: метка статуса для вывода сообщений
        - author_label: метка автора для обновления стиля
        - bin_folder: путь к папке с бинарными файлами
        - author_url: URL автора для отображения в ссылке
        """
        self.app = app
        self.widget = widget
        self.status_label = status_label
        self.author_label = author_label
        self.bin_folder = bin_folder
        self.author_url = author_url
        self.bol_van_url = bol_van_url
        self.support_label = support_label
        
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
            from qt_material import apply_stylesheet
            
            # Получаем информацию о теме
            theme_info = THEMES[theme_name]
            
            # Применяем тему
            apply_stylesheet(self.app, theme=theme_info["file"])
            
            # Обновляем цвет текста статуса
            self.status_label.setStyleSheet(f"color: {theme_info['status_color']};")
            
            # Обновляем цвет ссылки автора
            status_color = theme_info['status_color']
            self.bol_van_url.setStyleSheet(f"""
                color: {status_color}; 
                opacity: 0.6; 
                font-size: 9pt;
            """)
            self.author_label.setStyleSheet(f"""
                color: {status_color}; 
                opacity: 0.6; 
                font-size: 9pt;
            """)
            self.support_label.setStyleSheet(f"""
                color: {status_color}; 
                opacity: 0.6; 
                font-size: 9pt;
            """)

            self.bol_van_url.setText(f'Автор Zapret: <a href="https://github.com/bol-van" style="color:{status_color}">github.com/bol-van</a>')
            self.author_label.setText(f'Автор GUI: <a href="https://t.me/bypassblock" style="color:{status_color}">t.me/bypassblock</a>')

            self.support_label.setText(f'Поддержка: <a href="{self.support_label}" style="color:{status_color}">t.me/youtubenotwork</a><br>или на почту <a href="mail:fuckyourkn@yandex.ru"  style="color:{status_color}">fuckyourkn@yandex.ru</a>')

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
        self._ripple_animation.setEasingCurve(QEasingCurve.OutQuad)

        self._fade_animation = QPropertyAnimation(self, b"rippleOpacity", self)
        self._fade_animation.setDuration(300)
        self._fade_animation.setStartValue(0.5)
        self._fade_animation.setEndValue(0)

    from PyQt5.QtCore import pyqtProperty
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
            from PyQt5.QtGui import QPainter, QColor
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setOpacity(self._ripple_opacity)
            
            painter.setBrush(QColor(255, 255, 255, 60))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self._ripple_pos, self._ripple_radius, self._ripple_radius)