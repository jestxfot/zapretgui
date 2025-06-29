# stop.py
import os
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import LupiDPIApp

from log import log


def stop_dpi(app: "LupiDPIApp"):
    """
    Останавливает процесс winws.exe через stop.bat и обновляет UI.
    """
    try:
        log("======================== Stop DPI ========================", level="START")
        
        # Проверяем, запущен ли процесс
        if not app.dpi_starter.check_process_running(silent=True):
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
            log("stop.bat не найден, создаем...", level="INFO")
            if not create_stop_bat(app.dpi_starter.winws_exe):
                log("Не удалось создать stop.bat", level="❌ ERROR")
                app.set_status("Ошибка: не удалось создать stop.bat")
                return False
        
        # Запускаем stop.bat
        app.set_status("Останавливаю Zapret...")
        log(f"Запускаем {stop_bat_path}...", level="INFO")
        
        # Настройки для скрытого запуска
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        try:
            # Вариант 1: Запускаем напрямую через subprocess
            result = subprocess.run(
                [stop_bat_path],
                shell=True,
                startupinfo=startupinfo,
                capture_output=True,
                text=True,
                encoding='cp866',
                timeout=10,
                cwd=winws_dir  # Устанавливаем рабочую директорию
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
                subprocess.run(
                    ['C:\\Windows\\System32\\taskkill.exe', '/F', '/IM', 'winws.exe', '/T'],
                    shell=False,
                    capture_output=True,
                    timeout=5
                )
                
                # Останавливаем службу
                subprocess.run(
                    ['C:\\Windows\\System32\\sc.exe', 'stop', 'windivert'],
                    shell=False,
                    capture_output=True,
                    timeout=5
                )
                
                # Удаляем службу
                subprocess.run(
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
        if app.dpi_starter.check_process_running(silent=True):
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
        log(f"Критическая ошибка в stop_dpi: {e}", level="❌ ERROR")
        app.set_status(f"Ошибка остановки: {e}")
        return False


def create_stop_bat(winws_exe_path):
    """Создает файл stop.bat с абсолютными путями"""
    try:
        # Используем абсолютные пути
        stop_bat_path = os.path.join(os.path.dirname(os.path.abspath(winws_exe_path)), "stop.bat")
        
        # Содержимое stop.bat с полными путями к системным утилитам
        stop_bat_content = """@echo off
REM stop.bat - останавливает winws.exe и очищает службу windivert
echo Остановка Zapret...

REM Останавливаем все процессы winws.exe
C:\\Windows\\System32\\taskkill.exe /F /IM winws.exe /T >nul 2>&1

REM Останавливаем и удаляем службу windivert
C:\\Windows\\System32\\sc.exe stop windivert >nul 2>&1
C:\\Windows\\System32\\sc.exe delete windivert >nul 2>&1

REM Короткая пауза для завершения операций
C:\\Windows\\System32\\timeout.exe /t 1 /nobreak >nul

echo Остановка завершена.
exit /b 0
"""
        
        # Создаем директорию при необходимости
        os.makedirs(os.path.dirname(stop_bat_path), exist_ok=True)
        
        # Записываем файл
        with open(stop_bat_path, 'w', encoding='utf-8') as f:
            f.write(stop_bat_content)
            
        log(f"Файл stop.bat успешно создан: {stop_bat_path}", level="✅ SUCCESS")
        return True
        
    except Exception as e:
        log(f"Ошибка при создании stop.bat: {str(e)}", level="❌ ERROR")
        return False