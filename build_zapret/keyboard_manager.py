"""
keyboard_manager.py - Управление горячими клавишами и контекстным меню
Поддерживает русскую раскладку и контекстное меню
"""

import tkinter as tk
from tkinter import ttk
import platform

class KeyboardManager:
    def __init__(self, root):
        self.root = root
        self.context_menu = None
        self.setup_context_menu()
        self.setup_keyboard_shortcuts()
        
    def setup_context_menu(self):
        """Создание контекстного меню"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Вырезать", 
                                     accelerator="Ctrl+X",
                                     command=self.cut_text_from_menu)
        self.context_menu.add_command(label="Копировать", 
                                     accelerator="Ctrl+C",
                                     command=self.copy_text_from_menu)
        self.context_menu.add_command(label="Вставить", 
                                     accelerator="Ctrl+V",
                                     command=self.paste_text_from_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё", 
                                     accelerator="Ctrl+A",
                                     command=self.select_all_from_menu)
        
        # Если Text виджет, добавляем Undo/Redo
        self.text_context_menu = tk.Menu(self.root, tearoff=0)
        self.text_context_menu.add_command(label="Отменить", 
                                          accelerator="Ctrl+Z",
                                          command=self.undo_from_menu)
        self.text_context_menu.add_command(label="Повторить", 
                                          accelerator="Ctrl+Y",
                                          command=self.redo_from_menu)
        self.text_context_menu.add_separator()
        self.text_context_menu.add_command(label="Вырезать", 
                                          accelerator="Ctrl+X",
                                          command=self.cut_text_from_menu)
        self.text_context_menu.add_command(label="Копировать", 
                                          accelerator="Ctrl+C",
                                          command=self.copy_text_from_menu)
        self.text_context_menu.add_command(label="Вставить", 
                                          accelerator="Ctrl+V",
                                          command=self.paste_text_from_menu)
        self.text_context_menu.add_separator()
        self.text_context_menu.add_command(label="Выделить всё", 
                                          accelerator="Ctrl+A",
                                          command=self.select_all_from_menu)
        
        # Привязываем правую кнопку мыши
        self.root.bind_all('<Button-3>', self.show_context_menu)
        # Для Mac OS
        self.root.bind_all('<Button-2>', self.show_context_menu)
        
    def show_context_menu(self, event):
        """Показ контекстного меню"""
        widget = event.widget
        
        # Фокусируемся на виджете
        widget.focus_set()
        
        # Сохраняем текущий виджет для операций меню
        self.current_widget = widget
        
        # Выбираем подходящее меню
        if isinstance(widget, tk.Text):
            menu = self.text_context_menu
        else:
            menu = self.context_menu
            
        # Обновляем состояние пунктов меню
        self.update_menu_state(menu, widget)
        
        # Показываем меню
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            
    def update_menu_state(self, menu, widget):
        """Обновление состояния пунктов меню"""
        # Проверяем наличие выделенного текста
        has_selection = False
        
        if isinstance(widget, tk.Text):
            try:
                widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                has_selection = True
            except tk.TclError:
                pass
        elif isinstance(widget, (ttk.Entry, tk.Entry)):
            try:
                has_selection = widget.selection_present()
            except:
                pass
                
        # Проверяем буфер обмена
        has_clipboard = False
        try:
            self.root.clipboard_get()
            has_clipboard = True
        except:
            pass
            
        # Обновляем состояния
        if isinstance(widget, tk.Text):
            # Для Text виджетов проверяем undo/redo
            try:
                menu.entryconfig("Отменить", state='normal' if widget.edit_modified() else 'disabled')
            except:
                menu.entryconfig("Отменить", state='disabled')
                
            menu.entryconfig("Повторить", state='normal')  # Всегда активно для Text
            
        menu.entryconfig("Вырезать", state='normal' if has_selection else 'disabled')
        menu.entryconfig("Копировать", state='normal' if has_selection else 'disabled')
        menu.entryconfig("Вставить", state='normal' if has_clipboard else 'disabled')
        
    def setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш с поддержкой русской раскладки"""
        
        # Привязываем обработчик ко всем Control+Key событиям
        self.root.bind_all('<Control-KeyPress>', self.handle_control_key)
        
        # Дополнительные комбинации
        self.root.bind_all('<Control-Shift-KeyPress-z>', lambda e: self.redo_text(e))
        self.root.bind_all('<Control-Shift-KeyPress-Z>', lambda e: self.redo_text(e))
        
    def handle_control_key(self, event):
        """Универсальный обработчик для Control+Key"""
        # Получаем символ и keysym
        char = event.char.lower() if event.char else ''
        keysym = event.keysym.lower()
        
        # Словарь для маппинга русских букв на действия
        ru_mapping = {
            'с': 'copy',     # Ctrl+С (русская)
            'м': 'paste',    # Ctrl+М (русская)
            'ч': 'cut',      # Ctrl+Ч (русская)
            'ф': 'selectall',# Ctrl+Ф (русская)
            'я': 'undo',     # Ctrl+Я (русская)
            'н': 'redo',     # Ctrl+Н (русская)
        }
        
        # Словарь для английских букв
        en_mapping = {
            'c': 'copy',
            'v': 'paste',
            'x': 'cut',
            'a': 'selectall',
            'z': 'undo',
            'y': 'redo',
        }
        
        # Определяем действие
        action = None
        
        # Проверяем английскую раскладку
        if keysym in en_mapping:
            action = en_mapping[keysym]
        # Проверяем русскую раскладку по символу
        elif char in ru_mapping:
            action = ru_mapping[char]
            
        # Выполняем действие
        if action == 'copy':
            return self.copy_text(event)
        elif action == 'paste':
            return self.paste_text(event)
        elif action == 'cut':
            return self.cut_text(event)
        elif action == 'selectall':
            return self.select_all(event)
        elif action == 'undo':
            return self.undo_text(event)
        elif action == 'redo':
            return self.redo_text(event)
    
    # Операции из контекстного меню
    def cut_text_from_menu(self):
        if hasattr(self, 'current_widget'):
            event = type('Event', (), {'widget': self.current_widget})()
            self.cut_text(event)
            
    def copy_text_from_menu(self):
        if hasattr(self, 'current_widget'):
            event = type('Event', (), {'widget': self.current_widget})()
            self.copy_text(event)
            
    def paste_text_from_menu(self):
        if hasattr(self, 'current_widget'):
            event = type('Event', (), {'widget': self.current_widget})()
            self.paste_text(event)
            
    def select_all_from_menu(self):
        if hasattr(self, 'current_widget'):
            event = type('Event', (), {'widget': self.current_widget})()
            self.select_all(event)
            
    def undo_from_menu(self):
        if hasattr(self, 'current_widget'):
            event = type('Event', (), {'widget': self.current_widget})()
            self.undo_text(event)
            
    def redo_from_menu(self):
        if hasattr(self, 'current_widget'):
            event = type('Event', (), {'widget': self.current_widget})()
            self.redo_text(event)
    
    # Основные операции
    def paste_text(self, event):
        """Вставка текста из буфера обмена"""
        widget = event.widget
        
        try:
            # Получаем текст из буфера обмена
            clipboard_text = self.root.clipboard_get()
            
            if isinstance(widget, tk.Text):
                # Для Text виджета
                widget.event_generate('<<Paste>>')
                
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                # Для Entry виджета
                try:
                    widget.delete("sel.first", "sel.last")
                except:
                    pass
                    
                widget.insert("insert", clipboard_text)
                
        except tk.TclError:
            # Буфер обмена пуст
            pass
            
        return "break"  # Предотвращаем стандартную обработку
        
    def copy_text(self, event):
        """Копирование выделенного текста"""
        widget = event.widget
        
        try:
            if isinstance(widget, tk.Text):
                widget.event_generate('<<Copy>>')
                
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                widget.event_generate('<<Copy>>')
                    
        except:
            pass
            
        return "break"
        
    def cut_text(self, event):
        """Вырезание выделенного текста"""
        widget = event.widget
        
        try:
            if isinstance(widget, tk.Text):
                widget.event_generate('<<Cut>>')
                
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                widget.event_generate('<<Cut>>')
                    
        except:
            pass
            
        return "break"
        
    def select_all(self, event):
        """Выделение всего текста"""
        widget = event.widget
        
        try:
            if isinstance(widget, tk.Text):
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
                
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
                
        except:
            pass
            
        return "break"
        
    def undo_text(self, event):
        """Отмена последнего действия"""
        widget = event.widget
        
        if isinstance(widget, tk.Text):
            try:
                widget.event_generate('<<Undo>>')
            except:
                pass
                
        return "break"
        
    def redo_text(self, event):
        """Повтор отмененного действия"""
        widget = event.widget
        
        if isinstance(widget, tk.Text):
            try:
                widget.event_generate('<<Redo>>')
            except:
                pass
                
        return "break"