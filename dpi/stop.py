# dpi/stop.py
import subprocess
import time
import psutil, os
from utils import run_hidden
from typing import TYPE_CHECKING
from log import log

if TYPE_CHECKING:
    from main import LupiDPIApp

# Константы для скрытого запуска
CREATE_NO_WINDOW = 0x08000000

def stop_dpi(app: "LupiDPIApp"):
    """Останавливает процесс winws.exe напрямую"""
    try:
        log("======================== Stop DPI ========================", level="START")
        
        # Проверяем метод запуска
        from strategy_menu import get_strategy_launch_method
        launch_method = get_strategy_launch_method()
        
        if launch_method == "direct":
            # Используем новый метод остановки
            return stop_dpi_direct(app)
        else:
            # Используем старый метод через .bat
            return stop_dpi_bat(app)
            
    except Exception as e:
        log(f"Критическая ошибка в stop_dpi: {e}", level="❌ ERROR")
        app.set_status(f"Ошибка остановки: {e}")
        return False

def stop_dpi_direct(app: "LupiDPIApp"):
    """Останавливает DPI напрямую без .bat файлов"""
    try:
        # Проверяем, запущен ли процесс
        if not app.dpi_starter.check_process_running_wmi(silent=True):
            log("Процесс winws.exe не запущен", level="INFO")
            app.set_status("Zapret уже остановлен")
            app.update_ui(running=False)
            return True
        
        app.set_status("Останавливаю Zapret...")
        
        # 1. Останавливаем через StrategyRunner если он используется
        try:
            from strategy_menu.strategy_runner import get_strategy_runner
            runner = get_strategy_runner(app.dpi_starter.winws_exe)
            if runner.is_running():
                runner.stop()
                time.sleep(1)
        except:
            pass
        
        # 2. Убиваем все процессы winws.exe
        killed = False
        try:
            # Используем psutil для более надежного поиска процессов
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == 'winws.exe':
                    try:
                        psutil.Process(proc.info['pid']).terminate()
                        killed = True
                        log(f"Процесс winws.exe (PID: {proc.info['pid']}) завершен", "INFO")
                    except:
                        pass
            
            # Даем время на завершение
            time.sleep(1)
            
            # Принудительное завершение если не помогло
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == 'winws.exe':
                    try:
                        psutil.Process(proc.info['pid']).kill()
                        log(f"Процесс winws.exe (PID: {proc.info['pid']}) принудительно завершен", "⚠ WARNING")
                    except:
                        pass
                        
        except Exception as e:
            log(f"Ошибка при завершении процессов: {e}", "DEBUG")
            
            # Fallback на taskkill
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", "winws.exe", "/T"],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    killed = True
                    log("Процессы завершены через taskkill", "INFO")
            except:
                pass
        
        # 3. Останавливаем и удаляем службу WinDivert
        try:
            # Останавливаем службу
            subprocess.run(
                ["sc", "stop", "windivert"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=5
            )
            
            time.sleep(1)
            
            # Удаляем службу
            subprocess.run(
                ["sc", "delete", "windivert"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=5
            )
            
            log("Служба WinDivert остановлена и удалена", "INFO")
            
        except Exception as e:
            log(f"Ошибка при остановке службы: {e}", "DEBUG")
        
        # Проверяем результат
        time.sleep(1)
        if app.dpi_starter.check_process_running_wmi(silent=True):
            log("Процесс winws.exe все еще работает", level="⚠ WARNING")
            app.set_status("Не удалось полностью остановить Zapret")
            app.on_process_status_changed(True)
            return False
        else:
            log("Zapret успешно остановлен", level="✅ SUCCESS")
            app.update_ui(running=False)
            app.set_status("Zapret успешно остановлен")
            app.on_process_status_changed(False)
            return True
            
    except Exception as e:
        log(f"Ошибка в stop_dpi_direct: {e}", level="❌ ERROR")
        return False

    
def stop_dpi_bat(app: "LupiDPIApp"):
    """Старый метод остановки через .bat"""
    try:
        log("======================== Stop DPI (BAT) ========================", level="START")
        
        # Проверяем, запущен ли процесс
        if not app.dpi_starter.check_process_running_wmi(silent=True):
            log("Процесс winws.exe не запущен, нет необходимости в остановке", level="INFO")
            app.set_status("Zapret уже остановлен")
            app.update_ui(running=False)
            return True
        
        # Получаем абсолютные пути
        winws_dir = os.path.dirname(os.path.abspath(app.dpi_starter.winws_exe))
        stop_bat_path = os.path.join(winws_dir, "stop.bat")
        
        # Для отладки
        log(f"Абсолютный путь к winws.exe: {os.path.abspath(app.dpi_starter.winws_exe)}", level="DEBUG")
        log(f"Рабочая директория: {winws_dir}", level="DEBUG")
        log(f"Абсолютный путь к stop.bat: {stop_bat_path}", level="DEBUG")
        log(f"stop.bat существует: {os.path.exists(stop_bat_path)}", level="DEBUG")
        
        # Если stop.bat не существует, создаем его
        if not os.path.exists(stop_bat_path):
            log("stop.bat не найден!!!!!!!!!!!!!!!!!!!!!!!!!!!!", level="❌ ERROR")
            return False
        
        # Запускаем stop.bat
        app.set_status("Останавливаю Zapret...")
        log(f"Запускаем {stop_bat_path}...", level="INFO")
        
        # Настройки для скрытого запуска
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        try:
            # Запускаем stop.bat
            result = run_hidden(
                [stop_bat_path],
                shell=True,
                startupinfo=startupinfo,
                capture_output=True,
                text=True,
                encoding='cp866',
                timeout=10,
                cwd=winws_dir
            )
            
            if result.returncode == 0:
                log("stop.bat выполнен успешно", level="✅ SUCCESS")
            else:
                log(f"stop.bat вернул код: {result.returncode}", level="⚠ WARNING")
                if result.stdout:
                    log(f"Вывод: {result.stdout}", level="DEBUG")
                if result.stderr:
                    log(f"Ошибки: {result.stderr}", level="⚠ WARNING")
                
                # Если stop.bat не сработал, пробуем выполнить команды напрямую
                log("Пробуем выполнить команды остановки напрямую...", level="INFO")
                
                # Останавливаем процесс
                run_hidden(
                    ['C:\\Windows\\System32\\taskkill.exe', '/F', '/IM', 'winws.exe', '/T'],
                    shell=False,
                    capture_output=True,
                    timeout=5
                )
                
                # Останавливаем службу
                run_hidden(
                    ['C:\\Windows\\System32\\sc.exe', 'stop', 'windivert'],
                    shell=False,
                    capture_output=True,
                    timeout=5
                )
                
                # Удаляем службу
                run_hidden(
                    ['C:\\Windows\\System32\\sc.exe', 'delete', 'windivert'],
                    shell=False,
                    capture_output=True,
                    timeout=5
                )
                    
        except subprocess.TimeoutExpired:
            log("Таймаут при выполнении stop.bat", level="⚠ WARNING")
        except Exception as e:
            log(f"Ошибка при выполнении stop.bat: {e}", level="❌ ERROR")
        
        # Даем время на завершение процессов
        time.sleep(1)
        
        # Проверяем результат
        if app.dpi_starter.check_process_running_wmi(silent=True):
            log("Процесс winws.exe все еще работает", level="⚠ WARNING")
            app.set_status("Не удалось полностью остановить Zapret")
            app.on_process_status_changed(True)
            return False
        else:
            log("Zapret успешно остановлен", level="✅ SUCCESS")
            app.update_ui(running=False)
            app.set_status("Zapret успешно остановлен")
            app.on_process_status_changed(False)
            return True
            
    except Exception as e:
        log(f"Критическая ошибка в stop_dpi_bat: {e}", level="❌ ERROR")
        app.set_status(f"Ошибка остановки: {e}")
        return False