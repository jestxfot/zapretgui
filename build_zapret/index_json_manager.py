"""
GUI для управления файлом /home/zapretsite/index.json на удаленном сервере
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import tempfile
from pathlib import Path
from datetime import datetime
import threading
import os

# Импортируем SSH функции из вашего модуля
from ssh_pw import sftp_download, sftp_upload, ssh_exec

# Путь к файлу на сервере
REMOTE_FILE = "/home/zapretsite/index.json"
BACKUP_DIR = "/home/zapretsite/backups"
PUBLIC_DIR = "/home/zapretsite"

class IndexJsonManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Index.json Manager")
        self.root.geometry("1200x800")
        
        # Данные
        self.data = {}
        self.current_key = None
        self.modified = False
        self.current_config_modified = False
        self.bat_loaded = False  # Флаг для отслеживания загрузки BAT файла
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Загружаем данные при запуске
        self.load_from_server()
        
    def create_widgets(self):
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Загрузить с сервера", command=self.load_from_server, accelerator="Ctrl+R")
        file_menu.add_command(label="Сохранить на сервер", command=self.save_to_server, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Создать резервную копию", command=self.create_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_closing)
        
        # Горячие клавиши
        self.root.bind('<Control-r>', lambda e: self.load_from_server())
        self.root.bind('<Control-s>', lambda e: self.save_to_server())
        
        # Основной контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Левая панель - список конфигураций
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        ttk.Label(left_frame, text="Конфигурации:", font=("Arial", 10, "bold")).pack()
        
        # Поиск
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_list)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Список конфигураций с кнопками перемещения
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # Список конфигураций
        list_frame = ttk.Frame(list_container)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.config_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=40)
        self.config_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.config_listbox.yview)
        
        self.config_listbox.bind('<<ListboxSelect>>', self.on_select_config)
        
        # Кнопки перемещения
        move_frame = ttk.Frame(list_container)
        move_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        ttk.Button(move_frame, text="↑", command=self.move_up, width=3).pack(pady=2)
        ttk.Button(move_frame, text="↓", command=self.move_down, width=3).pack(pady=2)
        
        # Кнопки управления
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Добавить", command=self.add_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Удалить", command=self.delete_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Дублировать", command=self.duplicate_config).pack(side=tk.LEFT, padx=2)
        
        # Правая панель - редактор
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Создаем вкладки
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Привязываем обработчик смены вкладок
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Вкладка конфигурации
        config_tab = ttk.Frame(self.notebook)
        self.notebook.add(config_tab, text="Конфигурация")
        
        # Вкладка BAT файла
        bat_tab = ttk.Frame(self.notebook)
        self.notebook.add(bat_tab, text="BAT файл")
        
        # Содержимое вкладки конфигурации
        ttk.Label(config_tab, text="Редактор конфигурации:", font=("Arial", 10, "bold")).pack()
        
        # Форма редактирования
        form_frame = ttk.Frame(config_tab)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Поля формы
        self.fields = {}
        field_names = [
            ("key", "Ключ (ID)"),
            ("name", "Название"),
            ("description", "Описание"),
            ("version", "Версия"),
            ("provider", "Провайдер"),
            ("author", "Автор"),
            ("updated", "Дата обновления"),
            ("label", "Метка"),
            ("file_path", "Путь к файлу"),
            ("ports", "Порты"),
            ("host_lists", "Списки хостов"),
            ("sort_order", "Порядок сортировки")
        ]
        
        for i, (field, label) in enumerate(field_names):
            ttk.Label(form_frame, text=label + ":").grid(row=i, column=0, sticky=tk.W, pady=2)
            
            if field == "description":
                # Многострочное поле для описания
                text_widget = tk.Text(form_frame, height=3, width=50)
                text_widget.grid(row=i, column=1, sticky=(tk.W, tk.E), pady=2)
                text_widget.bind('<KeyRelease>', lambda e: self.mark_config_modified())
                self.fields[field] = text_widget
            else:
                entry = ttk.Entry(form_frame, width=50)
                entry.grid(row=i, column=1, sticky=(tk.W, tk.E), pady=2)
                self.fields[field] = entry
                
                # Привязываем обработчик изменений
                if field != "key":
                    entry.bind('<KeyRelease>', lambda e: self.mark_config_modified())
                else:
                    entry.bind('<KeyRelease>', self.on_key_change)
        
        # Чекбоксы
        checkbox_frame = ttk.Frame(form_frame)
        checkbox_frame.grid(row=len(field_names), column=0, columnspan=2, pady=5)
        
        self.fragments_var = tk.BooleanVar()
        ttk.Checkbutton(checkbox_frame, text="Fragments", variable=self.fragments_var,
                       command=self.mark_config_modified).pack(side=tk.LEFT, padx=5)
        
        self.recommended_var = tk.BooleanVar()
        ttk.Checkbutton(checkbox_frame, text="Recommended", variable=self.recommended_var,
                       command=self.mark_config_modified).pack(side=tk.LEFT, padx=5)
        
        # Вместо кнопок добавляем информационную панель
        info_config_frame = ttk.LabelFrame(config_tab, text="Информация", padding=5)
        info_config_frame.pack(fill=tk.X, pady=5)
        
        self.config_info_label = ttk.Label(info_config_frame, 
            text="• Изменения автоматически применяются при переключении конфигураций\n" +
                "• Для сохранения на сервер используйте Ctrl+S или меню Файл → Сохранить на сервер",
            foreground="gray")
        self.config_info_label.pack()
        
        # Содержимое вкладки BAT файла
        bat_frame = ttk.Frame(bat_tab)
        bat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(bat_frame, text="Редактор BAT файла:", font=("Arial", 10, "bold")).pack()
        
        # Информация о файле
        self.bat_info_label = ttk.Label(bat_frame, text="", foreground="gray")
        self.bat_info_label.pack(pady=5)
        
        # Текстовый редактор для BAT файла
        bat_text_frame = ttk.Frame(bat_frame)
        bat_text_frame.pack(fill=tk.BOTH, expand=True)
        
        bat_scrollbar = ttk.Scrollbar(bat_text_frame)
        bat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.bat_text = tk.Text(bat_text_frame, wrap=tk.NONE, yscrollcommand=bat_scrollbar.set)
        self.bat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bat_scrollbar.config(command=self.bat_text.yview)
        
        # Горизонтальный скроллбар для BAT
        bat_h_scrollbar = ttk.Scrollbar(bat_frame, orient=tk.HORIZONTAL)
        bat_h_scrollbar.pack(fill=tk.X)
        self.bat_text.config(xscrollcommand=bat_h_scrollbar.set)
        bat_h_scrollbar.config(command=self.bat_text.xview)
        
        # Кнопки для BAT файла (убрали кнопку "Загрузить BAT")
        bat_button_frame = ttk.Frame(bat_frame)
        bat_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(bat_button_frame, text="Сохранить BAT", command=self.save_bat_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(bat_button_frame, text="Создать BAT", command=self.create_bat_file).pack(side=tk.LEFT, padx=5)
        
        # Информационная панель
        info_frame = ttk.LabelFrame(right_frame, text="Информация", padding=5)
        info_frame.pack(fill=tk.X, pady=10)

        self.info_label = ttk.Label(info_frame, text="• Изменения конфигураций применяются автоматически\n" +
                                                    "• Ctrl+S или меню Файл → Сохранить на сервер - загружает все изменения на сервер\n" +
                                                    "• BAT файлы загружаются автоматически при переключении на вкладку",
                                foreground="gray")
        self.info_label.pack()
        
        # Статусная строка
        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)
        
    def on_tab_changed(self, event):
        """Обработчик смены вкладок"""
        selected_tab = event.widget.tab('current')['text']
        
        # Если переключились на вкладку BAT файла и есть выбранная конфигурация
        if selected_tab == "BAT файл" and self.current_key and not self.bat_loaded:
            self.load_bat_file()

    def move_up(self):
        """Перемещает выбранную конфигурацию вверх"""
        selection = self.config_listbox.curselection()
        if not selection or selection[0] == 0:
            return
            
        # Получаем текущий элемент
        current_index = selection[0]
        current_text = self.config_listbox.get(current_index)
        if current_text.startswith('★ '):
            current_text = current_text[2:]
        
        # Извлекаем ключ
        last_paren = current_text.rfind('(')
        if last_paren != -1:
            current_key = current_text[last_paren + 1:-1]
        else:
            current_key = current_text
            
        # Получаем элемент выше
        prev_text = self.config_listbox.get(current_index - 1)
        if prev_text.startswith('★ '):
            prev_text = prev_text[2:]
        
        # Извлекаем ключ
        last_paren = prev_text.rfind('(')
        if last_paren != -1:
            prev_key = prev_text[last_paren + 1:-1]
        else:
            prev_key = prev_text
            
        # Меняем sort_order
        current_sort = self.data[current_key].get('sort_order', 999)
        prev_sort = self.data[prev_key].get('sort_order', 999)
        
        self.data[current_key]['sort_order'] = prev_sort
        self.data[prev_key]['sort_order'] = current_sort
        
        self.mark_modified()
        self.update_list()
        
        # Восстанавливаем выделение
        for i in range(self.config_listbox.size()):
            if current_key in self.config_listbox.get(i):
                self.config_listbox.selection_clear(0, tk.END)
                self.config_listbox.selection_set(i)
                self.config_listbox.see(i)
                break
                
    def move_down(self):
        """Перемещает выбранную конфигурацию вниз"""
        selection = self.config_listbox.curselection()
        if not selection or selection[0] >= self.config_listbox.size() - 1:
            return
            
        # Получаем текущий элемент
        current_index = selection[0]
        current_text = self.config_listbox.get(current_index)
        if current_text.startswith('★ '):
            current_text = current_text[2:]
        
        # Извлекаем ключ
        last_paren = current_text.rfind('(')
        if last_paren != -1:
            current_key = current_text[last_paren + 1:-1]
        else:
            current_key = current_text
            
        # Получаем элемент ниже
        next_text = self.config_listbox.get(current_index + 1)
        if next_text.startswith('★ '):
            next_text = next_text[2:]
        
        # Извлекаем ключ
        last_paren = next_text.rfind('(')
        if last_paren != -1:
            next_key = next_text[last_paren + 1:-1]
        else:
            next_key = next_text
            
        # Меняем sort_order
        current_sort = self.data[current_key].get('sort_order', 999)
        next_sort = self.data[next_key].get('sort_order', 999)
        
        self.data[current_key]['sort_order'] = next_sort
        self.data[next_key]['sort_order'] = current_sort
        
        self.mark_modified()
        self.update_list()
        
        # Восстанавливаем выделение
        for i in range(self.config_listbox.size()):
            if current_key in self.config_listbox.get(i):
                self.config_listbox.selection_clear(0, tk.END)
                self.config_listbox.selection_set(i)
                self.config_listbox.see(i)
                break

    def load_bat_file(self):
        """Загружает BAT файл с сервера"""
        if not self.current_key:
            return
        
        # Получаем правильное имя файла из конфигурации
        config = self.data.get(self.current_key, {})
        file_path = config.get('file_path', '')
        
        if file_path:
            # Используем file_path из конфигурации
            if file_path.endswith('.bat'):
                bat_filename = file_path
            else:
                bat_filename = f"{file_path}.bat"
        else:
            # Фоллбэк - генерируем из ключа
            bat_filename = f"{self.current_key}.bat"
        
        remote_bat_path = f"{PUBLIC_DIR}/{bat_filename}"
        
        print(f"DEBUG: Key: {self.current_key}")
        print(f"DEBUG: file_path from config: '{file_path}'")
        print(f"DEBUG: Final BAT filename: {bat_filename}")
        print(f"DEBUG: Full path: {remote_bat_path}")
        
        self.status_var.set(f"Загрузка {bat_filename}...")
        self.bat_info_label.config(text=f"Загрузка файла {bat_filename}...")
        
        def load():
            try:
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.bat') as tmp:
                    tmp_path = tmp.name
                
                # Проверяем существование файла
                ret, out, err = ssh_exec(f"test -f {remote_bat_path} && echo 'exists'")
                print(f"DEBUG: test command returned: ret={ret}, out='{out}', err='{err}'")
                
                if 'exists' not in out:
                    # Файл не существует - показываем сообщение
                    self.root.after(0, lambda: self.bat_text.delete('1.0', tk.END))
                    self.root.after(0, lambda: self.bat_info_label.config(
                        text=f"Файл {bat_filename} не найден. Нажмите 'Создать BAT' для создания нового файла."))
                    self.root.after(0, lambda: self.status_var.set("BAT файл не найден"))
                    self.bat_loaded = True
                    return
                
                # Загружаем файл
                sftp_download(remote_bat_path, tmp_path)
                
                # Читаем содержимое
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Удаляем временный файл
                Path(tmp_path).unlink()
                
                # Обновляем интерфейс
                self.root.after(0, lambda: self.bat_text.delete('1.0', tk.END))
                self.root.after(0, lambda: self.bat_text.insert('1.0', content))
                self.root.after(0, lambda: self.bat_info_label.config(
                    text=f"Файл: {bat_filename} (загружен с сервера)"))
                self.root.after(0, lambda: self.status_var.set(f"BAT файл загружен"))
                self.bat_loaded = True
                
            except Exception as e:
                print(f"DEBUG: Exception occurred: {e}")
                import traceback
                traceback.print_exc()
                
                self.root.after(0, lambda: self.bat_text.delete('1.0', tk.END))
                self.root.after(0, lambda: self.bat_info_label.config(
                    text=f"Ошибка загрузки {bat_filename}: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("Ошибка загрузки BAT файла"))
                self.bat_loaded = True
        
        threading.Thread(target=load, daemon=True).start()

    def save_bat_file(self):
        """Сохраняет BAT файл на сервер"""
        if not self.current_key:
            messagebox.showwarning("Предупреждение", "Сначала выберите конфигурацию")
            return
            
        content = self.bat_text.get('1.0', tk.END).strip()
        if not content:
            messagebox.showwarning("Предупреждение", "BAT файл пустой")
            return
        
        # Получаем правильное имя файла из конфигурации
        config = self.data.get(self.current_key, {})
        file_path = config.get('file_path', '')
        
        if file_path:
            # Используем file_path из конфигурации
            if file_path.endswith('.bat'):
                bat_filename = file_path
            else:
                bat_filename = f"{file_path}.bat"
        else:
            # Фоллбэк - генерируем из ключа
            bat_filename = f"{self.current_key}.bat"
        
        remote_bat_path = f"{PUBLIC_DIR}/{bat_filename}"
        
        if not messagebox.askyesno("Подтверждение", 
            f"Сохранить BAT файл '{bat_filename}' на сервер?"):
            return
            
        self.status_var.set(f"Сохранение {bat_filename}...")
        
        def save():
            try:
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.bat', 
                                            encoding='utf-8', newline='\r\n') as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                # Загружаем на сервер
                sftp_upload(tmp_path, remote_bat_path)
                
                # Устанавливаем права на выполнение
                ssh_exec(f"chmod +x {remote_bat_path}")
                
                # Удаляем временный файл
                Path(tmp_path).unlink()
                
                # Обновляем интерфейс
                self.root.after(0, lambda: self.bat_info_label.config(
                    text=f"Файл: {bat_filename} (сохранен на сервер)"))
                self.root.after(0, lambda: self.status_var.set(f"BAT файл сохранен"))
                self.root.after(0, lambda: messagebox.showinfo("Успех", 
                    f"BAT файл '{bat_filename}' успешно сохранен на сервер"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", 
                    f"Не удалось сохранить BAT файл:\n{str(e)}"))
                self.root.after(0, lambda: self.status_var.set("Ошибка сохранения BAT файла"))
        
        threading.Thread(target=save, daemon=True).start()

    def create_bat_file(self):
        """Создает шаблон BAT файла"""
        if not self.current_key:
            messagebox.showwarning("Предупреждение", "Сначала выберите конфигурацию")
            return
            
        config = self.data.get(self.current_key, {})
        config_name = config.get('name', self.current_key)
        
        # Получаем правильное имя файла
        file_path = config.get('file_path', '')
        if file_path:
            if file_path.endswith('.bat'):
                bat_filename = file_path.replace('.bat', '')
            else:
                bat_filename = file_path
        else:
            bat_filename = self.current_key
        
        # Создаем шаблон BAT файла (исправлены отступы)
        template = f"""@echo off
    chcp 65001 >nul
    title {config_name}

    echo ========================================
    echo {config_name}
    echo ========================================
    echo.

    REM Здесь добавьте команды для вашей конфигурации
    REM Например:

    REM Установка переменных окружения
    set CONFIG_NAME={self.current_key}

    REM Запуск основной программы
    REM start /wait your_program.exe --config "%CONFIG_NAME%"

    echo.
    echo Нажмите любую клавишу для выхода...
    pause >nul
    """
        
        self.bat_text.delete('1.0', tk.END)
        self.bat_text.insert('1.0', template)
        self.bat_info_label.config(text=f"Файл: {bat_filename}.bat (новый шаблон)")
        self.status_var.set("Создан шаблон BAT файла")        

    def load_from_server(self):
        """Загружает файл с сервера"""
        if self.modified:
            if not messagebox.askyesno("Несохраненные изменения", 
                "Есть несохраненные изменения. Продолжить без сохранения?"):
                return
                
        self.status_var.set("Загрузка с сервера...")
        
        def load():
            try:
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                    tmp_path = tmp.name
                
                # Загружаем файл
                sftp_download(REMOTE_FILE, tmp_path)
                
                # Читаем JSON с поддержкой utf-8-sig
                with open(tmp_path, 'r', encoding='utf-8-sig') as f:
                    self.data = json.load(f)
                
                # Удаляем временный файл
                Path(tmp_path).unlink()
                
                # Обновляем интерфейс в главном потоке
                self.root.after(0, self.update_list)
                self.root.after(0, lambda: self.status_var.set("Загружено успешно"))
                self.modified = False
                self.current_config_modified = False
                self.root.after(0, lambda: self.root.title("Index.json Manager"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}"))
                self.root.after(0, lambda: self.status_var.set("Ошибка загрузки"))
        
        threading.Thread(target=load, daemon=True).start()

    def save_to_server(self):
        """Сохраняет файл на сервер"""
        # Автоматически применяем текущие изменения без вопросов
        if self.current_config_modified and self.current_key:
            self.apply_current_config()
        
        if not self.modified:
            messagebox.showinfo("Информация", "Нет изменений для сохранения")
            return
            
        if not messagebox.askyesno("Подтверждение", "Сохранить все изменения на сервер?"):
            return
            
        self.status_var.set("Сохранение на сервер...")
        
        def save():
            try:
                # Создаем временный файл с кодировкой utf-8-sig
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8-sig') as tmp:
                    json.dump(self.data, tmp, ensure_ascii=False, indent=2)
                    tmp_path = tmp.name
                
                # Загружаем на сервер
                sftp_upload(tmp_path, REMOTE_FILE)
                
                # Удаляем временный файл
                Path(tmp_path).unlink()
                
                # Обновляем статус
                self.root.after(0, lambda: self.status_var.set("Сохранено на сервер успешно"))
                self.modified = False
                self.root.after(0, lambda: self.root.title("Index.json Manager"))
                self.root.after(0, lambda: messagebox.showinfo("Успех", "Изменения успешно сохранены на сервер"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}"))
                self.root.after(0, lambda: self.status_var.set("Ошибка сохранения"))
        
        threading.Thread(target=save, daemon=True).start()
        
    def create_backup(self):
        """Создает резервную копию на сервере"""
        self.status_var.set("Создание резервной копии...")
        
        def backup():
            try:
                # Создаем директорию для бэкапов если её нет
                ssh_exec(f"mkdir -p {BACKUP_DIR}")
                
                # Создаем имя файла с датой
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{BACKUP_DIR}/index_{timestamp}.json"
                
                # Копируем файл
                ret, out, err = ssh_exec(f"cp {REMOTE_FILE} {backup_file}")
                
                if ret == 0:
                    self.root.after(0, lambda: messagebox.showinfo("Успех", f"Резервная копия создана:\n{backup_file}"))
                    self.root.after(0, lambda: self.status_var.set("Резервная копия создана"))
                else:
                    raise Exception(err)
                    
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось создать резервную копию:\n{str(e)}"))
                self.root.after(0, lambda: self.status_var.set("Ошибка создания резервной копии"))
        
        threading.Thread(target=backup, daemon=True).start()
        
    def update_list(self):
        """Обновляет список конфигураций"""
        self.config_listbox.delete(0, tk.END)
        
        # Сортируем по sort_order
        sorted_items = sorted(self.data.items(), 
                            key=lambda x: x[1].get('sort_order', 999))
        
        search_term = self.search_var.get().lower()
        
        for key, config in sorted_items:
            # Фильтрация по поиску
            if search_term:
                if not any(search_term in str(v).lower() for v in [key, config.get('name', ''), 
                          config.get('provider', ''), config.get('author', '')]):
                    continue
                    
            display_text = f"{config.get('name', key)} ({key})"
            if config.get('recommended'):
                display_text = "★ " + display_text
            self.config_listbox.insert(tk.END, display_text)
            
    def filter_list(self, *args):
        """Фильтрует список при поиске"""
        self.update_list()
        
    def on_select_config(self, event):
        """Обработчик выбора конфигурации"""
        # Автоматически применяем изменения текущей конфигурации без запроса
        if self.current_config_modified and self.current_key:
            self.apply_current_config()
        
        selection = self.config_listbox.curselection()
        if not selection:
            return
            
        # Получаем ключ из текста
        text = self.config_listbox.get(selection[0])
        # Убираем звездочку если есть
        if text.startswith('★ '):
            text = text[2:]
        
        # Извлекаем ключ из скобок
        last_paren = text.rfind('(')
        if last_paren != -1:
            key = text[last_paren + 1:-1]
        else:
            key = text
            
        self.load_config(key)
        
        # Сбрасываем флаг загрузки BAT файла
        self.bat_loaded = False
        
        # Если текущая вкладка - BAT файл, загружаем его
        if self.notebook.tab('current')['text'] == "BAT файл":
            self.load_bat_file()
        else:
            # Очищаем BAT редактор и показываем информацию
            self.bat_text.delete('1.0', tk.END)
            self.bat_info_label.config(text=f"Переключитесь на вкладку 'BAT файл' для работы с файлом")
        
    def load_config(self, key):
        """Загружает конфигурацию в форму"""
        if key not in self.data:
            print(f"DEBUG: Key '{key}' not found in data!")
            return
            
        self.current_key = key
        print(f"DEBUG: Current key set to: '{self.current_key}'")
        
        config = self.data[key]
        
        # Заполняем поля
        self.fields['key'].delete(0, tk.END)
        self.fields['key'].insert(0, key)
        
        for field, widget in self.fields.items():
            if field == 'key':
                continue
                
            value = config.get(field, '')
            
            if isinstance(widget, tk.Text):
                # Для текстового виджета
                widget.delete('1.0', tk.END)
                widget.insert('1.0', str(value))
            else:
                # Для Entry виджета
                widget.delete(0, tk.END)
                widget.insert(0, str(value))
        
        # Устанавливаем чекбоксы
        self.fragments_var.set(config.get('fragments', False))
        self.recommended_var.set(config.get('recommended', False))
        
        # Сбрасываем флаг изменений конфигурации
        self.current_config_modified = False
        
    def apply_current_config(self):
        """Применяет изменения текущей конфигурации"""
        if not self.current_key:
            messagebox.showwarning("Предупреждение", "Не выбрана конфигурация")
            return
            
        new_key = self.fields['key'].get().strip()
        if not new_key:
            messagebox.showerror("Ошибка", "Ключ не может быть пустым")
            return
            
        # Собираем данные из формы
        config = {}
        for field, widget in self.fields.items():
            if field == 'key':
                continue
                
            if isinstance(widget, tk.Text):
                value = widget.get('1.0', tk.END).strip()
            else:
                value = widget.get().strip()
                
            if field == 'sort_order':
                try:
                    value = int(value) if value else 999
                except ValueError:
                    value = 999
                    
            if value:  # Сохраняем только непустые значения
                config[field] = value
        
        # Добавляем чекбоксы
        config['fragments'] = self.fragments_var.get()
        if self.recommended_var.get():
            config['recommended'] = True
        
        # Если ключ изменился, удаляем старый
        if new_key != self.current_key:
            if new_key in self.data:
                if not messagebox.askyesno("Подтверждение", 
                    f"Конфигурация с ключом '{new_key}' уже существует. Перезаписать?"):
                    return
            del self.data[self.current_key]
            self.current_key = new_key
        
        # Сохраняем конфигурацию
        self.data[new_key] = config
        self.mark_modified()
        self.current_config_modified = False
        self.update_list()
        
        # Выделяем сохраненный элемент
        for i in range(self.config_listbox.size()):
            if new_key in self.config_listbox.get(i):
                self.config_listbox.selection_clear(0, tk.END)
                self.config_listbox.selection_set(i)
                self.config_listbox.see(i)
                break
                
        self.status_var.set("Изменения применены (не забудьте сохранить на сервер)")
        
    def add_config(self):
        """Добавляет новую конфигурацию"""
        # Автоматически применяем изменения без запроса
        if self.current_config_modified and self.current_key:
            self.apply_current_config()
        
        # Генерируем уникальный ключ
        base_key = "new_config"
        key = base_key
        counter = 1
        while key in self.data:
            key = f"{base_key}_{counter}"
            counter += 1
            
        # Создаем базовую конфигурацию
        self.data[key] = {
            "name": "Новая конфигурация",
            "description": "",
            "version": "1.0",
            "provider": "All",
            "author": "",
            "updated": datetime.now().strftime("%Y-%m-%d"),
            "label": "All",
            "file_path": "",
            "ports": "80, 443",
            "host_lists": "Discord, YouTube, Other, Cloudflare",
            "fragments": True,
            "sort_order": max([c.get('sort_order', 0) for c in self.data.values()], default=0) + 1
        }
        
        self.mark_modified()
        self.update_list()
        
        # Выделяем новый элемент
        for i in range(self.config_listbox.size()):
            if key in self.config_listbox.get(i):
                self.config_listbox.selection_clear(0, tk.END)
                self.config_listbox.selection_set(i)
                self.config_listbox.see(i)
                self.load_config(key)
                break
                
    def delete_config(self):
        """Удаляет выбранную конфигурацию"""
        if not self.current_key:
            messagebox.showwarning("Предупреждение", "Не выбрана конфигурация")
            return
            
        config_name = self.data[self.current_key].get('name', self.current_key)
        if not messagebox.askyesno("Подтверждение", 
            f"Удалить конфигурацию '{config_name}'?"):
            return
            
        del self.data[self.current_key]
        self.current_key = None
        self.mark_modified()
        self.update_list()
        
        # Очищаем форму
        for widget in self.fields.values():
            if isinstance(widget, tk.Text):
                widget.delete('1.0', tk.END)
            else:
                widget.delete(0, tk.END)
        self.fragments_var.set(False)
        self.recommended_var.set(False)
        self.current_config_modified = False
        
        # Очищаем BAT редактор
        self.bat_text.delete('1.0', tk.END)
        self.bat_info_label.config(text="")
        self.bat_loaded = False
        
    def duplicate_config(self):
        """Дублирует выбранную конфигурацию"""
        if not self.current_key:
            messagebox.showwarning("Предупреждение", "Не выбрана конфигурация")
            return
            
        # Генерируем новый ключ
        base_key = f"{self.current_key}_copy"
        new_key = base_key
        counter = 1
        while new_key in self.data:
            new_key = f"{base_key}_{counter}"
            counter += 1
            
        # Копируем конфигурацию
        import copy
        self.data[new_key] = copy.deepcopy(self.data[self.current_key])
        self.data[new_key]['name'] = self.data[new_key].get('name', '') + " (копия)"
        self.data[new_key]['sort_order'] = max([c.get('sort_order', 0) for c in self.data.values()], default=0) + 1
        
        self.mark_modified()
        self.update_list()
        
        # Выделяем новый элемент
        for i in range(self.config_listbox.size()):
            if new_key in self.config_listbox.get(i):
                self.config_listbox.selection_clear(0, tk.END)
                self.config_listbox.selection_set(i)
                self.config_listbox.see(i)
                self.load_config(new_key)
                break
                
    def on_key_change(self, event):
        """Обработчик изменения ключа"""
        new_key = self.fields['key'].get().strip()
        if new_key and new_key != self.current_key and new_key in self.data:
            self.fields['key'].config(background='#ffcccc')
        else:
            self.fields['key'].config(background='white')
        self.mark_config_modified()
        
    def mark_modified(self):
        """Отмечает, что данные изменены"""
        if not self.modified:
            self.modified = True
            self.root.title("Index.json Manager *")
            
    def mark_config_modified(self):
        """Отмечает, что текущая конфигурация изменена"""
        if not self.current_config_modified:
            self.current_config_modified = True
            
    def on_closing(self):
        """Обработчик закрытия окна"""
        # Автоматически применяем изменения конфигурации
        if self.current_config_modified and self.current_key:
            self.apply_current_config()
        
        # Проверяем несохраненные изменения на сервере
        if self.modified:
            result = messagebox.askyesnocancel("Несохраненные изменения", 
                "Есть несохраненные изменения. Сохранить на сервер перед выходом?")
            if result is None:  # Отмена
                return
            elif result:  # Да
                self.save_to_server()
                # Ждем завершения сохранения
                self.root.after(2000, self.root.destroy)
                return
                
        self.root.destroy()


def main():
    root = tk.Tk()
    app = IndexJsonManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()