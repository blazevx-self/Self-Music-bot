<div align="center">

# 🎧 Self Music

**Персональный музыкальный ассистент: подбор по вкусу, поиск треков и плейлисты.**

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2AABEE?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Бот в Telegram](https://t.me/selfmusical_bot) · [Разработчик](https://t.me/blazevx) · [Канал проекта](https://t.me/blazevx_self)

</div>

---

## ℹ️ О проекте (в процессе разработки, сделана малая часть)

**Self Music** — Telegram-бот, ориентированный на прямой поиск и доставку полных аудиозаписей в чат без сторонней рекламы и перехода на внешние сервисы.

Большинство открытых API (например, Deezer) отдают только 30-секундные ознакомительные фрагменты. В проекте реализован гибридный подход:
1. Каталог **Deezer API** используется для быстрого поиска, получения точных названий, длительности и обложек альбомов.
2. При выборе композиции загрузчик на базе **yt-dlp** находит полную версию (SoundCloud / YouTube) и передаёт файл в Telegram в неблокирующем потоке.

---

## 📲 Функционал

- **Каталог и поиск:** поиск по названию композиции и имени исполнителя по международной базе.
- **Распознавание музыки:** голосовые напевы, аудио и видео обрабатываются через AudD; распознавание включается и отключается в настройках. Для работы нужен `AUDD_API_TOKEN`.
- **Полные аудиозаписи:** отправка полноценных аудиофайлов в формате Telegram Audio (`.m4a` / `.mp3`).
- **Метаданные:** корректное заполнение тегов (исполнитель, трек, длительность) и прикрепление оригинальной обложки.
- **Постраничная навигация:** отображение результатов порциями по 10 треков с инлайн-пагинацией.
- **Отказоустойчивость:** fallback-логика источников для предотвращения блокировок (HTTP 403) на стороне серверных дата-центров.
- **Защита от нагрузки:**
  - Дебаунс нажатий инлайн-кнопок для предотвращения повторных скачиваний (`CallbackSpamMiddleware`).
  - Ограничение частоты текстовых запросов со скользящим окном и временной блокировкой (`MessageFloodMiddleware`).
- **Контроль доступа:** проверка обязательной подписки на канал проекта перед началом работы.

---

## 📝 Планы по развитию

- [ ] Кэширование `file_id` отправленных аудиозаписей в PostgreSQL для моментальной повторной отправки.
- [ ] Пользовательские плейлисты и избранное (`/playlists`).
- [x] Распознавание аудиозаписей по голосовым сообщениям, аудиофайлам и видео.
- [ ] Парсинг ссылок на альбомы и плейлисты стриминговых сервисов.
- [ ] Топы, новинки и подборки
- [ ] Настройка функционала и аккаунты
 
---

## 📜 Развёртывание

### Требования
- Установленные `docker` и `docker compose`.
- Токен Telegram-бота от [@BotFather](https://t.me/BotFather).

### 💾 Установка

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/self-music.git
   cd self-music

2. Создайте конфигурационный файл окружения:
   ```bash
    cp .env.example .env

3. Заполните обязательные переменные в .env:
    ```ini
   POSTGRES_USER=your_postgres_user
   POSTGRES_PASSWORD=your_postgres_password
   POSTGRES_DB=self_music

   PGADMIN_EMAIL=admin@example.com
   PGADMIN_PASSWORD=your_pgadmin_password

   BOT_TOKEN=your_bot_token
   ADMIN_ID=your_telegram_id

   DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"

   CHANNEL_ID=your_telegram_channel_id
   CHANNEL_URL=https://t.me/your_channel

   # Для распознавания: токен AudD с https://dashboard.audd.io/
   AUDD_API_TOKEN=your_audd_api_token

   Без `AUDD_API_TOKEN` текстовый поиск работает, но распознавание аудио отключено.

4. Запустите контейнеры:
   ```bash
   docker compose up -d --build

5. Просмотр логов:
   ```bash 
   docker compose logs -f bot

## 📄 Лицензия
Проект распространяется под лицензией MIT.