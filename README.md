<div align="center">

# 🎧 Self Music

**Музыкальный Telegram-ассистент: ищет треки, распознаёт мелодии и помогает находить музыку по настроению.**

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2AABEE?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Открыть бота](https://t.me/selfmusical_bot) · [Разработчик](https://t.me/blazevx) · [Канал проекта](https://t.me/blazevx_self)

</div>

---

## ✨ О проекте

**Self Music** — персональный музыкальный бот для Telegram. Он помогает найти песню по названию или исполнителю, распознать музыку из аудио и видео, а также открыть чарты и тематические подборки.

Проект формально завершён. Не сделаны только плейлисты. Данные о треках и обложках бот получает через Deezer, а для попытки найти аудиозапись использует `yt-dlp` и доступные источники. Доступность конкретного трека зависит от источника и региона
### Как это работает

```text
Текстовый запрос ──► Deezer: поиск и метаданные ──► результаты в Telegram
Выбор трека ───────► yt-dlp: поиск аудио ─────────► отправка аудио в чат
Голос / аудио / видео ► AudD: распознавание ───────► поиск совпадения в Deezer
```

## 🎼 Возможности

- **Поиск музыки** по названию трека или имени исполнителя с постраничной навигацией.
- **Отправка найденного аудио** в чат как Telegram Audio — если подходящая запись доступна в источниках.
- **Распознавание музыки** из голосовых сообщений, аудиофайлов и видео; для напетых мелодий используется режим AudD humming.
- **Новинки и топы Deezer** — мировые новинки, жанровые чарты и отдельный русский топ.
- **Подборки по настроению** — например, музыка для дороги, отдыха или тренировки.
- **Настройки функций** — пользователь может включать и отключать распознавание и другие доступные переключатели.
- **Раздел аккаунтов** — экспериментальная работа с публичными профилями VK. Доступ к аудиозаписям зависит от ограничений VK API и настроек профиля.
- **Проверка подписки на канал** перед началом использования.
- **Защита от частых запросов и повторных нажатий** на кнопки.

> Возможности внешних сервисов меняются. Бот не гарантирует наличие каждой записи или доступность VK-аудио.

## 🤖 Команды и меню

- `/start` — начать работу и открыть главное меню.
- `/help` — показать справку.
- `/new` — новинки 
- `/settings` — настройки функций
- `/accounts` — подключенные аккаунты вк
- `/mixes` — подборки треков
- `/top` — топы треков по прослушиваниям

Поиск, новинки, топы, подборки, настройки и аккаунты открываются из меню бота или же через slash-команды

## 🧰 Технологии

- Python 3.14 и [aiogram 3](https://docs.aiogram.dev/)
- PostgreSQL 16, SQLAlchemy и Alembic
- Docker Compose
- Deezer API, AudD API и `yt-dlp`
- FFmpeg для извлечения аудио из видео

## 🚀 Запуск через Docker Compose

### Требования

- Docker с поддержкой `docker compose`.
- Telegram-бот и его токен от [@BotFather](https://t.me/BotFather).
- ID Telegram-пользователя администратора.
- Канал проекта, если включена проверка подписки.

### 1. Получить проект

```bash
git clone https://github.com/blazevx-self/Self-Music-bot.git
cd Self-Music-bot
cp .env.example .env
```

### 2. Настроить `.env`

Укажи значения вместо примеров:

```dotenv
POSTGRES_USER=self_music
POSTGRES_PASSWORD=замени-на-сильный-пароль
POSTGRES_DB=self_music
POSTGRES_CONTAINER_NAME=self-music-postgres

PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=замени-на-сильный-пароль
PGADMIN_CONTAINER_NAME=self-music-pgadmin

BOT_CONTAINER_NAME=self-music-bot
BOT_TOKEN=токен-от-BotFather
ADMIN_ID=твой-числовой-Telegram-ID

DATABASE_URL=postgresql+asyncpg://self_music:замени-на-сильный-пароль@postgres:5432/self_music

CHANNEL_ID=-1000000000000
CHANNEL_URL=https://t.me/имя_канала

# Необязательно: распознавание AudD
AUDD_API_TOKEN=

# Необязательно: доступ к VK API для раздела аккаунтов
VK_TOKEN=

# Необязательно: прокси для yt-dlp, если источник недоступен напрямую
YTDLP_PROXY=
```

`CHANNEL_ID` — числовой ID канала, обычно начинается с `-100`. Боту нужно дать доступ к каналу, чтобы проверка подписки работала.

Если в пароле PostgreSQL есть символы вроде `@`, `:`, `/` или `#`, закодируй их для URL в `DATABASE_URL` либо используй пароль без этих символов.

**Не публикуй `.env` и не отправляй его в GitHub:** в нём находятся секреты. Файл уже исключён из Git через `.gitignore`.

### 3. Запустить

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f bot
```

Контейнер миграций дождётся готовности PostgreSQL и выполнит миграции Alembic при запуске Compose.

### 4. Остановить

```bash
docker compose down
```

Обычный `down` останавливает и удаляет контейнеры, но сохраняет данные PostgreSQL в Docker volume. **Не добавляй `-v`, если не хочешь удалить базу данных.**

## 🖥️ PgAdmin

PgAdmin доступен локально по адресу [http://localhost:5050](http://localhost:5050). Войди с `PGADMIN_EMAIL` и `PGADMIN_PASSWORD` из `.env`.

Чтобы подключиться к базе из PgAdmin, укажи hostname `postgres`, порт `5432`, имя базы, пользователя и пароль из `.env`. Этот hostname работает внутри Docker-сети проекта.

## 🔑 Необязательные интеграции

- **AudD:** получи API-токен в [кабинете AudD](https://dashboard.audd.io/) и задай `AUDD_API_TOKEN`. Без него обычный текстовый поиск продолжит работать, но распознавание будет недоступно.
- **VK:** задай `VK_TOKEN`, чтобы бот мог обращаться к VK API. Даже с токеном VK может ограничивать доступ к аудиозаписям.
- **Прокси для yt-dlp:** при необходимости укажи `YTDLP_PROXY`, например `socks5h://proxy-host:1080`.

## 🛡️ Ответственное использование

Внешние каталоги и платформы предоставляют данные по собственным правилам и могут менять доступность контента. Используй бота только для материалов, к которым у тебя есть право доступа, и соблюдай условия соответствующих сервисов и местное законодательство.