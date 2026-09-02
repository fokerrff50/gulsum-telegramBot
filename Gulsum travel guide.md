# Telegram-бот @Gulsumgoddnessbot

Воронка для Instagram + Telegram:
- Проверка подписки на канал
- Выдача PDF-гайда по ключу `TRAVEL`
- Follow-up сообщения через 2, 5 и 7 дней
- Ответы на ключи `ПАРТНЁР` и `РАЗБОР`
- SQLite-база всех пользователей

## 📦 Что внутри

| Файл | Описание |
|---|---|
| `bot.py` | Основной код бота |
| `gulsum_travel_guide.pdf` | PDF-гайд (17 страниц) |
| `requirements.txt` | Зависимости Python |
| `.env.example` | Шаблон конфига |
| `README.md` | Эта инструкция |

## 🚀 Быстрый запуск

### 1. Установить зависимости

```bash
cd telegram_bot
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Создать `.env` файл

```bash
cp .env.example .env
nano .env   # или любой редактор
```

Впиши свой `BOT_TOKEN` от @BotFather.

### 3. Запустить

```bash
python bot.py
```

Если всё ок — увидишь:
```
Бот запущен. Канал: @flywithgulsum
```

## ☁️ Развёртывание на сервере (бесплатно)

### Вариант А: Railway.app (рекомендую)

1. Создай аккаунт на https://railway.app
2. «New Project» → «Deploy from GitHub repo»
3. Залей папку `telegram_bot/` в репозиторий
4. В Railway: Variables → добавь `BOT_TOKEN` и `CHANNEL_USERNAME`
5. Deploy → готово

### Вариант Б: Render.com

1. https://render.com → New → Background Worker
2. Подключи репозиторий
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. Environment: добавь `BOT_TOKEN` и `CHANNEL_USERNAME`

### Вариант В: Свой сервер / VPS

```bash
# На сервере
git clone <твой-репо>
cd telegram_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env   # впиши токен

# Запуск в фоне через systemd
sudo nano /etc/systemd/system/gulsum-bot.service
```

Содержимое service-файла:

```ini
[Unit]
Description=Gulsum Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram_bot
ExecStart=/home/ubuntu/telegram_bot/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable gulsum-bot
sudo systemctl start gulsum-bot
```

## 🧪 Как протестировать

1. Открой своего бота в Telegram: `@Gulsumgoddnessbot`
2. Нажми `/start`
3. Нажми «🎁 Получить гайд»
4. Если не подписан на канал — увидишь кнопки подписки
5. Подпишись на `@flywithgulsum`
6. Нажми «✅ Проверить»
7. Получишь PDF

## 📊 Как посмотреть базу пользователей

```bash
sqlite3 bot_users.db
sqlite> SELECT user_id, username, first_name, guide_sent FROM users;
sqlite> .quit
```

## 🔑 Ключевые слова бота

| Слово | Что делает |
|---|---|
| `/start` | Приветствие + кнопка |
| `TRAVEL` | Проверка подписки → выдача PDF |
| `ПАРТНЁР` | Нейтральный ответ про модель |
| `РАЗБОР` | Запрос информации для консультации |

## 📅 Follow-up цепочка

После выдачи PDF автоматически:
- **День 2:** «Как гайд? Получилось применить?»
- **День 5:** «Могу разобрать твою ситуацию — напиши РАЗБОР»
- **День 7:** «Если интересно партнёрство — напиши ПАРТНЁР»

## 🆘 Если что-то не работает

1. Бот не отвечает → проверь токен в `.env`
2. «Не подписан» хотя подписан → бот не админ канала
3. PDF не отправляется → проверь, что файл лежит рядом с `bot.py`
4. Follow-up не приходит → бот должен работать постоянно (не выключай сервер)

## 📞 Поддержка

Telegram: @gulsumgoddness
Instagram: @gulsumgoddness
