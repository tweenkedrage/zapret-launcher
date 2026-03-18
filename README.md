# zapret-launcher
Обход ограничений и ускорение Telegram`a в РФ

На GitHub имеются Zapret и TGWSProxy отдельно и лично мне надоело их по отдельности включать, поэтому я решил сделать общий лаунчер куда я интегрировал в одно и zapret и tg proxy.

*Установка:*
1. Скачивайте архив и распаковывайте в любое место;
2. Запускайте Zapret_Launcher_v2.0.exe от имени администратора;
3. Выбирайте любой метод использования Zapret и подключайтесь к стабильной сети находясь под ограничениями РКН.

*Telegram Proxy:*
1. Ставим галочку "Запустить вместе с Zapret" в лаунчере;
2. Запускаем Telegram на ПК;
3. Переходим в настройки;
4. Продвинутые настройки;
5. Тип соединения;
6. Использовать собственное прокси (SOCKS5, Хост: 127.0.0.1, Порт: 1080).

*Youtube:*
Возможно он может не работать писав "Нет подключения к интернету" и т.п., решение этой проблемы может быть что то одним из:
1. WIN + R: cmd, ipconfig /flushdns (Можно прописать в CMD также, как снизу (p.s Если произошли какие то ошибки));
2. В браузере (Пример Google) заходим в настройки —> Конфиденциальность и безопасность —> Безопасность: Выбрать поставщика услуг DNS (Google: Public DNS или Cloudflare);
3. По порядку пробовать:
general (ALT).bat
general (ALT2).bat
general (ALT3).bat
general (FAKE TLS AUTO).bat
general (SIMPLE FAKE).bat
4. Обновите hosts в лаунчере (Сервис —> Обновить hosts);

**Разные провайдеры = разные блокировки.**

Если произошли какие то ошибки: `ipconfig /flushdns && netsh winsock reset && netsh int ip reset && taskkill /F /IM winws.exe 2>nul && taskkill /F /IM ws2s.exe 2>nul && taskkill /F /IM nfqws.exe 2>nul && taskkill /F /IM divert.exe 2>nul`

Оригинальный запрет: https://github.com/flowseal/zapret-discord-youtube
Оригинальный тг прокси: https://github.com/Flowseal/tg-ws-proxy

**by trimansberg.**
