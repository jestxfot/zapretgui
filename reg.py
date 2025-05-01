#reg.py
import winreg

def get_last_strategy():
    """Получает последнюю выбранную стратегию обхода из реестра"""
    try:
        registry = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Zapret"
        )
        value, _ = winreg.QueryValueEx(registry, "LastStrategy")
        winreg.CloseKey(registry)
        return value
    except:
        # По умолчанию возвращаем None, чтобы использовать первую стратегию из списка
        return "Оригинальная bol-van v2 (07.04.2025)"
    
def set_last_strategy(strategy_name):
    """Сохраняет последнюю выбранную стратегию обхода в реестр"""
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
        winreg.SetValueEx(registry, "LastStrategy", 0, winreg.REG_SZ, strategy_name)
        winreg.CloseKey(registry)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении стратегии: {str(e)}")
        return False