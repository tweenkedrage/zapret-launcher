# zapret-launcher
Обход ограничений и ускорение Telegram`a в РФ

На GitHub имеются Zapret и TGWSProxy отдельно и лично мне надоело их по отдельности включать, поэтому я решил сделать общий лаунчер куда я интегрировал в одно и zapret и tg proxy.

*Установка*
— Скачивайте архив и распаковывайте в любое место;
— Запускайте Zapret_Launcher_v2.0.exe от имени администратора;
— Выбирайте любой метод использования Zapret и подключайтесь к стабильной сети находясь под ограничениями РКН.

*Telegram Proxy:*
Запускаем Telegram на ПК, переходим в настройки —> Продвинутые настройки —> Тип соединения —> Использовать собственное прокси (SOCKS5, Хост: 127.0.0.1, Порт: 1080).

Если произошли какие то ошибки: `ipconfig /flushdns && netsh winsock reset && netsh int ip reset && taskkill /F /IM winws.exe 2>nul && taskkill /F /IM ws2s.exe 2>nul && taskkill /F /IM nfqws.exe 2>nul && taskkill /F /IM divert.exe 2>nul`

by trimansberg.
