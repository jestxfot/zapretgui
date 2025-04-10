import os
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QStyle, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QEvent

class SystemTrayManager:
    """Управление иконкой в системном трее и соответствующим функционалом"""
    
    def __init__(self, parent, icon_path, app_version):
        """
        Инициализация менеджера системного трея
        
        Args:
            parent: родительский виджет (главное окно)
            icon_path: путь к файлу иконки
            app_version: версия приложения для отображения в подсказке
        """
        self.parent = parent
        self.tray_icon = QSystemTrayIcon(parent)
        self.app_version = app_version
        self._shown_tray_message = False
        
        # Устанавливаем иконку
        self.set_icon(icon_path)
        
        # Создаем контекстное меню
        self.setup_menu()
        
        # Подключаем сигнал клика
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # Показываем иконку
        self.tray_icon.show()
        
    def set_icon(self, icon_path):
        """Устанавливает иконку для трея"""
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
            self.tray_icon.setToolTip(f"Zapret v{self.app_version}")
        else:
            # Если иконка не найдена, используем стандартную
            self.tray_icon.setIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
            self.tray_icon.setToolTip(f"Zapret v{self.app_version} (иконка не найдена)")
            print(f"ОШИБКА: Файл иконки {icon_path} не найден")
            
    def setup_menu(self):
        """Настройка контекстного меню трея"""
        tray_menu = QMenu()
        
        # Добавляем опцию показа окна
        show_action = QAction("Показать", self.parent)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        # Добавляем разделитель
        tray_menu.addSeparator()
        
        # Добавляем опцию выхода
        exit_action = QAction("Выход", self.parent)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)
        
        # Устанавливаем меню для иконки
        self.tray_icon.setContextMenu(tray_menu)
        
    def on_tray_icon_activated(self, reason):
        """Обработчик активации иконки в трее"""
        if reason == QSystemTrayIcon.Trigger:  # Клик левой кнопкой мыши
            # Переключаем видимость окна
            if self.parent.isVisible():
                self.parent.hide()
            else:
                self.show_window()
    
    def show_window(self):
        """Показывает окно приложения"""
        self.parent.showNormal()
        self.parent.activateWindow()
        self.parent.raise_()  # Поднимаем окно поверх других окон
    
    def exit_app(self):
        """Полностью закрывает приложение"""
        # Отключаем обработчик закрытия окна для предотвращения сворачивания в трей
        self.parent._allow_close = True
        
        # Скрываем иконку трея
        self.tray_icon.hide()
        
        # Завершаем приложение
        QApplication.quit()
    
    def show_message(self, title, message, icon=QSystemTrayIcon.Information, duration=3000):
        """Показывает всплывающее сообщение от иконки в трее"""
        self.tray_icon.showMessage(title, message, icon, duration)
    
    def handle_window_close(self, event):
        """Обрабатывает закрытие окна"""
        if not hasattr(self.parent, '_allow_close') or not self.parent._allow_close:
            # Показываем уведомление при первом сворачивании
            if not self._shown_tray_message:
                self.show_message(
                    "Zapret продолжает работать",
                    "Программа свернута в трей и продолжает работать в фоновом режиме. "
                    "Кликните на иконку в трее для восстановления окна."
                )
                self._shown_tray_message = True
            
            # Скрываем окно и игнорируем событие закрытия
            self.parent.hide()
            event.ignore()
        else:
            # Если разрешено закрытие, передаем событие дальше
            event.accept()
    
    def handle_window_minimize(self, event):
        """Обрабатывает сворачивание окна"""
        if event.type() == QEvent.WindowStateChange and self.parent.isMinimized():
            # При сворачивании скрываем окно
            event.ignore()
            self.parent.hide()
            
            # Показываем уведомление при первом сворачивании
            if not self._shown_tray_message:
                self.show_message(
                    "Zapret продолжает работать",
                    "Программа свернута в трей и продолжает работать в фоновом режиме. "
                    "Кликните на иконку в трее для восстановления окна."
                )
                self._shown_tray_message = True
            
            return True
        return False