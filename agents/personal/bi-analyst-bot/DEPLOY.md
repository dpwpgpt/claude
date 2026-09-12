# Деплой на VDS (Ubuntu/Debian, Docker)

Все команды ниже выполняются **по SSH на самом VDS**, не в этой сессии.

## 1. Подключись к серверу

```bash
ssh user@your-vds-ip
```

## 2. Установи Docker (если ещё не установлен)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

После `usermod` переподключись по SSH, чтобы группа применилась:

```bash
exit
ssh user@your-vds-ip
docker --version
docker compose version
```

## 3. Скопируй проект на сервер

Вариант А — через git (если репозиторий доступен серверу):

```bash
git clone <URL_РЕПОЗИТОРИЯ> claude
cd claude/agents/personal/bi-analyst-bot
```

Вариант Б — скопировать папку с локальной машины по scp:

```bash
# выполнить у себя на компьютере, не на VDS
scp -r agents/personal/bi-analyst-bot user@your-vds-ip:~/bi-analyst-bot
```

затем на VDS:

```bash
cd ~/bi-analyst-bot
```

## 4. Настрой `.env`

```bash
cp .env.example .env
nano .env
```

Обязательно заполни:

```
TELEGRAM_BOT_TOKEN=токен_от_botfather
ANTHROPIC_API_KEY=ключ_anthropic
MSSQL_SERVER=адрес_сервера
MSSQL_DATABASE=имя_базы
MSSQL_USER=логин
MSSQL_PASSWORD=пароль
ALLOWED_TELEGRAM_USER_IDS=твой_telegram_user_id
```

Убедись, что MS SQL Server доступен с этого VDS по сети (порт 1433
открыт в файрволе/группе безопасности, включён TCP/IP-протокол и SQL
Server Authentication на самом сервере).

## 5. Запусти бота

```bash
docker compose up -d --build
```

Проверь, что контейнер поднялся и работает:

```bash
docker compose ps
docker compose logs -f
```

В логах должна появиться строка о числе загруженных таблиц и
`Bot started`. Напиши боту `/start` в Telegram — если ответил, всё
работает. Останови просмотр логов `Ctrl+C` (бот продолжит работать в
фоне).

## Обновление после изменений в коде

```bash
git pull                       # если клонировали через git
docker compose up -d --build
```

## Остановка / перезапуск

```bash
docker compose down       # остановить
docker compose restart    # перезапустить
```

## Просмотр логов позже

```bash
docker compose logs -f --tail 100
```

Бот не хранит на диске никакого состояния — вся конфигурация в `.env`,
все данные читаются напрямую из MS SQL Server, поэтому отдельный бэкап
не требуется.
