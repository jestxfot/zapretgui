import winreg
from PyQt5.QtWidgets import QMessageBox

def get_discord_restart_setting():
    """Получает настройку автоматического перезапуска Discord из реестра"""
    try:
        registry = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Zapret"
        )
        value, _ = winreg.QueryValueEx(registry, "AutoRestartDiscord")
        winreg.CloseKey(registry)
        return bool(value)
    except:
        # По умолчанию включено
        return True
    
def set_discord_restart_setting(enabled):
    """Сохраняет настройку автоматического перезапуска Discord в реестр"""
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
        winreg.SetValueEx(registry, "AutoRestartDiscord", 0, winreg.REG_DWORD, int(enabled))
        winreg.CloseKey(registry)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении настройки: {str(e)}")
        return False

def toggle_discord_restart(parent, status_callback=None, discord_auto_restart_attr_name='discord_auto_restart'):
    """
    Переключает настройку автоматического перезапуска Discord
    
    Args:
        parent: Родительское окно для диалогов
        status_callback: Функция обратного вызова для отображения статуса
        discord_auto_restart_attr_name: Имя атрибута в родительском объекте для хранения настройки
    """
    current_setting = get_discord_restart_setting()
    
    # Показываем диалог подтверждения
    if current_setting:
        # Если сейчас включено, предлагаем выключить
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Отключение автоперезапуска Discord")
        msg.setText("Вы действительно хотите отключить автоматический перезапуск Discord?")
        
        msg.setInformativeText(
            "Если вы отключите эту функцию, вам придется самостоятельно перезапускать "
            "Discord после смены стратегии обхода блокировок.\n\n"
            "Это может привести к проблемам с подключением к голосовым каналам и "
            "нестабильной работе Discord.\n\n"
            "Вы понимаете последствия своих действий?"
        )
        
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        choice = msg.exec_()
        
        if choice == QMessageBox.Yes:
            # Отключаем автоперезапуск
            set_discord_restart_setting(False)
            
            # Обновляем настройку в родительском объекте
            if hasattr(parent, discord_auto_restart_attr_name):
                setattr(parent, discord_auto_restart_attr_name, False)
            
            # Выводим статус
            if status_callback:
                status_callback("Автоматический перезапуск Discord отключен")
            
            QMessageBox.information(parent, "Настройка изменена", 
                                "Автоматический перезапуск Discord отключен.\n\n"
                                "Теперь вам нужно будет самостоятельно перезапускать Discord "
                                "после смены стратегии обхода блокировок.")
    else:
        # Включаем автоперезапуск (без дополнительного подтверждения)
        set_discord_restart_setting(True)
        
        # Обновляем настройку в родительском объекте
        if hasattr(parent, discord_auto_restart_attr_name):
            setattr(parent, discord_auto_restart_attr_name, True)
        
        # Выводим статус
        if status_callback:
            status_callback("Автоматический перезапуск Discord включен")
        
        QMessageBox.information(parent, "Настройка изменена", 
                            "Автоматический перезапуск Discord снова включен.")
                            
    return True