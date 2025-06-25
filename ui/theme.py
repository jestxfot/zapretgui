import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty
from PyQt6.QtGui import QPixmap, QPalette, QBrush, QPainter, QColor
from PyQt6.QtWidgets import QPushButton
from config import reg, HKCU
from log import log

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

    # ------------------------------------------------------------------
    def __init__(self, app, widget, status_label, theme_folder,
                 donate_checker=None):
        self.app            = app
        self.widget         = widget
        self.status_label   = status_label
        self.theme_folder     = theme_folder
        self.donate_checker = donate_checker
        self._fallback_due_to_premium: str | None = None  # ← запомним, если был откат

        # ---------- список тем (делаем один раз!) ---------------------
        self.themes = [
            {'name': name, 'premium': name == "РКН Тян"}
            for name in THEMES
        ]

        # ---------- выбираем стартовую тему ---------------------------
        saved = get_selected_theme()
        if saved and saved in THEMES:
            if saved == "РКН Тян" and not self._is_premium_available():
                log("Премиум недоступен; временно «Тёмная синяя»", "INFO")
                self.current_theme = "Темная синяя"
                self._fallback_due_to_premium = saved  # запомнили «РКН Тян»
            else:
                self.current_theme = saved
        else:
            self.current_theme = (
                "Светлая синяя" if get_windows_theme() == "light"
                else "Темная синяя"
            )

        # применяем тему, НО БЕЗ записи в настройки
        self.apply_theme(self.current_theme, persist=False)

    # -------------------------------------------------------------------------
    # вспомогательные методы
    # -------------------------------------------------------------------------
    def _is_premium_available(self) -> bool:
        if not self.donate_checker:
            return False
        try:
            is_prem, *_ = self.donate_checker.check_subscription_status()
            return is_prem
        except Exception as e:
            log(f"Ошибка проверки подписки: {e}", "❌ ERROR")
            return False
        
    def reapply_saved_theme_if_premium(self):
        """
        Вызывайте после инициализации DonateChecker.
        Восстанавливает премиум-тему «РКН Тян», если подписка подтверждена.
        """
        if (not self._fallback_due_to_premium or      # не было отката
                not self._is_premium_available()):    # премиум всё ещё нет
            return

        ok, msg = self.apply_theme(self._fallback_due_to_premium,
                                   persist=True)      # Сохраняем выбор!
        if ok:
            log(f"Премиум-тема «{self._fallback_due_to_premium}» восстановлена",
                "INFO")
            self._fallback_due_to_premium = None
        else:
            log(f"Не удалось восстановить тему: {msg}", "⚠ WARNING")

    def get_available_themes(self):
        """Возвращает список доступных тем с учетом статуса подписки"""
        themes = []
        
        # Проверяем статус подписки, но безопасно
        is_premium = False
        try:
            if (self.donate_checker and 
                hasattr(self.donate_checker, '__class__') and 
                self.donate_checker.__class__.__name__ != 'DummyChecker'):
                is_premium, _, _ = self.donate_checker.check_subscription_status()
        except Exception as e:
            log(f"Ошибка проверки подписки в ThemeManager: {e}", "DEBUG")
        
        for theme_info in self.themes:
            theme_name = theme_info['name']
            
            if theme_info['premium'] and not is_premium:
                # Премиум тема недоступна
                themes.append(f"{theme_name} (заблокировано)")
            else:
                # Обычная тема или доступная премиум
                themes.append(theme_name)
                
        return themes
    
    def get_clean_theme_name(self, display_name):
        """Извлекает чистое имя темы из отображаемого названия"""
        if " (заблокировано)" in display_name:
            return display_name.replace(" (заблокировано)", "")
        return display_name

    def apply_theme(self, theme_name: str | None = None, *, persist: bool = True) -> tuple[bool, str]:
        """
        Применяет тему.
        persist=False  – только визуально, без записи в настройки.
        """
        from PyQt6.QtWidgets import QMessageBox
        import qt_material

        if theme_name is None:
            theme_name = self.current_theme

        clean = self.get_clean_theme_name(theme_name)

        # --- премиум-проверка --------------------------------------
        if clean == "РКН Тян" and not self._is_premium_available():
            QMessageBox.information(
                self.widget, "Премиум-тема",
                "Тема «РКН Тян» доступна только для подписчиков Zapret Premium."
            )
            return False, "need premium"

        try:
            info = THEMES[clean]
            qt_material.apply_stylesheet(self.app, theme=info["file"])

            # обновляем цвета, кнопки, лейблы … (как у вас было)
            self.status_label.setStyleSheet(
                f"color: {info['status_color']}; font-size: 9pt;"
            )

            # цвет «синих» кнопок
            if hasattr(self.widget, "themed_buttons"):
                btn_color = info.get("button_color", "0, 119, 255")
                for btn in self.widget.themed_buttons:
                    btn.setStyleSheet(BUTTON_STYLE.format(btn_color))
                    btn._bgcolor = btn_color

            # цвет меток
            if hasattr(self.widget, "themed_labels"):
                lbl_color = info.get("button_color", "0, 119, 255")
                if "," in lbl_color:                                   # RGB→HEX
                    r, g, b = [int(x) for x in lbl_color.split(",")]
                    lbl_color = f"#{r:02x}{g:02x}{b:02x}"
                for lbl in self.widget.themed_labels:
                    cur = lbl.styleSheet()
                    lbl.setStyleSheet(self._update_color_in_style(cur, lbl_color))

            # обновляем заголовок (если есть донат-чекер)
            if (hasattr(self.widget, "update_title_with_subscription_status")
                    and hasattr(self.widget, "donate_checker")):
                try:
                    is_prem, msg, days = self.widget.donate_checker.check_subscription_status()
                    self.widget.update_title_with_subscription_status(is_prem, clean, days)
                except Exception as e:
                    log(f"Ошибка обновления статуса подписки: {e}", "❌ ERROR")
                    self.widget.update_title_with_subscription_status(False, clean, None)

            # фон для РКН-тян
            if clean == "РКН Тян":
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, self.apply_rkn_background)
            else:
                self.widget.setAutoFillBackground(False)

            if persist:
                set_selected_theme(clean)           # ← запись ТОЛЬКО если persist
            self.current_theme = clean
            return True, "ok"

        except Exception as e:
            log(f"Theme error: {e}", "❌ ERROR")
            return False, str(e)

    def _update_color_in_style(self, current_style, new_color):
        """Обновляет цвет в существующем стиле"""
        import re
        # Заменяем существующий color или добавляем новый
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
                    img_url = "https://zapretdpi.ru/rkn_background.jpg"
                    
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
