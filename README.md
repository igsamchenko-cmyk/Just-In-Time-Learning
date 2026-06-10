# Генератор інтерактивного навчання

MVP україномовної Just-In-Time Learning платформи: користувач створює персональний мікрокурс, проходить модулі, відповідає на сценарні завдання, а ШІ-провайдер дає навчальний фідбек і відкриває наступні кроки.

## Що вже є

- FastAPI backend.
- SQLite база даних.
- Простий frontend на HTML/CSS.
- Mock AI provider для розробки без API-ключів.
- Структура під майбутні Gemini/Claude provider-и.
- Google OAuth каркас і демо-вхід для локальної перевірки без ключів.
- Експорт курсу в Markdown-конспект.

## Запуск

```powershell
.\run.ps1
```

Проєкт використовує локальний Python у `.runtime/python`, якщо він уже підготовлений. Папка `.runtime` не входить у git і потрібна тільки для локального запуску на цій машині.

Після запуску відкрий:

```text
http://127.0.0.1:8000
```

Для Google OAuth заповни змінні з `.env.example` у власному `.env` або в системному середовищі. Без них буде доступний демо-вхід.

## AI provider

За замовчуванням працює `MockProvider`. Для Gemini створи `.env` і заповни:

```text
AI_PROVIDER=gemini
GEMINI_API_KEY=твій_ключ
GEMINI_MODEL=gemini-2.5-flash
```

Якщо `AI_PROVIDER=gemini`, але ключа немає, застосунок повернеться до mock-режиму, якщо `AI_FALLBACK_TO_MOCK=true`.

## Наступний етап

- Підключити реальні виклики GeminiProvider або ClaudeProvider.
- Додати міграції бази даних.
- Додати завантаження PDF після стабілізації текстових нотаток.

## Документація

- API: `docs/API.md`
- Ручна перевірка: `docs/MANUAL_TEST.md`
- Gemini provider: `docs/GEMINI.md`
- Deploy: `docs/DEPLOY.md`

## Тести

```powershell
.\.runtime\python\python.exe -m unittest
```

## Міграції бази даних

```powershell
.\migrate.ps1
```

Міграції використовують `DATABASE_URL` із `.env`. За замовчуванням це локальна SQLite база `learning_mvp.db`.

## Docker

1. Створи `.env` на основі `.env.production.example`.
2. Запусти:

```powershell
docker compose up --build
```

Застосунок буде доступний на:

```text
http://127.0.0.1:8000
```

Контейнер автоматично виконує міграції перед стартом. SQLite база зберігається у Docker volume `learning_data`.
