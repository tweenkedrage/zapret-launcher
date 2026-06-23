# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import json
from config import CONFIG_FILE

class Languages:
    LANGUAGES = {
        'Russian': 'Russian',
        'English': 'English'
    }
    
    TRANSLATIONS = {
        'Russian': {
            'main_title': 'Главная',
            'main_desc': 'Управление подключением и мониторинг состояния',
            'status': 'Статус:',
            'status_ready': 'Готов к работе',
            'status_connected': 'Подключено',
            'mode': 'Режим:',
            'mode_not_selected': 'Не выбран',
            'stats_session': 'Статистика сессии',
            'stats_time': 'время работы',
            'stats_speed': 'Скорость:',
            'stats_rtt': 'RTT:',
            'stats_rtt_ms': 'ms',
            'button_connect': 'ПОДКЛЮЧИТЬСЯ',
            'button_disconnect': 'ОТКЛЮЧИТЬСЯ',

            'update_available': 'Доступно обновление',
            
            'service_title': 'Сервис',
            'service_desc': 'Zapret фильтры',
            'service_filters': 'Фильтры',
            'service_game_filter': 'Game Filter',
            'service_ipset_filter': 'IPSet Filter',
                
            'lists_title': 'Редактор',
            'lists_desc': 'Редактирование списков для обхода блокировок',
            'lists_general': 'Общие',
            'lists_white': 'Исключения',
            'lists_google': 'Браузер',
            'lists_custom': 'Пользовательские',
            'lists_ipset_white': 'IP-исключения',
            'lists_ipset': 'IP-разрешенные',
            'lists_edit': 'Изменить',
            'lists_open_folder': 'Папка с листами',

            'additionally_title': 'Дополнительно',
            'additionally_desc': 'Дополнительные инструменты для разблокировки сервисов',
            'soundcloud_description': 'Добавляет домены для разблокировки SoundCloud в list-custom.txt и ipset-all.txt',
            'meta_description': 'Добавляет домены для разблокировки Facebook и Instagram в list-custom.txt и ipset-all.txt',
            'soundcloud_unblocked': 'SoundCloud разблокирован',
            'meta_unblocked': 'Meta разблокирована',
            'soundcloud_removed': 'Домены SoundCloud удалены',
            'meta_removed': 'Домены Meta удалены',
            'enabled_additionally': 'Разблокирован',
            'disabled_additionally': 'Не разблокирован',
            'enable': 'Включить',
            'disable': 'Отключить',
            
            'traffic_title': 'Трафик',
            'traffic_desc': 'Мониторинг сетевого трафика по процессам',
            'traffic_warning': 'Обновление таблицы может занимать до 60 секунд',
            'traffic_process': 'Процесс',
            'traffic_speed': 'Скорость',
            'traffic_vpn': 'VPN',
            'traffic_direct': 'Прямой',
            'traffic_connections': 'Соед.',
            'traffic_host': 'Хост',
            'traffic_total': 'Всего',
            'traffic_no_connections': 'Нет активных соединений',
            'error_traffic_collection': 'Ошибка сбора трафика',

            'logs_title': 'Логи',
            'logs_desc': 'Журнал событий лаунчера',
            'logs_clear': 'Очистить',
            'logs_refresh': 'Обновить',

            'splash_check_connecting': 'Проверяем подключение к сети..',
            'splash_check_updates': 'Проверяем обновления...',
            'splash_download_update': 'Подготовка к обновлению..',
            'splash_downloading': 'Начинаем загрузку обновления..',
            'splash_downloading_percent': 'Загружено:',
            'splash_downloading_exe': 'Загрузка обновления...',
            'splash_downloading_zip': 'Загрузка внутренних файлов...',
            'splash_extracting_files': 'Распаковка файлов...',
            'splash_remove_old': 'Удаление старых файлов...',
            'splash_extracting': 'Распаковка...',
            'splash_downloading_zapret': 'Загрузка zapret...',
            'splash_extracting_zapret': 'Распаковка zapret...',
            'splash_updating_zapret': 'Обновление zapret...',
            'splash_stopping_processes': 'Остановка процессов...',
            'splash_install_update': 'Устанавливаем обновление...',
            'splash_starting_exe': 'Запуск лаунчера..',
            'splash_update_error': 'Ошибка обновления!',
            'splash_help_update': 'Ошибка обновления? Ручная установка',
            'splash_check_connect_error': 'Ошибка подключения к сети',
                        
            'settings_title': 'Настройки',
            'settings_desc': 'Настройка интерфейса и параметров работы',
            'settings_interface': 'Обновление интерфейса',
            'settings_interval_fast': 'Быстро',
            'settings_interval_5': '5 секунд',
            'settings_interval_10': '10 секунд',
            'settings_interval_30': '30 секунд',
            'settings_interval_60': '60 секунд',
            'settings_interval_off': 'Не обновлять',
            'settings_interval_fast_small': '1 сек',
            'settings_interval_5_small': '5 сек',
            'settings_interval_10_small': '10 сек',
            'settings_interval_30_small': '30 сек',
            'settings_interval_60_small': '60 сек',
            'settings_interval_off_small': 'выкл',
            'settings_current': 'Текущие настройки',
            'settings_current_interval': 'Обновление интерфейса:',
            'settings_interval_fast_text': 'быстро',
            'settings_interval_off_text': 'отключено',
            'settings_theme': 'Оформление',
            'settings_language': 'Язык / Language',
            'settings_recovery': 'Лаунчер',
            'settings_integrity': 'Проверить целостность',
            'settings_integrity_title': 'Проверка целостности',
            'settings_reinstall': 'Переустановить zapret',
            'settings_reinstall_title': 'Переустановка ядра',
            'settings_integrity_folder_missing': 'папка отсутствует',
            'settings_integrity_result': 'Результат:',
            'settings_integrity_missing_count': 'Отсутствует файлов: {count}',
            'settings_integrity_success': 'Результат:\nВсе файлы имеются',
            'settings_reinstall_all_exists': 'Все файлы ядра уже имеются\nВы точно хотите переустановить их?',
            'settings_reinstall_missing': 'Обнаружены отсутствующие файлы ядра\nПереустановить?',
            'settings_reinstall_active': 'Активное подключение',
            'settings_reinstall_disconnect': 'Для переустановки ядра необходимо отключить активное подключение\nОтключиться и продолжить?',
            'settings_current_tg_secret': 'Текущий секрет:',
            'settings_open_folder': 'Открыть папку',
            'settings_autostart': 'Автозапуск',
            
            'mode_standard': 'Стандартный',
            'mode_standard_desc': 'Обход блокировок через Zapret',
            'mode_tgproxy_desc': 'Ускорение работы Telegram',
            'mode_zapret_tgproxy': 'Совместный',
            'mode_zapret_tgproxy_desc': 'Zapret и Telegram Proxy',
            'mode_select_title': 'Выбор режима',
            'mode_select': 'Выберите режим запуска',
            'mode_select_button': 'Выбрать',
            'mode_cancel': 'Отмена',
            
            'notification_save_settings': 'Перезапустите Telegram Proxy',
            'notification_copied': 'Ссылка скопирована',
            'notification_copied_secret': 'Секрет-ключ скопирован',
            'notification_updated_secret': 'Секрет-ключ обновлен',
            'notification_interval_fast': 'Обновление интерфейса: быстро',
            'notification_interval_5': 'Обновление интерфейса: 5 секунд',
            'notification_interval_10': 'Обновление интерфейса: 10 секунд',
            'notification_interval_30': 'Обновление интерфейса: 30 секунд',
            'notification_interval_60': 'Обновление интерфейса: 60 секунд',
            'notification_interval_off': 'Обновление интерфейса: отключено',
            
            'dialog_exit': 'Выход',
            'dialog_exit_message': 'Активное подключение будет разорвано\nВы действительно хотите закрыть лаунчер?',
            'dialog_no_connection': 'Лаунчер не может работать без прав администратора',
            'dialog_admin_message': 'Лаунчер требует прав администратора для работы\nЗапустить от имени администратора?',
            'restart_manual_title': 'Требуется перезапуск',
            'restart_manual_message': 'Настройки сохранены\nНажмите "Ок", чтобы перезапустить лаунчер',

            'vpn_detected_title': 'Обнаружен VPN',
            'vpn_detected_message': 'Обнаружен активное подключение к VPN-клиенту, рекомендуется его отключить',
            'vpn_detected_processes': 'Найденные процессы',
            'vpn_detected_interfaces': 'Найденные интерфейсы',
            'vpn_ignore': 'Игнорировать',
            'vpn_disable': 'Отключить VPN',
            'vpn_disabled_notification': 'Остановлено {} VPN процессов',
            'vpn_no_processes_to_kill': 'Не найдено процессов VPN для остановки',
                        
            'tg_instruction_title': 'Настройка Telegram',
            'tg_instruction_subtitle': 'Для использования прокси выполните следующие шаги:',
            'tg_generate_secret': 'Сгенерировать секрет-ключ',
            'tg_instruction_show_hide': 'Показывать инструкцию',
            'tg_copy_secret': 'Скопировать секрет-ключ',
            'tg_step1': 'Откройте Telegram и перейдите в',
            'tg_step1_desc': 'Настройки - Продвинутые настройки',
            'tg_step2': 'В разделе «Тип соединения» выберите:',
            'tg_step2_desc': 'Использовать собственный прокси',
            'tg_step3': 'Заполните поля прокси:',
            'tg_type': 'Тип: MTPROTO',
            'tg_host': 'Хост: указан на главной странице',
            'tg_port': 'Порт: указан на главной странице',
            'tg_secret': 'Secret: (Генерируется автоматически)',
            'tg_copy_link': 'Скопировать ссылку подключения',
            'tg_copied': 'Скопировано',
            'tg_dont_show': 'Больше не показывать',
            'tg_instruction_hidden': 'Инструкция скрыта',
            'tg_instruction_shown': 'Инструкция доступна',

            'instruction_title_window': 'Инструкция',
            'edit_title_window': 'Редактирование',

            'hosts_instruction_title': 'Доступ к Telegram Web',
            'hosts_instruction_subtitle': 'Для использования Web версии выполните следующие шаги:',
            'hosts_step1': 'Откройте "Блокнот" от имени администратора',
            'hosts_step2': 'Файл - Открыть:',
            'hosts_step2_desc': 'Путь: C:\Windows\System32\drivers\etc\hosts',
            'hosts_step3': 'Добавьте следующие домены в конец файла:',
            'hosts_step4': 'Сохраните файл (Ctrl+S)',
            'hosts_step5': 'Перезапустите браузер для применения изменений',
            'hosts_desc_on_page': 'Добавляет IP адреса Telegram в файл hosts',
            'hosts_copy_lines': 'Скопировать все строки',
            'hosts_copied_notification': 'Строки скопированы в буфер обмена',
            'hosts_button_unblock': 'Открыть',

            'ghub_instruction_title': 'Доступ к GitHub',
            'ghub_instruction_subtitle': 'Возвращение доступа к сервису:',
            'ghub_step1': 'Перейдите в страницу Редактор и откройте list-custom',
            'ghub_step2': 'Вставьте в конец файла домены, которые вы можете скопировать ниже',
            'ghub_step3': 'Сохраните файл и запустите командную строку без имени администратора',
            'ghub_step4': 'Введите: ping github.com и после скопируйте IP, который был выведен',
            'ghub_step5': 'Вернитесь в страницу Редактор и откройте IPSet-all',
            'ghub_step6': 'Вставьте IP в конец файла в таком формате: 127.0.0.1/32',
            'ghub_step7': 'Сохраните файл, перейдите в страницу Сервис и там выберите IPSet - loaded',
            'ghub_step8': 'Запустите любой режим где есть Zapret (Стандартный или Совместный)',
            'ghub_desc_on_page': 'Восстановление доступа к GitHub через zapret',
            'ghub_copy_lines': 'Скопировать домены',
            'ghub_copied_notification': 'Домены скопированы в буфер обмена',
            'ghub_button_unblock': 'Открыть',
            
            'error_update_check': 'Не удалось проверить обновления',
            'error_no_strategies': 'Нет доступных стратегий Zapret',
            'error_select_strategy': 'Выберите стратегию',
            'error_zapret_folder': 'Папка с Zapret не найдена!',
            'error_tgproxy_start': 'Не удалось запустить Telegram Proxy',
            'error_tgproxy_timeout': 'Таймаут запуска',
            'error_admin_required': 'Требуются права администратора!',
            'error_strategy_not_found': 'Стратегия не найдена:',
            'error_winws_not_found': 'Стратегия запущена, но winws.exe не обнаружен',
            'error_secret_not_found': 'Секрет-ключ не найден',
            'error_secret_not_generate': 'Секрет-ключ не сгенерирован',
            'error_telegram_proxy_start': 'Сначала запустите Telegram Proxy режим',
            'error_startup': 'Ошибка запуска',
            'error_icon_not_found': 'Иконка не найдена',
            'error_unknown_command': 'Неизвестная команда',
            'error_autostart': 'Ошибка настройки автозапуска',
            'error_port_have_words': 'Порт должен содержать число',
            'error_no_connection': 'Ошибка',
            'error_warning': 'Предупреждение',
            'error_occurred': 'Произошла ошибка',

            'tg_secret_required_message': 'Для работы Telegram Proxy требуется секрет-ключ.\n\nСгенерировать новый секрет и продолжить?',
            'tg_secret_updated': 'Секрет-ключ обновлен',
            'tg_secret_new': 'Новый секрет:',
            'tg_paste_instruction': 'Вставьте его в Telegram для подключения',
                        
            'status_connecting': 'Запуск...',
            'status_disconnecting': 'Отключение...',
            'status_starting': 'Подключение...',
            'status_error': 'Ошибка запуска',
            'status_strategy_started': 'Запущена стратегия:',
            'status_enabled': 'включен',
            'status_disabled': 'выключен',
            'restart_zapret': 'Перезапустите zapret',
            
            'main_page_tg_proxy_host': 'Хост',
            'main_page_tg_proxy_port': 'Порт',
            'main_page_tg_proxy_domain': 'Домен',
            
            'autostart_enabled': 'Автозапуск включен',
            'autostart_disabled': 'Автозапуск отключен',
            'autostart_error': 'Не удалось изменить настройки автозапуска',
            
            'editor_title': 'Редактирование',
            'editor_save': 'Сохранить',
            'editor_cancel': 'Отмена',
            'editor_success': 'Файл успешно сохранен',
            'editor_error_load': 'Не удалось загрузить файл',
            'editor_error_save': 'Не удалось сохранить файл',
            'editor_find': 'Найти:',
            'editor_find_next': 'Далее',
            'editor_close': 'Закрыть',
            'editor_enter_text': 'Введите текст для поиска',
            'editor_not_found': 'не найден',
            'editor_tooltip': 'Ctrl+F — поиск | Esc — закрыть',
            
            'menu_open': 'Открыть',
            'menu_connect': 'Подключиться',
            'menu_disconnect': 'Отключиться',
            'menu_settings': 'Настройки',
            'menu_settings_interface': 'Изменить скорость интерфейса',
            'menu_settings_folder': 'Открыть папку с лаунчером',
            'menu_help': 'Помощь',
            'menu_help_release': 'Список изменений',
            'menu_help_report': 'Сообщить об ошибке',
            'menu_help_idea': 'Предложить идею',
            'menu_help_readme': 'Документация',
            'menu_help_logs': 'Логи',
            'menu_exit': 'Выход',
            
            'button_start': 'Запустить',
            'button_apply': 'Применить',
            'button_close': 'Закрыть',
            'button_restart': 'Перезапустить',
            
            'select_strategy': 'Выбор стратегии Zapret',
            'select_strategy_title': 'Выбор стратегии',
            'available_strategies': 'Доступные стратегии:',
            'selected': 'Выбрано:',

            'update_title': 'Обновление Zapret Launcher',
            'update_available_question': 'Доступна новая версия',
            'update_ask_now': 'Хотите обновиться прямо сейчас?',

            'seconds': 'сек',
            'please_wait': 'Пожалуйста, подождите...',
            
            'success': 'Успех',
            'is_empty': 'пустой',
            'not_found': 'отсутствует',
            'files': 'файлов',
            'strategies_count': 'Стратегии',
        },
        
        'English': {
            'main_title': 'Home',
            'main_desc': 'Connection management and monitoring',
            'status': 'Status:',
            'status_ready': 'Ready',
            'status_connected': 'Connected',
            'mode': 'Mode:',
            'mode_not_selected': 'Not selected',
            'stats_session': 'Session statistics',
            'stats_time': 'uptime',
            'stats_speed': 'Speed:',
            'stats_rtt': 'RTT:',
            'stats_rtt_ms': 'ms',
            'button_connect': 'CONNECT',
            'button_disconnect': 'DISCONNECT',

            'update_available': 'Update available',
            
            'service_title': 'Service',
            'service_desc': 'Zapret filters',
            'service_filters': 'Filters',
            'service_game_filter': 'Game Filter',
            'service_ipset_filter': 'IPSet Filter',
            
            'lists_title': 'Editor',
            'lists_desc': 'Edit lists for bypassing blocks',
            'lists_general': 'General',
            'lists_white': 'Exceptions',
            'lists_google': 'Browser',
            'lists_custom': 'Custom',
            'lists_ipset_white': 'IP-exceptions',
            'lists_ipset': 'IP-allowed',
            'lists_edit': 'Edit',
            'lists_open_folder': 'Lists folder',

            'additionally_title': 'Additionally',
            'additionally_desc': 'Additional tools for unblocking services',
            'soundcloud_description': 'Adds domains for unblocking SoundCloud to list-custom.txt and ipset-all.txt',
            'meta_description': 'Adds domains to unblock Facebook and Instagram to list-custom.txt and ipset-all.txt',
            'soundcloud_unblocked': 'SoundCloud is unblocked',
            'meta_unblocked': 'Meta is unblocked',
            'soundcloud_removed': 'SoundCloud domains removed',
            'meta_removed': 'Meta domains removed',
            'enabled_additionally': 'Unlocked',
            'disabled_additionally': 'Not unlocked',
            'enable': 'Enable',
            'disable': 'Disable',
            
            'traffic_title': 'Traffic',
            'traffic_desc': 'Network traffic monitoring by process',
            'traffic_warning': 'Updating a table can take up to 60 seconds',
            'traffic_process': 'Process',
            'traffic_speed': 'Speed',
            'traffic_vpn': 'VPN',
            'traffic_direct': 'Direct',
            'traffic_connections': 'Conn.',
            'traffic_host': 'Host',
            'traffic_total': 'Total',
            'traffic_no_connections': 'No active connections',
            'error_traffic_collection': 'Traffic collection error',

            'logs_title': 'Logs',
            'logs_desc': 'Launcher event log',
            'logs_clear': 'Clear',
            'logs_refresh': 'Refresh',

            'splash_check_connecting': 'Checking your network..',
            'splash_check_updates': 'Checking for updates...',
            'splash_download_update': 'Preparing for the update..',
            'splash_downloading': 'Starting to download the update..',
            'splash_downloading_percent': 'Uploaded:',
            'splash_install_update': 'Installing update...',
            'splash_starting_exe': 'Starting..',
            'splash_downloading_exe': 'Downloading executable...',
            'splash_downloading_zip': 'Downloading files...',
            'splash_extracting_files': 'Extracting files...',
            'splash_remove_old': 'Removing old files...',
            'splash_extracting': 'Extracting...',
            'splash_downloading_zapret': 'Downloading zapret...',
            'splash_updating_zapret': 'Updating zapret...',
            'splash_extracting_zapret': 'Extracting zapret...',
            'splash_stopping_processes': 'Stopping processes...',
            'splash_update_error': 'Update error!',
            'splash_help_update': 'Update error? Manual installation',
            'splash_check_connect_error': 'Network connection error',
            
            'settings_title': 'Settings',
            'settings_desc': 'Interface and operation settings',
            'settings_interface': 'Interface refresh',
            'settings_interval_fast': 'Fast',
            'settings_interval_5': '5 seconds',
            'settings_interval_10': '10 seconds',
            'settings_interval_30': '30 seconds',
            'settings_interval_60': '60 seconds',
            'settings_interval_off': 'Disabled',
            'settings_interval_fast_small': '1 sec',
            'settings_interval_5_small': '5 sec',
            'settings_interval_10_small': '10 sec',
            'settings_interval_30_small': '30 sec',
            'settings_interval_60_small': '60 sec',
            'settings_interval_off_small': 'off',
            'settings_current': 'Current settings',
            'settings_current_interval': 'Interface refresh:',
            'settings_interval_fast_text': 'fast',
            'settings_interval_off_text': 'disabled',
            'settings_theme': 'Theme',
            'settings_language': 'Language',
            'settings_recovery': 'Launcher',
            'settings_integrity': 'Check integrity',
            'settings_integrity_title': 'Integrity check',
            'settings_reinstall': 'Reinstall zapret',
            'settings_reinstall_title': 'Reinstalling the core',
            'settings_integrity_folder_missing': 'folder missing',
            'settings_integrity_result': 'Result:',
            'settings_integrity_missing_count': 'Missing files: {count}',
            'settings_integrity_success': 'Result:\nAll files are present',
            'settings_reinstall_all_exists': 'All core files are already present\nAre you want to reinstall them?',
            'settings_reinstall_missing': 'Missing core files detected\nReinstall?',
            'settings_reinstall_active': 'Active connection',
            'settings_reinstall_disconnect': 'To reinstall the core, you must disconnect the active connection\nDisconnect and continue?',
            'settings_current_tg_secret': 'Current secret:',
            'settings_open_folder': 'Open folder',
            'settings_autostart': 'Autostart',
            
            'mode_standard': 'Standard',
            'mode_standard_desc': 'Bypass blocks via Zapret',
            'mode_tgproxy_desc': 'Telegram acceleration',
            'mode_zapret_tgproxy': 'Combined',
            'mode_zapret_tgproxy_desc': 'Zapret and Telegram Proxy',
            'mode_select_title': 'Select mode',
            'mode_select': 'Select launch mode',
            'mode_select_button': 'Select',
            'mode_cancel': 'Cancel',
            
            'notification_save_settings': 'Restart Telegram Proxy',
            'notification_copied': 'Link copied',
            'notification_copied_secret': 'Secret-key copied',
            'notification_updated_secret': 'Secret-key updated',
            'notification_interval_fast': 'Interface refresh: fast',
            'notification_interval_5': 'Interface refresh: 5 seconds',
            'notification_interval_10': 'Interface refresh: 10 seconds',
            'notification_interval_30': 'Interface refresh: 30 seconds',
            'notification_interval_60': 'Interface refresh: 60 seconds',
            'notification_interval_off': 'Interface refresh: disabled',
            
            'dialog_exit': 'Exit',
            'dialog_exit_message': 'Active connection will be terminated\nDo you really want to close the launcher?',
            'dialog_no_connection': 'Launcher cannot run without administrator rights',
            'dialog_admin_message': 'Launcher requires administrator rights to run\nRun as administrator?',
            'restart_manual_title': 'Restart Required',
            'restart_manual_message': 'Settings has been saved\nClick "OK" to restart the launcher',

            'vpn_detected_title': 'VPN Detected',
            'vpn_detected_message': 'An active VPN client connection has been detected, it is recommended to disable it',
            'vpn_detected_processes': 'Detected processes',
            'vpn_detected_interfaces': 'Detected interfaces',
            'vpn_ignore': 'Ignore',
            'vpn_disable': 'Disable VPN',
            'vpn_disabled_notification': 'Stopped {} VPN processes',
            'vpn_no_processes_to_kill': 'No VPN processes found to stop',
            
            'tg_instruction_title': 'Telegram Setup',
            'tg_instruction_subtitle': 'To use the proxy, follow these steps:',
            'tg_generate_secret': 'Generate secret-key',
            'tg_instruction_show_hide': 'Show instruction',
            'tg_copy_secret': 'Copy the secret-key',
            'tg_step1': 'Open Telegram and go to',
            'tg_step1_desc': 'Settings - Advanced Settings',
            'tg_step2': 'In the "Connection Type" section select:',
            'tg_step2_desc': 'Use custom proxy',
            'tg_step3': 'Fill in the proxy fields:',
            'tg_type': 'Type: MTPROTO',
            'tg_host': 'Host: listed on the main page',
            'tg_port': 'Port: listed on the main page',
            'tg_secret': 'Secret: (auto-generated)',
            'tg_copied': 'Copied',
            'tg_dont_show': 'Don\'t show again',
            'tg_instruction_hidden': 'Instruction unavailable',
            'tg_instruction_shown': 'Instruction available',

            'instruction_title_window': 'Instruction',
            'edit_title_window': 'Editing',

            'hosts_instruction_title': 'Unblock Telegram Web',
            'hosts_instruction_subtitle': 'To use the Web version, follow these steps:',
            'hosts_step1': 'Open Notepad as administrator',
            'hosts_step2': 'File - Open:',
            'hosts_step2_desc': 'Path: C:\Windows\System32\drivers\etc\hosts',
            'hosts_step3': 'Add the following domains to the end of the file:',
            'hosts_desc_on_page': 'Adds Telegram IP addresses to the hosts file',
            'hosts_step4': 'Save the file (Ctrl+S)',
            'hosts_step5': 'Restart your browser to apply changes',
            'hosts_copy_lines': 'Copy all lines',
            'hosts_copied_notification': 'Lines copied to clipboard',
            'hosts_button_unblock': 'Open',

            'ghub_instruction_title': 'Unblock GitHub',
            'ghub_instruction_subtitle': 'Restoring access to the service:',
            'ghub_step1': 'Go to the Editor page and open list-custom',
            'ghub_step2': 'Paste the domains you can copy below at the end of the file',
            'ghub_step3': 'Save file and run the command prompt without administrator name',
            'ghub_step4': 'Type: ping github.com and then copy the IP that was displayed',
            'ghub_step5': 'Return to the Editor page and open IPSet-all',
            'ghub_step6': 'Paste the IP at the end of the file in this format: 127.0.0.1/32',
            'ghub_step7': 'Save file, go to the Service page and select IPSet - loaded',
            'ghub_step8': 'Launch any mode where there is Zapret (Standard or Combined)',
            'ghub_desc_on_page': 'Restoring access to GitHub after a zapret',
            'ghub_copy_lines': 'Copy domains',
            'ghub_copied_notification': 'Domains copied to clipboard',
            'ghub_button_unblock': 'Open',
            
            'error_update_check': 'Failed to check for updates',
            'error_no_strategies': 'No Zapret strategies available',
            'error_select_strategy': 'Select a strategy',
            'error_zapret_folder': 'Zapret folder not found!',
            'error_tgproxy_start': 'Failed to start Telegram Proxy',
            'error_tgproxy_timeout': 'Startup timeout',
            'error_admin_required': 'Administrator rights required!',
            'error_strategy_not_found': 'Strategy not found:',
            'error_winws_not_found': 'Strategy started but winws.exe not detected',
            'error_secret_not_found': 'Secret-key not found',
            'error_secret_not_generate': 'The secret key was not generated',
            'error_telegram_proxy_start': 'First, launch Telegram Proxy mode',
            'error_startup': 'Startup error',
            'error_unknown_command': 'Unknown command',
            'error_autostart': 'Autostart configuration error',
            'error_port_have_words': 'Port must contain numbers',
            'error_no_connection': 'Error',
            'error_warning': 'Warning',
            'error_occurred': 'Error occurred',

            'tg_secret_required_message': 'A secret-key is required for Telegram Proxy to work.\n\nGenerate a new secret and continue?',
            'tg_secret_updated': 'Secret-key updated',
            'tg_secret_new': 'New secret:',
            'tg_paste_instruction': 'Paste it into Telegram to connect.',
            'tg_proxy_restarted': 'Proxy restarted with new secret.',
                        
            'status_connecting': 'Starting...',
            'status_disconnecting': 'Disconnecting...',
            'status_starting': 'Connecting...',
            'status_error': 'Startup error',
            'status_strategy_started': 'Strategy started:',
            'status_enabled': 'enabled',
            'status_disabled': 'disabled',
            'restart_zapret': 'Restart the zapret',

            'main_page_tg_proxy_host': 'Host',
            'main_page_tg_proxy_port': 'Port',
            'main_page_tg_proxy_domain': 'Domain',
            
            'autostart_enabled': 'Autostart enabled',
            'autostart_disabled': 'Autostart disabled',
            'autostart_error': 'Failed to change autostart settings',
            
            'editor_title': 'Editing',
            'editor_save': 'Save',
            'editor_cancel': 'Cancel',
            'editor_success': 'File saved successfully',
            'editor_error_load': 'Failed to load file',
            'editor_error_save': 'Failed to save file',
            'editor_find': 'Find:',
            'editor_find_next': 'Next',
            'editor_close': 'Close',
            'editor_enter_text': 'Enter text to search',
            'editor_not_found': 'not found',
            'editor_tooltip': 'Ctrl+F — search | Esc — close',
            
            'menu_open': 'Open',
            'menu_connect': 'Connect',
            'menu_disconnect': 'Disconnect',
            'menu_settings': 'Settings',
            'menu_settings_interface': 'Change interface speed',
            'menu_settings_folder': 'Open launcher folder',
            'menu_help': 'Help',
            'menu_help_release': 'Release notes',
            'menu_help_report': 'Report a bug',
            'menu_help_idea': 'Propose an idea',
            'menu_help_readme': 'Documentation',
            'menu_help_logs': 'Logs',
            'menu_exit': 'Exit',
            
            'button_start': 'Start',
            'button_apply': 'Apply',
            'button_close': 'Close',
            'button_restart': 'Restart',
            
            'select_strategy': 'Select Zapret strategy',
            'select_strategy_title': 'Select strategy',
            'available_strategies': 'Available strategies:',
            'selected': 'Selected:',

            'update_title': 'Update Zapret Launcher',
            'update_available_question': 'New version available',
            'update_ask_now': 'Want to upgrade now?',

            'seconds': 'sec',
            'please_wait': 'Please, wait...',
            
            'success': 'Success',
            'not_found': 'is missing',
            'files': 'files',
            'strategies_count': 'Strategies',
        }
    }
    
    def __init__(self):
        self._current_lang = 'Russian'
        self._config_file = CONFIG_FILE
        self.load_language()
    
    def load_language(self):
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    lang = data.get('language', 'Russian')
                    if lang in self.LANGUAGES:
                        self._current_lang = lang
        except:
            pass
    
    def save_language(self):
        try:
            data = {}
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data['language'] = self._current_lang
            
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def set_language(self, lang_code: str) -> bool:
        if lang_code in self.LANGUAGES:
            self._current_lang = lang_code
            self.save_language()
            return True
        return False
    
    def get_current_language(self) -> str:
        return self._current_lang
    
    def get_language_name(self) -> str:
        return self.LANGUAGES.get(self._current_lang, 'Russian')
    
    def get_available_languages(self) -> dict:
        return self.LANGUAGES.copy()
    
    def tr(self, key: str, **kwargs) -> str:
        text = self.TRANSLATIONS.get(self._current_lang, {}).get(key, key)
        
        if kwargs:
            for k, v in kwargs.items():
                text = text.replace(f'{{{k}}}', str(v))
        
        return text

_languages = None

def get_languages() -> Languages:
    global _languages
    if _languages is None:
        _languages = Languages()
    return _languages

def tr(key: str, **kwargs) -> str:
    return get_languages().tr(key, **kwargs)

def set_language(lang_code: str) -> bool:
    return get_languages().set_language(lang_code)

def get_current_language() -> str:
    return get_languages().get_current_language()

def get_available_languages() -> dict:
    return get_languages().get_available_languages()
