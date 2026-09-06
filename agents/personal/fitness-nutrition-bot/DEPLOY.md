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
cd claude/agents/personal/fitness-nutrition-bot
```

Вариант Б — скопировать папку с локальной машины по scp:

```bash
# выполнить у себя на компьютере, не на VDS
scp -r agents/personal/fitness-nutrition-bot user@your-vds-ip:~/fitness-nutrition-bot
```

затем на VDS:

```bash
cd ~/fitness-nutrition-bot
```

## 4. Настрой `.env`

```bash
cp .env.example .env
nano .env
```

Заполни:

```
TELEGRAM_BOT_TOKEN=токен_от_botfather
ANTHROPIC_API_KEY=sk-ant-...
```

`BOT_DB_PATH` в `.env` можно не трогать — в docker-compose.yml он уже
переопределён на `/app/data/fitness_bot.db`, файл базы сохранится в папке
`./data` на хосте и переживёт пересборку контейнера.

## 5. Запусти бота

```bash
docker compose up -d --build
```

Проверь, что контейнер поднялся и работает:

```bash
docker compose ps
docker compose logs -f
```

В логах должна появиться строка `Bot started`. Напиши боту `/start` в
Telegram — если ответил, всё работает. Останови просмотр логов `Ctrl+C`
(бот продолжит работать в фоне).

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

## Бэкап дневника питания

Вся база — это один файл `./data/fitness_bot.db` на хосте. Достаточно
периодически копировать его:

```bash
cp data/fitness_bot.db data/fitness_bot.db.bak-$(date +%F)
```
