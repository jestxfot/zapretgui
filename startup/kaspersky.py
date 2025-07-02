# startup/kaspersky.py
from __future__ import annotations
import os, sys, ctypes, subprocess
from PyQt6.QtCore import QUrl
from PyQt6.QtGui  import QDesktopServices

def _open_url(url: str):
    QDesktopServices.openUrl(QUrl(url))

def _check_kaspersky_antivirus(self):
    """
    Проверяет наличие антивируса Касперского в системе.
    
    Returns:
        bool: True если Касперский обнаружен, False если нет
    """
    try:
        import subprocess
        import os
        
        # Проверяем наличие процессов Касперского
        kaspersky_processes = [
            'avp.exe', 'kavfs.exe', 'klnagent.exe', 'ksde.exe',
            'kavfswp.exe', 'kavfswh.exe', 'kavfsslp.exe'
        ]
        
        # Получаем список запущенных процессов
        try:
            result = run_hidden(['C:\\Windows\\System32\\tasklist.exe'], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                running_processes = result.stdout.lower()
                
                for process in kaspersky_processes:
                    if process.lower() in running_processes:
                        return True
        except Exception:
            pass
        
        # Проверяем папки установки Касперского
        kaspersky_paths = [
            r'C:\Program Files\Kaspersky Lab',
            r'C:\Program Files (x86)\Kaspersky Lab',
            r'C:\Program Files\Kaspersky Security',
            r'C:\Program Files (x86)\Kaspersky Security'
        ]
        
        for path in kaspersky_paths:
            if os.path.exists(path) and os.path.isdir(path):
                try:
                    # Проверяем, что папка не пустая
                    dir_contents = os.listdir(path)
                    if dir_contents:
                        # Дополнительно проверяем наличие исполняемых файлов или подпапок
                        for item in dir_contents:
                            item_path = os.path.join(path, item)
                            if os.path.isdir(item_path) or item.lower().endswith(('.exe', '.dll')):
                                return True
                except (PermissionError, OSError):
                    # Если нет доступа к папке, но она существует - считаем что Касперский есть
                    return True
        
        # Если ни один процесс не найден и папки пустые/не найдены, считаем что Касперского нет
        return False
        
    except Exception as e:
        # В случае ошибки считаем, что Касперского нет
        return False

def show_kaspersky_warning(parent=None) -> None:
    """
    Показывает Qt-диалог с предупреждением, «кликабельными» путями и
    кнопками копирования.  Требует уже созданный QApplication.
    """
    # -- корректно определяем пути -------------------------------------------------
    if getattr(sys, "frozen", False):          # .exe, собранный PyInstaller-ом
        exe_path = os.path.abspath(sys.executable)
        base_dir = os.path.dirname(exe_path)
    else:                                      # запуск из исходников
        exe_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "zapret.pyw")
        )
        base_dir = os.path.dirname(exe_path)

    # -- сам QMessageBox -----------------------------------------------------------
    from PyQt6.QtWidgets import QMessageBox, QPushButton, QApplication
    from PyQt6.QtCore    import Qt, QUrl
    from PyQt6.QtGui     import QDesktopServices, QIcon

    mb = QMessageBox(parent)
    mb.setWindowTitle("Zapret – Обнаружен Kaspersky")
    mb.setIcon(QMessageBox.Icon.Warning)
    mb.setTextFormat(Qt.TextFormat.RichText)

    # ✨ HTML-текст со ссылками (file:// …) – Windows их открывает проводником
    mb.setText(
        "⚠️ <b>ВНИМАНИЕ: Обнаружен антивирус Kaspersky!</b><br><br>"
        "Для корректной работы Zapret необходимо добавить программу в исключения.<br><br>"
        "<b>ИНСТРУКЦИЯ</b>:<br>"
        "1. Откройте Kaspersky → Настройки<br>"
        "2. «Исключения» / «Доверенная зона»<br>"
        "3. Добавьте:<br>"
        f"&nbsp;&nbsp;• Папку:&nbsp;"
        f"<a href='file:///{base_dir.replace(os.sep, '/')}'>{base_dir}</a><br>"
        f"&nbsp;&nbsp;• Файл:&nbsp;"
        f"<a href='file:///{exe_path.replace(os.sep, '/')}'>{exe_path}</a><br>"
        "4. Сохраните и перезапустите Zapret.<br><br>"
        "Без добавления в исключения программа может работать некорректно.<br><br>"
        "Нажмите <b>OK</b> для продолжения запуска."
    )

    # -- добавляем 2 кастомных «копирующих» кнопки --------------------------------
    copy_dir_btn  = QPushButton("📋 Копировать папку")
    copy_exe_btn  = QPushButton("📋 Копировать exe")
    mb.addButton(copy_dir_btn, QMessageBox.ButtonRole.ActionRole)
    mb.addButton(copy_exe_btn, QMessageBox.ButtonRole.ActionRole)

    # 2) отключаем «кнопка по умолчанию» – иначе клик интерпретируется
    #    как Accept и QMessageBox закрывается
    for btn in (copy_dir_btn, copy_exe_btn):
        btn.setAutoDefault(False)
        btn.setDefault(False)

    # стандартный OK, который действительно закрывает окно
    ok_btn = mb.addButton(QMessageBox.StandardButton.Ok)
    mb.setDefaultButton(ok_btn)

    # -- обработка копирования -----------------------------------------------------
    def copy_to_clipboard(text: str):
        QApplication.clipboard().setText(text)
    copy_dir_btn.clicked.connect(lambda: copy_to_clipboard(base_dir))
    copy_exe_btn.clicked.connect(lambda: copy_to_clipboard(exe_path))

    if hasattr(mb, "linkActivated"):
        mb.linkActivated.connect(_open_url)
    else:
        # fallback для старых/обрезанных сборок
        from PyQt6.QtWidgets import QLabel
        lbl = mb.findChild(QLabel, "qt_msgbox_label")
        if lbl is not None and hasattr(lbl, "linkActivated"):
            lbl.setOpenExternalLinks(False)
            lbl.linkActivated.connect(_open_url)

    mb.exec()