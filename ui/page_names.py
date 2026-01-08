"""
Именованные константы для навигации по страницам.
Используй эти Enum вместо числовых индексов!

Пример использования:
    from ui.page_names import PageName, SectionName, SECTION_TO_PAGE

    # В main_window.py:
    self.show_page(PageName.LOGS)

    # В sidebar.py:
    page = SECTION_TO_PAGE[SectionName.LOGS]
"""

from enum import Enum, auto
from typing import Optional


class PageName(Enum):
    """Имена страниц в pages_stack (QStackedWidget)

    Порядок значений НЕ ВАЖЕН - это просто уникальные идентификаторы.
    Фактический индекс в стеке определяется порядком добавления виджетов.
    """

    # === Основные страницы ===
    HOME = auto()                    # Главная
    CONTROL = auto()                 # Управление DPI
    ZAPRET2_DIRECT = auto()          # Zapret 2 Direct стратегии
    ZAPRET2_ORCHESTRA = auto()       # Zapret 2 Orchestra (direct_zapret2_orchestra режим)
    ZAPRET1_DIRECT = auto()          # Zapret 1 Direct стратегии
    BAT_STRATEGIES = auto()          # BAT стратегии
    STRATEGY_DETAIL = auto()         # Детальный просмотр стратегии
    STRATEGY_SORT = auto()           # Сортировка стратегий
    PRESET_CONFIG = auto()           # Конфиг preset-zapret2.txt
    HOSTLIST = auto()                # Hostlist
    IPSET = auto()                   # IPset
    BLOBS = auto()                   # Блобы
    EDITOR = auto()                  # Редактор стратегий
    DPI_SETTINGS = auto()            # Настройки DPI
    PRESETS = auto()                 # Пресеты настроек (только direct_zapret2)

    # === Мои списки ===
    NETROGAT = auto()                # Исключения (netrogat.txt)
    CUSTOM_DOMAINS = auto()          # Мои hostlist (other2.txt)
    CUSTOM_IPSET = auto()            # Мои ipset (my-ipset.txt)

    # === Настройки системы ===
    AUTOSTART = auto()               # Автозапуск
    NETWORK = auto()                 # Сеть
    CONNECTION_TEST = auto()         # Диагностика соединения
    DNS_CHECK = auto()               # DNS подмена
    HOSTS = auto()                   # Разблокировка сервисов
    BLOCKCHECK = auto()              # BlockCheck
    APPEARANCE = auto()              # Оформление
    PREMIUM = auto()                 # Донат/Premium
    LOGS = auto()                    # Логи
    SERVERS = auto()                 # Серверы обновлений
    ABOUT = auto()                   # О программе

    # === Оркестратор (автообучение) ===
    ORCHESTRA = auto()               # Оркестр - главная
    ORCHESTRA_LOCKED = auto()        # Залоченные стратегии
    ORCHESTRA_BLOCKED = auto()       # Заблокированные стратегии
    ORCHESTRA_WHITELIST = auto()     # Белый список
    ORCHESTRA_RATINGS = auto()       # История с рейтингами


class SectionName(Enum):
    """Имена секций в sidebar (навигационные кнопки)

    Секции - это кнопки в боковой панели. Они могут быть:
    - Обычные (открывают страницу)
    - Collapsible (разворачивают подменю)
    - Header (заголовок группы, не кликабельный)
    """

    # === Главное меню ===
    HOME = auto()                    # Главная
    CONTROL = auto()                 # Управление

    # === Стратегии (collapsible группа) ===
    STRATEGIES = auto()              # Заголовок группы (collapsible)
    STRATEGY_SORT = auto()           # - Сортировка
    PRESET_CONFIG = auto()           # - Конфиг
    HOSTLIST = auto()                # - Hostlist
    IPSET = auto()                   # - IPset
    BLOBS = auto()                   # - Блобы
    EDITOR = auto()                  # - Редактор
    ORCHESTRA_LOCKED = auto()        # - Залоченные
    ORCHESTRA_BLOCKED = auto()       # - Заблокированные
    ORCHESTRA_RATINGS = auto()       # - Рейтинги
    DPI_SETTINGS = auto()            # - Настройки DPI
    PRESETS = auto()                 # - Пресеты настроек

    # === Мои списки (collapsible группа) ===
    MY_LISTS_HEADER = auto()         # Заголовок группы (header, не страница!)
    NETROGAT = auto()                # - Исключения
    ORCHESTRA_WHITELIST = auto()     # - Белый список
    CUSTOM_HOSTLIST = auto()         # - Мои hostlist
    CUSTOM_IPSET = auto()            # - Мои ipset

    # === Основные пункты ===
    AUTOSTART = auto()               # Автозапуск
    NETWORK = auto()                 # Сеть

    # === Диагностика (collapsible группа) ===
    DIAGNOSTICS = auto()             # Заголовок группы (collapsible)
    DNS_CHECK = auto()               # - DNS подмена

    # === Остальные пункты ===
    HOSTS = auto()                   # Hosts
    BLOCKCHECK = auto()              # BlockCheck
    APPEARANCE = auto()              # Оформление
    PREMIUM = auto()                 # Донат
    LOGS = auto()                    # Логи
    SERVERS = auto()                 # Обновления
    ABOUT = auto()                   # О программе


# Маппинг Section -> Page (какую страницу открывать при клике на секцию)
# None означает что секция collapsible - при клике определяется динамически в main_window
SECTION_TO_PAGE: dict[SectionName, Optional[PageName]] = {
    SectionName.HOME: PageName.HOME,
    SectionName.CONTROL: PageName.CONTROL,
    SectionName.STRATEGIES: None,  # Collapsible группа, целевая страница определяется по методу запуска
    SectionName.STRATEGY_SORT: PageName.STRATEGY_SORT,
    SectionName.PRESET_CONFIG: PageName.PRESET_CONFIG,
    SectionName.HOSTLIST: PageName.HOSTLIST,
    SectionName.IPSET: PageName.IPSET,
    SectionName.BLOBS: PageName.BLOBS,
    SectionName.EDITOR: PageName.EDITOR,
    SectionName.ORCHESTRA_LOCKED: PageName.ORCHESTRA_LOCKED,
    SectionName.ORCHESTRA_BLOCKED: PageName.ORCHESTRA_BLOCKED,
    SectionName.ORCHESTRA_RATINGS: PageName.ORCHESTRA_RATINGS,
    SectionName.DPI_SETTINGS: PageName.DPI_SETTINGS,
    SectionName.PRESETS: PageName.PRESETS,
    SectionName.MY_LISTS_HEADER: None,  # Заголовок, нет страницы!
    SectionName.NETROGAT: PageName.NETROGAT,
    SectionName.ORCHESTRA_WHITELIST: PageName.ORCHESTRA_WHITELIST,
    SectionName.CUSTOM_HOSTLIST: PageName.CUSTOM_DOMAINS,
    SectionName.CUSTOM_IPSET: PageName.CUSTOM_IPSET,
    SectionName.AUTOSTART: PageName.AUTOSTART,
    SectionName.NETWORK: PageName.NETWORK,
    SectionName.DIAGNOSTICS: PageName.CONNECTION_TEST,
    SectionName.DNS_CHECK: PageName.DNS_CHECK,
    SectionName.HOSTS: PageName.HOSTS,
    SectionName.BLOCKCHECK: PageName.BLOCKCHECK,
    SectionName.APPEARANCE: PageName.APPEARANCE,
    SectionName.PREMIUM: PageName.PREMIUM,
    SectionName.LOGS: PageName.LOGS,
    SectionName.SERVERS: PageName.SERVERS,
    SectionName.ABOUT: PageName.ABOUT,
}


# Collapsible секции (которые можно сворачивать)
COLLAPSIBLE_SECTIONS: set[SectionName] = {
    SectionName.STRATEGIES,
    SectionName.MY_LISTS_HEADER,
    SectionName.DIAGNOSTICS,
}


# Подсекции для каждой collapsible группы
SECTION_CHILDREN: dict[SectionName, list[SectionName]] = {
    SectionName.STRATEGIES: [
        SectionName.STRATEGY_SORT,
        SectionName.PRESET_CONFIG,
        SectionName.HOSTLIST,
        SectionName.IPSET,
        SectionName.BLOBS,
        SectionName.EDITOR,
        SectionName.ORCHESTRA_LOCKED,
        SectionName.ORCHESTRA_BLOCKED,
        SectionName.ORCHESTRA_RATINGS,
        SectionName.DPI_SETTINGS,
        SectionName.PRESETS,
    ],
    SectionName.MY_LISTS_HEADER: [
        SectionName.NETROGAT,
        SectionName.ORCHESTRA_WHITELIST,
        SectionName.CUSTOM_HOSTLIST,
        SectionName.CUSTOM_IPSET,
    ],
    SectionName.DIAGNOSTICS: [
        SectionName.DNS_CHECK,
    ],
}


# Секции которые показываются только в режиме оркестратора
ORCHESTRA_ONLY_SECTIONS: set[SectionName] = {
    SectionName.ORCHESTRA_LOCKED,
    SectionName.ORCHESTRA_BLOCKED,
    SectionName.ORCHESTRA_RATINGS,
    SectionName.ORCHESTRA_WHITELIST,
}


# Страницы стратегий (для переключения по режиму запуска)
STRATEGY_PAGES: set[PageName] = {
    PageName.ZAPRET2_DIRECT,
    PageName.ZAPRET2_ORCHESTRA,
    PageName.ZAPRET1_DIRECT,
    PageName.BAT_STRATEGIES,
    PageName.STRATEGY_DETAIL,
    PageName.ORCHESTRA,
}
