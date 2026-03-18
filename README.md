# zapret-launcher
Обход ограничений и ускорение Telegram`a в РФ

На **GitHub`e** имеются **zapret-discord-youtube** и **tg-ws-proxy**, и лично мне надоело их по отдельности включать, поэтому я решил сделать общий лаунчер куда я объединил всё в одно.

***Установка:***
1. Скачивайте архив и распаковывайте в любое место;
2. Запускайте Zapret_Launcher_v2.0.exe от имени администратора;
3. Выбирайте любой метод использования Zapret и подключайтесь к стабильной сети находясь под ограничениями РКН.

***Telegram Proxy:***
1. Ставим галочку "Запустить вместе с Zapret" в лаунчере;
2. Запускаем Telegram на ПК;
3. Переходим в настройки;
4. Продвинутые настройки;
5. Тип соединения;
6. Использовать собственное прокси (SOCKS5, Хост: 127.0.0.1, Порт: 1080).

***Youtube:***
Возможно он может не работать писав "Нет подключения к интернету" и т.п., решение этой проблемы может быть что то одним из:
1. WIN + R: cmd, ipconfig /flushdns (Можно прописать в CMD также, как снизу (p.s Если произошли какие то ошибки));
2. В браузере (Пример Google) заходим в настройки —> Конфиденциальность и безопасность —> Безопасность: Выбрать поставщика услуг DNS (Google: Public DNS или Cloudflare);
3. По порядку пробовать:
3.1. general (ALT).bat,
3.2. general (ALT2).bat,
3.3. general (ALT3).bat,
3.4. general (FAKE TLS AUTO).bat,
3.5. general (SIMPLE FAKE).bat.
4. Обновите hosts в лаунчере (Сервис —> Обновить hosts);

**Разные провайдеры = разные блокировки.**

Если произошли какие то ошибки: `ipconfig /flushdns && netsh winsock reset && netsh int ip reset && taskkill /F /IM winws.exe 2>nul && taskkill /F /IM ws2s.exe 2>nul && taskkill /F /IM nfqws.exe 2>nul && taskkill /F /IM divert.exe 2>nul`

1. Оригинальный запрет: https://github.com/flowseal/zapret-discord-youtube
2. Оригинальный тг прокси: https://github.com/Flowseal/tg-ws-proxy

**by trimansberg.**
