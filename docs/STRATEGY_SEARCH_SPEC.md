# Спецификация: Поиск и фильтрация стратегий

## Обзор

Универсальный компонент поиска и фильтрации стратегий для всех режимов:
- Zapret 1 BAT (таблица .bat файлов)
- Zapret 1 Direct (категории + JSON стратегии)
- Zapret 2 Direct (категории + JSON стратегии)

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    StrategySearchBar                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ [🔍 Поиск...]  [Label ▼]  [Сортировка ▼]  [Фильтры ▼]   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    StrategyFilterEngine                          │
│  - parse_query(text) → SearchQuery                              │
│  - filter_strategies(strategies, query) → filtered              │
│  - sort_strategies(strategies, sort_key) → sorted               │
│  - group_by_label(strategies) → grouped                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Адаптеры для разных источников                      │
│  - BatStrategyAdapter (для .bat файлов)                         │
│  - JsonStrategyAdapter (для JSON стратегий)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. StrategySearchBar (UI виджет)

**Файл:** `ui/widgets/strategy_search_bar.py`

```python
class StrategySearchBar(QWidget):
    """Панель поиска и фильтрации стратегий"""

    # Сигналы
    search_changed = pyqtSignal(str)           # Текст поиска изменился
    filters_changed = pyqtSignal(dict)         # Фильтры изменились
    sort_changed = pyqtSignal(str, bool)       # (ключ сортировки, reverse)

    def __init__(self, parent=None):
        # Компоненты:
        # - QLineEdit для поиска (с debounce 300ms)
        # - QComboBox для выбора Label
        # - QComboBox для сортировки
        # - QPushButton для дополнительных фильтров (popup)
```

**Элементы UI:**

| Элемент | Тип | Описание |
|---------|-----|----------|
| Поле поиска | QLineEdit | Иконка 🔍, placeholder "Поиск по названию, описанию, аргументам..." |
| Label фильтр | QComboBox | "Все", "recommended", "experimental", "deprecated", "game", etc. |
| Сортировка | QComboBox | "По умолчанию", "По названию А-Я", "По названию Я-А", "По рейтингу", "По дате" |
| Фильтры | QPushButton | Открывает popup с чекбоксами |

### 2. StrategyFilterEngine (Логика фильтрации)

**Файл:** `strategy_menu/filter_engine.py`

```python
@dataclass
class SearchQuery:
    """Структура поискового запроса"""
    text: str = ""                    # Текст поиска
    labels: List[str] = None         # Фильтр по label (None = все)
    has_hostlist: bool = None        # Использует hostlist?
    has_ipset: bool = None           # Использует ipset?
    protocols: List[str] = None      # TCP, UDP, QUIC
    ports: List[int] = None          # Конкретные порты
    techniques: List[str] = None     # fake, split, disorder, etc.


class StrategyFilterEngine:
    """Движок фильтрации стратегий"""

    def filter_strategies(
        self,
        strategies: List[StrategyInfo],
        query: SearchQuery
    ) -> List[StrategyInfo]:
        """
        Фильтрует стратегии по запросу.

        Поиск по тексту ищет в:
        - name (название)
        - description (описание)
        - args (аргументы командной строки)
        - author (автор)
        - comment (комментарий)
        """

    def sort_strategies(
        self,
        strategies: List[StrategyInfo],
        sort_key: str,
        reverse: bool = False
    ) -> List[StrategyInfo]:
        """
        Сортирует стратегии.

        sort_key варианты:
        - "default" - по порядку в файле
        - "name" - по названию
        - "rating" - по рейтингу (из реестра)
        - "label" - по label (recommended первые)
        - "date" - по дате изменения файла
        """

    def group_by_label(
        self,
        strategies: List[StrategyInfo]
    ) -> Dict[str, List[StrategyInfo]]:
        """
        Группирует стратегии по label.

        Возвращает:
        {
            "recommended": [...],
            "experimental": [...],
            "deprecated": [...],
            "unlabeled": [...]
        }
        """
```

### 3. StrategyInfo (Унифицированная структура)

**Файл:** `strategy_menu/strategy_info.py`

```python
@dataclass
class StrategyInfo:
    """Унифицированная информация о стратегии"""

    # Идентификация
    id: str                          # Уникальный ID
    name: str                        # Отображаемое название
    source: str                      # "bat" | "json_tcp" | "json_quic" | etc.

    # Метаданные
    description: str = ""            # Описание
    author: str = ""                 # Автор
    version: str = ""                # Версия
    label: str = ""                  # recommended, experimental, deprecated
    comment: str = ""                # Комментарий

    # Технические данные
    args: str = ""                   # Аргументы командной строки
    file_path: str = ""              # Путь к файлу

    # Анализ (заполняется автоматически)
    protocols: List[str] = None      # ["TCP", "UDP"]
    ports: List[int] = None          # [80, 443]
    techniques: List[str] = None     # ["fake", "split"]
    uses_hostlist: bool = False
    uses_ipset: bool = False

    # Пользовательские данные (из реестра)
    rating: int = 0                  # 0-5 звёзд
    is_favorite: bool = False
    last_used: datetime = None
```

### 4. Адаптеры источников

**Файл:** `strategy_menu/strategy_adapters.py`

```python
class BaseStrategyAdapter(ABC):
    """Базовый адаптер для источника стратегий"""

    @abstractmethod
    def get_all_strategies(self) -> List[StrategyInfo]:
        """Возвращает все стратегии из источника"""

    @abstractmethod
    def get_strategy_by_id(self, strategy_id: str) -> Optional[StrategyInfo]:
        """Возвращает стратегию по ID"""


class BatStrategyAdapter(BaseStrategyAdapter):
    """Адаптер для .bat файлов (Zapret 1 BAT режим)"""

    def __init__(self, bat_folder: str):
        self.bat_folder = bat_folder

    def get_all_strategies(self) -> List[StrategyInfo]:
        # Парсит все .bat файлы
        # Извлекает метаданные из REM комментариев
        # Анализирует аргументы


class JsonStrategyAdapter(BaseStrategyAdapter):
    """Адаптер для JSON стратегий (Direct режимы)"""

    def __init__(self, json_folder: str, category_key: str):
        self.json_folder = json_folder
        self.category_key = category_key

    def get_all_strategies(self) -> List[StrategyInfo]:
        # Загружает JSON файлы
        # Парсит стратегии
        # Заполняет StrategyInfo
```

## Поисковый синтаксис

### Простой поиск
```
youtube          # Ищет "youtube" в названии, описании, аргументах
fake split       # Ищет стратегии содержащие И "fake" И "split"
```

### Расширенный синтаксис (опционально)
```
label:recommended         # Только recommended
port:443                  # Только для порта 443
protocol:udp              # Только UDP
technique:fake            # Использует fake
author:bol-van            # По автору
-deprecated               # Исключить deprecated
"exact phrase"            # Точная фраза
```

## Интеграция с существующим кодом

### Для BAT режима (StrategyTableWithFavoritesFilter)

```python
# В strategy_table_widget_favorites.py

class StrategyTableWithFavoritesFilter(QWidget):
    def __init__(self, ...):
        # Добавляем search bar
        self.search_bar = StrategySearchBar()
        self.search_bar.search_changed.connect(self._on_search)
        self.search_bar.filters_changed.connect(self._on_filters)

        # Движок фильтрации
        self.filter_engine = StrategyFilterEngine()
        self.adapter = BatStrategyAdapter(BAT_FOLDER)

    def _on_search(self, text: str):
        query = SearchQuery(text=text)
        filtered = self.filter_engine.filter_strategies(
            self.adapter.get_all_strategies(),
            query
        )
        self._update_table(filtered)
```

### Для Direct режима (CategoriesTabPanel)

```python
# В categories_tab_panel.py или strategies_page.py

class CategoriesTabPanel(QWidget):
    def __init__(self, ...):
        # Search bar добавляется над вкладками
        self.search_bar = StrategySearchBar()
        self.search_bar.search_changed.connect(self._on_search)

    def _on_search(self, text: str):
        # Фильтрует стратегии внутри текущей вкладки категории
        current_category = self._get_current_category()
        adapter = JsonStrategyAdapter(JSON_FOLDER, current_category)

        query = SearchQuery(text=text)
        filtered = self.filter_engine.filter_strategies(
            adapter.get_all_strategies(),
            query
        )
        self._update_strategies_list(filtered)
```

## UI Дизайн (Windows 11 Fluent)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────┐ ┌─────────┐ ┌─────────┐ │
│ │ 🔍 Поиск стратегий...                   │ │ Label ▼ │ │ Сорт. ▼ │ │
│ └─────────────────────────────────────────┘ └─────────┘ └─────────┘ │
│                                                                     │
│ Найдено: 42 стратегии  |  Фильтры: recommended, TCP                │
└─────────────────────────────────────────────────────────────────────┘
```

**Стили:**
- Поле поиска: rgba(255,255,255,0.05), border-radius: 6px
- Dropdown: Acrylic blur эффект
- Hover эффекты на кнопках
- Анимация появления результатов

## Порядок реализации

1. **Этап 1:** Создать `StrategyInfo` и адаптеры
2. **Этап 2:** Создать `StrategyFilterEngine` с базовым поиском
3. **Этап 3:** Создать `StrategySearchBar` виджет
4. **Этап 4:** Интегрировать в BAT режим
5. **Этап 5:** Интегрировать в Direct режимы
6. **Этап 6:** Добавить расширенный синтаксис поиска
7. **Этап 7:** Добавить группировку по label

## Файловая структура

```
strategy_menu/
├── filter_engine.py        # StrategyFilterEngine
├── strategy_info.py        # StrategyInfo dataclass
├── strategy_adapters.py    # BatStrategyAdapter, JsonStrategyAdapter
└── ...

ui/widgets/
├── strategy_search_bar.py  # StrategySearchBar виджет
└── ...
```
